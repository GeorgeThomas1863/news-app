import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from app import config, db
from app.pipeline import clean, embed, group, ingest_rss, ingest_telegram, score, verdict
from app.pipeline import filter as importance_filter

log = logging.getLogger(__name__)

VERDICT_SAMPLE_TEXTS = 3
EMBED_CHUNK_SIZE = 64  # one rejected text costs at most this many docs, not the whole backlog

_lock = asyncio.Lock()
_background_tasks = set()
_paused = True  # scraping is opt-in: every boot starts stopped until Resume
_stop_requested = False


def is_running():
    return _lock.locked()


def is_paused():
    return _paused


def pause():
    """Stop the workflow: scheduler skips its ticks and any in-flight run aborts
    at its next checkpoint. In-memory only, and the module default is stopped,
    so a restart also boots stopped."""
    global _paused, _stop_requested
    _paused = True
    if _lock.locked():
        _stop_requested = True
        return {"success": True, "message": "pipeline stopped; in-flight run aborting"}
    return {"success": True, "message": "pipeline stopped"}


def resume():
    global _paused, _stop_requested
    _paused = False
    _stop_requested = False
    return {"success": True, "message": "pipeline resumed"}


def start_background_run(tg_client, trigger):
    """Kick off a run without blocking the caller. False if one is already in flight."""
    if _lock.locked():
        return False
    task = asyncio.create_task(run_pipeline(tg_client, trigger))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return True


async def run_pipeline(tg_client, trigger):
    global _stop_requested
    if _lock.locked():
        return {"success": False, "message": "pipeline already running"}

    async with _lock:
        run_id = await start_run(trigger)
        counts = {
            "ingested": 0,
            "deduped": 0,
            "embedded": 0,
            "stories_created": 0,
            "stories_updated": 0,
            "filtered_out": 0,
            "scored": 0,
            "orphans_reaped": 0,
        }
        errors = []
        status = "success"
        try:
            await ingest_all(tg_client, counts, errors)
            await embed_pending(counts, errors)
            await reap_orphan_stories(counts)
            await group_new_items(counts, errors)
            await process_dirty_stories(counts, errors)
        except Exception as error:
            log.exception("pipeline run failed (trigger=%s)", trigger)
            errors.append({"stage": "run", "message": str(error)})
            status = "error"

        if _stop_requested:
            _stop_requested = False
            if status == "success":
                status = "stopped"
            log.info("pipeline run aborted by stop (trigger=%s)", trigger)

        await finish_run(run_id, status, counts, errors)
        return {"success": status == "success", "message": status, "run_id": str(run_id)}


async def start_run(trigger):
    result = await db.pipeline_runs.insert_one(
        {
            "trigger": trigger,
            "started_at": datetime.now(timezone.utc),
            "finished_at": None,
            "status": "running",
            "counts": {},
            "errors": [],
        }
    )
    return result.inserted_id


async def finish_run(run_id, status, counts, errors):
    await db.pipeline_runs.update_one(
        {"_id": run_id},
        {
            "$set": {
                "finished_at": datetime.now(timezone.utc),
                "status": status,
                "counts": counts,
                "errors": errors,
            }
        },
    )


async def ingest_all(tg_client, counts, errors):
    try:
        source_docs = await db.sources.find({"enabled": True}).to_list(length=None)
    except Exception as error:
        log.exception("loading sources failed")
        errors.append({"stage": "ingest", "source": "sources-load", "message": str(error)})
        return

    telegram_channels = [doc["channel"] for doc in source_docs if doc["type"] == "telegram"]
    rss_feeds = [{"name": doc["name"], "url": doc["url"]} for doc in source_docs if doc["type"] == "rss"]

    for channel in telegram_channels:
        if _stop_requested:
            return
        try:
            items = await ingest_telegram.fetch_new_channel_messages(tg_client, channel)
            await store_items(items, counts)
            if items:
                last_id = max(item["message_id"] for item in items)
                await ingest_telegram.set_bookmark(channel, last_id)
        except Exception as error:
            log.exception("telegram ingest failed (channel=%s)", channel)
            errors.append({"stage": "ingest", "source": channel, "message": str(error)})

    for feed in rss_feeds:
        if _stop_requested:
            return
        try:
            items = await ingest_rss.fetch_new_feed_entries(feed["name"], feed["url"])
            await store_items(items, counts)
        except Exception as error:
            log.exception("rss ingest failed (feed=%s)", feed["name"])
            errors.append({"stage": "ingest", "source": feed["name"], "message": str(error)})


async def store_items(items, counts):
    for item in items:
        doc = clean.build_clean_item(
            source_type=item["source_type"],
            source_name=item["source_name"],
            url=item["url"],
            title=item["title"],
            text=item["text"],
            published_at=item["published_at"],
        )
        if doc is None:
            continue
        try:
            await db.raw.insert_one(doc)
            counts["ingested"] += 1
        except DuplicateKeyError:
            counts["deduped"] += 1


async def embed_pending(counts, errors):
    if _stop_requested:
        return
    # An unembedded item is always ungrouped too, and story_id (unlike the
    # vector field) has an index that serves null equality.
    docs = [doc async for doc in db.raw.find({"story_id": None, "embedding": None})]
    for start in range(0, len(docs), EMBED_CHUNK_SIZE):
        if _stop_requested:
            return
        await embed_chunk(docs[start : start + EMBED_CHUNK_SIZE], counts, errors)


async def embed_chunk(chunk, counts, errors):
    try:
        vectors = await embed.embed_texts([doc["text"] for doc in chunk])
    except Exception as error:
        log.exception("embedding chunk failed (%d docs)", len(chunk))
        errors.append({"stage": "embed", "message": str(error)})
        return

    for doc, vector in zip(chunk, vectors):
        await db.raw.update_one({"_id": doc["_id"]}, {"$set": {"embedding": vector}})
        counts["embedded"] += 1


async def reap_orphan_stories(counts):
    """Delete story shells whose creating run died before linking the item —
    their item stayed story_id: None, so grouping will redo it this run."""
    pending = [s async for s in db.stories.find({"status": "pending"})]
    for story in pending:
        linked = await db.raw.count_documents({"story_id": story["_id"]})
        if linked > 0:
            continue
        await db.stories.delete_one({"_id": story["_id"]})
        counts["orphans_reaped"] += 1


async def group_new_items(counts, errors):
    new_items = [
        doc async for doc in db.raw.find({"embedding": {"$ne": None}, "story_id": None})
    ]
    if not new_items:
        return

    candidates = await load_active_candidates()
    for item in new_items:
        if _stop_requested:
            return
        try:
            await place_item(item, candidates, counts)
        except Exception as error:
            log.exception("grouping failed (item=%s)", item["_id"])
            errors.append({"stage": "group", "item": str(item["_id"]), "message": str(error)})


async def load_active_candidates():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.ACTIVE_WINDOW_HOURS)
    stories = [s async for s in db.stories.find({"latest_item_at": {"$gte": cutoff}})]

    candidates = []
    for story in stories:
        embeddings = []
        sample_texts = []
        async for doc in db.raw.find({"story_id": story["_id"], "embedding": {"$ne": None}}):
            embeddings.append(doc["embedding"])
            if len(sample_texts) < VERDICT_SAMPLE_TEXTS:
                sample_texts.append(doc["text"])
        if not embeddings:
            continue
        candidates.append(
            {
                "story_id": story["_id"],
                "embedding_matrix": group.build_embedding_matrix(embeddings),
                "headline": story.get("headline"),
                "sample_texts": sample_texts,
            }
        )
    return candidates


async def place_item(item, candidates, counts):
    # Pure-CPU similarity over every active embedding — keep it off the event
    # loop so API requests stay responsive while grouping runs.
    decision = await asyncio.to_thread(
        group.decide_placement, item["embedding"], candidates, config.SIM_HIGH, config.SIM_LOW
    )

    if decision["action"] == "verify":
        candidate = find_candidate(candidates, decision["story_id"])
        same = await verdict.ask_same_story(
            item["text"], candidate["headline"], candidate["sample_texts"]
        )
        action = "join" if same else "new"
        decision = {"action": action, "story_id": decision["story_id"]}

    if decision["action"] == "join":
        await attach_item_to_story(item, decision["story_id"], candidates, counts)
        return
    await create_story_for_item(item, candidates, counts)


def find_candidate(candidates, story_id):
    for candidate in candidates:
        if candidate["story_id"] == story_id:
            return candidate
    raise ValueError(f"candidate story {story_id} not found")


async def attach_item_to_story(item, story_id, candidates, counts):
    now = datetime.now(timezone.utc)
    # Story bookkeeping first: a crash between the writes then leaves the item
    # story_id: None, so the next run re-groups it instead of losing it. The
    # transient item_count over-count is corrected when the story is scored.
    await db.stories.update_one(
        {"_id": story_id},
        {
            "$inc": {"item_count": 1},
            "$set": {"dirty": True, "updated_at": now},
            "$max": {"latest_item_at": item["published_at"]},
            "$min": {"first_item_at": item["published_at"]},
        },
    )
    await db.raw.update_one({"_id": item["_id"]}, {"$set": {"story_id": story_id}})

    candidate = find_candidate(candidates, story_id)
    candidate["embedding_matrix"] = group.append_to_embedding_matrix(
        candidate["embedding_matrix"], item["embedding"]
    )
    if len(candidate["sample_texts"]) < VERDICT_SAMPLE_TEXTS:
        candidate["sample_texts"].append(item["text"])
    counts["stories_updated"] += 1


async def create_story_for_item(item, candidates, counts):
    now = datetime.now(timezone.utc)
    result = await db.stories.insert_one(
        {
            "status": "pending",
            "dirty": True,
            "topic": None,
            "headline": None,
            "summary": None,
            "score": None,
            "item_count": 1,
            "first_item_at": item["published_at"],
            "latest_item_at": item["published_at"],
            "scored_at": None,
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.raw.update_one({"_id": item["_id"]}, {"$set": {"story_id": result.inserted_id}})

    candidates.append(
        {
            "story_id": result.inserted_id,
            "embedding_matrix": group.build_embedding_matrix([item["embedding"]]),
            "headline": None,
            "sample_texts": [item["text"]],
        }
    )
    counts["stories_created"] += 1


async def process_dirty_stories(counts, errors):
    dirty = [s async for s in db.stories.find({"dirty": True})]
    for story in dirty:
        if _stop_requested:
            return
        try:
            await process_story(story, counts)
        except Exception as error:
            log.exception("story processing failed (story=%s)", story["_id"])
            errors.append({"stage": "score", "story": str(story["_id"]), "message": str(error)})


async def process_story(story, counts):
    items = [doc async for doc in db.raw.find({"story_id": story["_id"]})]
    texts = [item["text"] for item in items]

    if story["status"] in ("pending", "filtered"):
        important = await importance_filter.is_possibly_important(texts)
        if important is None:
            return
        if important is False:
            await mark_story_filtered(story["_id"])
            counts["filtered_out"] += 1
            return

    result = await score.score_story(items)
    if result is None:
        return
    await mark_story_scored(story["_id"], result, len(items))
    counts["scored"] += 1


async def mark_story_filtered(story_id):
    await db.stories.update_one(
        {"_id": story_id},
        {"$set": {"status": "filtered", "dirty": False, "updated_at": datetime.now(timezone.utc)}},
    )


async def mark_story_scored(story_id, result, item_count):
    now = datetime.now(timezone.utc)
    await db.stories.update_one(
        {"_id": story_id},
        {
            "$set": {
                "status": "scored",
                "dirty": False,
                "score": result["score"],
                "topic": result["topic"],
                "headline": result["headline"],
                "summary": result["summary"],
                # authoritative recount — attach's $inc can transiently over-count
                "item_count": item_count,
                "scored_at": now,
                "updated_at": now,
            }
        },
    )

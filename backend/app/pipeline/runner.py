import asyncio
import logging
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

from app import config, db
from app.pipeline import clean, embed, group, ingest_rss, ingest_telegram, score, verdict
from app.pipeline import filter as importance_filter

log = logging.getLogger(__name__)

VERDICT_SAMPLE_TEXTS = 3

_lock = asyncio.Lock()
_background_tasks = set()


def is_running():
    return _lock.locked()


def start_background_run(tg_client, trigger):
    """Kick off a run without blocking the caller. False if one is already in flight."""
    if _lock.locked():
        return False
    task = asyncio.create_task(run_pipeline(tg_client, trigger))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return True


async def run_pipeline(tg_client, trigger):
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
        }
        errors = []
        status = "success"
        try:
            await ingest_all(tg_client, counts, errors)
            await embed_pending(counts, errors)
            await group_new_items(counts, errors)
            await process_dirty_stories(counts, errors)
        except Exception as error:
            log.exception("pipeline run failed (trigger=%s)", trigger)
            errors.append({"stage": "run", "message": str(error)})
            status = "error"

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
    for channel in config.TELEGRAM_CHANNELS:
        try:
            items = await ingest_telegram.fetch_new_channel_messages(tg_client, channel)
            await store_items(items, counts)
            if items:
                last_id = max(item["message_id"] for item in items)
                await ingest_telegram.set_bookmark(channel, last_id)
        except Exception as error:
            log.exception("telegram ingest failed (channel=%s)", channel)
            errors.append({"stage": "ingest", "source": channel, "message": str(error)})

    for feed in config.RSS_FEEDS:
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
    docs = [doc async for doc in db.raw.find({"embedding": None})]
    if not docs:
        return

    try:
        vectors = await embed.embed_texts([doc["text"] for doc in docs])
    except Exception as error:
        log.exception("embedding stage failed")
        errors.append({"stage": "embed", "message": str(error)})
        return

    for doc, vector in zip(docs, vectors):
        await db.raw.update_one({"_id": doc["_id"]}, {"$set": {"embedding": vector}})
        counts["embedded"] += 1


async def group_new_items(counts, errors):
    new_items = [
        doc async for doc in db.raw.find({"embedding": {"$ne": None}, "story_id": None})
    ]
    if not new_items:
        return

    candidates = await load_active_candidates()
    for item in new_items:
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
                "embeddings": embeddings,
                "headline": story.get("headline"),
                "sample_texts": sample_texts,
            }
        )
    return candidates


async def place_item(item, candidates, counts):
    decision = group.decide_placement(
        item["embedding"], candidates, config.SIM_HIGH, config.SIM_LOW
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
    await db.raw.update_one({"_id": item["_id"]}, {"$set": {"story_id": story_id}})
    await db.stories.update_one(
        {"_id": story_id},
        {
            "$inc": {"item_count": 1},
            "$set": {"dirty": True, "updated_at": now},
            "$max": {"latest_item_at": item["published_at"]},
            "$min": {"first_item_at": item["published_at"]},
        },
    )

    candidate = find_candidate(candidates, story_id)
    candidate["embeddings"].append(item["embedding"])
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
            "embeddings": [item["embedding"]],
            "headline": None,
            "sample_texts": [item["text"]],
        }
    )
    counts["stories_created"] += 1


async def process_dirty_stories(counts, errors):
    dirty = [s async for s in db.stories.find({"dirty": True})]
    for story in dirty:
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
    await mark_story_scored(story["_id"], result)
    counts["scored"] += 1


async def mark_story_filtered(story_id):
    await db.stories.update_one(
        {"_id": story_id},
        {"$set": {"status": "filtered", "dirty": False, "updated_at": datetime.now(timezone.utc)}},
    )


async def mark_story_scored(story_id, result):
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
                "scored_at": now,
                "updated_at": now,
            }
        },
    )

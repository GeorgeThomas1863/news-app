import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app import config, db, ranking
from app.auth import require_auth

log = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


@router.get("/stories")
async def get_stories(topic: str | None = None, limit: int | None = None, skip: int = 0):
    now = datetime.now(timezone.utc)
    if topic is None:
        return await build_overview(now)
    return await build_topic_page(topic, limit or config.STORIES_PER_TOPIC, skip, now)


@router.get("/stories/{story_id}")
async def get_story(story_id: str):
    oid = parse_object_id(story_id)
    story = await find_scored_story(oid)
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    payload = serialize_story(story)
    payload["items"] = await find_story_items(oid)
    return payload


async def build_overview(now):
    topics = []
    for topic in config.TOPICS:
        ranked = await rank_topic(topic, now)
        topics.append(
            {
                "topic": topic,
                "total": len(ranked),
                "stories": [serialize_story(s) for s in ranked[: config.STORIES_PER_TOPIC]],
            }
        )
    return {"topics": topics}


async def build_topic_page(topic, limit, skip, now):
    if topic not in config.TOPICS:
        raise HTTPException(status_code=404, detail="Unknown topic")

    ranked = await rank_topic(topic, now)
    return {
        "topic": topic,
        "total": len(ranked),
        "stories": [serialize_story(s) for s in ranked[skip : skip + limit]],
    }


async def rank_topic(topic, now):
    # Past this many half-lives a story's effective score can never outrank a
    # fresh one, so bounding the query keeps rank cost flat as stories accumulate.
    cutoff = now - timedelta(hours=config.DECAY_HALF_LIFE_HOURS * config.RANKING_WINDOW_HALF_LIVES)
    try:
        docs = [
            s
            async for s in db.stories.find(
                {"status": "scored", "topic": topic, "latest_item_at": {"$gte": cutoff}}
            )
        ]
    except Exception:
        log.exception("rank_topic: failed to load scored stories (topic=%s)", topic)
        raise HTTPException(status_code=503, detail="Database unavailable")
    return ranking.rank_stories(docs, now, config.DECAY_HALF_LIFE_HOURS)


async def find_scored_story(oid):
    # Only scored stories are ever returned to the frontend —
    # pending/filtered ones 404 just like unknown ids.
    try:
        return await db.stories.find_one({"_id": oid, "status": "scored"})
    except Exception:
        log.exception("find_scored_story: failed to load story (id=%s)", oid)
        raise HTTPException(status_code=503, detail="Database unavailable")


async def find_story_items(oid):
    try:
        return [
            serialize_item(doc)
            async for doc in db.raw.find({"story_id": oid}).sort("published_at", -1)
        ]
    except Exception:
        log.exception("find_story_items: failed to load items (story=%s)", oid)
        raise HTTPException(status_code=503, detail="Database unavailable")


def parse_object_id(value):
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Story not found")


def serialize_story(story):
    return {
        "id": str(story["_id"]),
        "topic": story["topic"],
        "headline": story["headline"],
        "summary": story["summary"],
        "score": story["score"],
        "effective_score": story.get("effective_score"),
        "item_count": story["item_count"],
        "first_item_at": story["first_item_at"].isoformat(),
        "latest_item_at": story["latest_item_at"].isoformat(),
    }


def serialize_item(item):
    return {
        "id": str(item["_id"]),
        "source_type": item["source_type"],
        "source_name": item["source_name"],
        "url": item["url"],
        "title": item["title"],
        "text": item["text"],
        "published_at": item["published_at"].isoformat(),
    }

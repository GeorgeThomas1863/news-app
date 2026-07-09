from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException

from app import config, db, ranking
from app.auth import require_auth

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
    story = await db.stories.find_one({"_id": oid})
    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")

    payload = serialize_story(story)
    payload["items"] = [
        serialize_item(doc)
        async for doc in db.raw.find({"story_id": oid}).sort("published_at", -1)
    ]
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
    docs = [s async for s in db.stories.find({"status": "scored", "topic": topic})]
    return ranking.rank_stories(docs, now, config.DECAY_HALF_LIFE_HOURS)


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

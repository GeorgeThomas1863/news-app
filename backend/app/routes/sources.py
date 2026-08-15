import logging
from datetime import datetime, timezone

import feedparser
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo.errors import DuplicateKeyError

from app import db
from app.auth import require_auth
from app.pipeline import ingest_rss

log = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


class RssSourceIn(BaseModel):
    name: str
    url: str


class TelegramSourceIn(BaseModel):
    channel: str


class SourceUpdateIn(BaseModel):
    name: str | None = None
    url: str | None = None
    channel: str | None = None
    enabled: bool | None = None


@router.get("/sources")
async def list_sources():
    return await build_sources_payload()


@router.post("/sources/rss")
async def add_rss_source(body: RssSourceIn):
    await verify_rss_feed(body.url)
    doc = {
        "type": "rss",
        "name": body.name,
        "url": body.url,
        "channel": None,
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
    }
    source_id = await insert_source(doc)
    return {"success": True, "message": "Source added", "id": source_id}


@router.post("/sources/telegram")
async def add_telegram_source(body: TelegramSourceIn, request: Request):
    await verify_telegram_channel(request.app.state.tg_client, body.channel)
    doc = {
        "type": "telegram",
        "name": body.channel,
        "url": None,
        "channel": body.channel,
        "enabled": True,
        "created_at": datetime.now(timezone.utc),
    }
    source_id = await insert_source(doc)
    return {"success": True, "message": "Source added", "id": source_id}


@router.put("/sources/{source_id}")
async def update_source(source_id: str, body: SourceUpdateIn, request: Request):
    oid = parse_object_id(source_id)
    source = await find_source(oid)
    updates = await build_update_fields(source, body, request)
    await apply_source_update(oid, updates)
    return {"success": True, "message": "Source updated"}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    oid = parse_object_id(source_id)
    await find_source(oid)
    await remove_source(oid)
    return {"success": True, "message": "Source removed"}


async def build_sources_payload():
    try:
        docs = [doc async for doc in db.sources.find({})]
    except Exception:
        log.exception("build_sources_payload: failed to load sources")
        raise HTTPException(status_code=503, detail="Database unavailable")

    payload = {"rss": [], "telegram": []}
    for doc in docs:
        payload[doc["type"]].append(serialize_source(doc))
    return payload


async def verify_rss_feed(url):
    try:
        feed_text = await ingest_rss.fetch_feed_text(url)
    except Exception as exc:
        log.warning("verify_rss_feed: fetch failed (url=%s): %s", url, exc)
        raise HTTPException(status_code=400, detail=f"Could not fetch feed: {exc}")

    parsed = feedparser.parse(feed_text)
    if not parsed.entries and not parsed.feed.get("title"):
        raise HTTPException(
            status_code=400, detail="URL does not look like a valid RSS/Atom feed"
        )


async def insert_source(doc):
    try:
        result = await db.sources.insert_one(doc)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Source already exists")
    except Exception:
        log.exception("insert_source: failed to insert (name=%s)", doc.get("name"))
        raise HTTPException(status_code=503, detail="Database unavailable")
    return str(result.inserted_id)


async def verify_telegram_channel(tg_client, channel):
    if tg_client is None:
        raise HTTPException(status_code=503, detail="Telegram client not connected")

    try:
        await tg_client.get_entity(channel)
    except Exception as exc:
        log.warning("verify_telegram_channel: get_entity failed (channel=%s): %s", channel, exc)
        raise HTTPException(status_code=400, detail=f"Could not resolve channel: {exc}")


def parse_object_id(value):
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Source not found")


async def find_source(oid):
    try:
        source = await db.sources.find_one({"_id": oid})
    except Exception:
        log.exception("find_source: failed to load source (id=%s)", oid)
        raise HTTPException(status_code=503, detail="Database unavailable")

    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


async def build_update_fields(source, body, request):
    updates = {}
    if body.enabled is not None:
        updates["enabled"] = body.enabled

    if source["type"] == "rss":
        await apply_rss_update_fields(source, body, updates)
    else:
        await apply_telegram_update_fields(source, body, request, updates)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    return updates


async def apply_rss_update_fields(source, body, updates):
    if body.name is not None:
        updates["name"] = body.name

    if body.url is not None and body.url != source.get("url"):
        await verify_rss_feed(body.url)
        updates["url"] = body.url


async def apply_telegram_update_fields(source, body, request, updates):
    if body.channel is None or body.channel == source.get("channel"):
        return

    await verify_telegram_channel(request.app.state.tg_client, body.channel)
    updates["channel"] = body.channel
    updates["name"] = body.channel  # a telegram source's name always follows its channel


async def apply_source_update(oid, updates):
    try:
        await db.sources.update_one({"_id": oid}, {"$set": updates})
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="Source already exists")
    except Exception:
        log.exception("apply_source_update: failed to update (id=%s)", oid)
        raise HTTPException(status_code=503, detail="Database unavailable")


async def remove_source(oid):
    try:
        await db.sources.delete_one({"_id": oid})
    except Exception:
        log.exception("remove_source: failed to delete (id=%s)", oid)
        raise HTTPException(status_code=503, detail="Database unavailable")


def serialize_source(doc):
    out = {"id": str(doc["_id"]), "name": doc["name"], "enabled": doc["enabled"]}
    if doc["type"] == "rss":
        out["url"] = doc["url"]
    else:
        out["channel"] = doc["channel"]
    return out

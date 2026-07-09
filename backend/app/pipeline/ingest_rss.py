import calendar
from datetime import datetime, timezone

import feedparser
import httpx

from app import db


async def fetch_new_feed_entries(feed_name, feed_url):
    """Returns pre-clean item dicts for unseen entries; empty on first poll (no backfill)."""
    feed_text = await fetch_feed_text(feed_url)
    entries = feedparser.parse(feed_text).entries

    state = await db.source_state.find_one(
        {"source_type": "rss", "source_name": feed_name}
    )
    if state is None:
        await record_initial_snapshot(feed_name, entries)
        return []

    seen_urls = set(state.get("initial_seen_urls", []))
    items = []
    for entry in entries:
        item = await build_feed_item(feed_name, entry, seen_urls)
        if item is None:
            continue
        items.append(item)

    await mark_polled(feed_name)
    return items


async def fetch_feed_text(url):
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def record_initial_snapshot(feed_name, entries):
    urls = []
    for entry in entries:
        url = entry.get("link")
        if url:
            urls.append(url)

    await db.source_state.update_one(
        {"source_type": "rss", "source_name": feed_name},
        {"$set": {"initial_seen_urls": urls, "last_polled_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


async def mark_polled(feed_name):
    await db.source_state.update_one(
        {"source_type": "rss", "source_name": feed_name},
        {"$set": {"last_polled_at": datetime.now(timezone.utc)}},
    )


async def build_feed_item(feed_name, entry, seen_urls):
    url = entry.get("link")
    if not url or url in seen_urls:
        return None
    if await db.raw.find_one({"url": url}):
        return None

    return {
        "source_type": "rss",
        "source_name": feed_name,
        "url": url,
        "title": entry.get("title"),
        "text": extract_entry_text(entry),
        "published_at": parse_entry_published(entry),
    }


def extract_entry_text(entry):
    content = entry.get("content")
    if content:
        return content[0].get("value", "")
    return entry.get("summary", "")


def parse_entry_published(entry):
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct is None:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)

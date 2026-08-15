import logging
from datetime import datetime, timezone

from pymongo import AsyncMongoClient

from app import config

log = logging.getLogger(__name__)

client = None
db = None
raw = None
stories = None
source_state = None
pipeline_runs = None
sources = None


async def init_db(uri=None, db_name=None):
    """Connect and bind collection handles. Called from the app lifespan (and test fixtures)."""
    global client, db, raw, stories, source_state, pipeline_runs, sources

    # tz_aware so stored datetimes come back UTC-aware — decay math mixes them with datetime.now(timezone.utc)
    client = AsyncMongoClient(uri or config.MONGO_URI, tz_aware=True)
    db = client[db_name or config.DB_NAME]
    raw = db["raw"]
    stories = db["stories"]
    source_state = db["source_state"]
    pipeline_runs = db["pipeline_runs"]
    sources = db["sources"]

    await ensure_indexes()


async def close_db():
    global client
    if client is None:
        return
    await client.close()
    client = None


async def ensure_indexes():
    try:
        await raw.create_index("content_hash", unique=True)
        await raw.create_index("url")
        await raw.create_index("story_id")
        await stories.create_index([("status", 1), ("latest_item_at", -1)])
        await stories.create_index(
            [("status", 1), ("topic", 1), ("latest_item_at", -1)]
        )  # rank_topic, per dashboard request
        await stories.create_index("dirty")  # process_dirty_stories, per pipeline run
        await sources.create_index(
            "url", unique=True, partialFilterExpression={"type": "rss"}
        )
        await sources.create_index(
            "channel", unique=True, partialFilterExpression={"type": "telegram"}
        )
    except Exception:
        log.exception("failed to ensure mongo indexes")
        raise


async def seed_sources_if_empty(rss_feeds, telegram_channels):
    """Insert config-defined feeds/channels as sources on first run. No-ops once any source exists."""
    try:
        if await sources.count_documents({}) > 0:
            return

        now = datetime.now(timezone.utc)
        docs = []
        for feed in rss_feeds:
            docs.append(
                {
                    "type": "rss",
                    "name": feed["name"],
                    "url": feed["url"],
                    "channel": None,
                    "enabled": True,
                    "created_at": now,
                }
            )
        for channel in telegram_channels:
            docs.append(
                {
                    "type": "telegram",
                    "name": channel,
                    "url": None,
                    "channel": channel,
                    "enabled": True,
                    "created_at": now,
                }
            )

        if docs:
            await sources.insert_many(docs)
    except Exception:
        log.exception("failed to seed sources")
        raise

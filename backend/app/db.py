import logging

from pymongo import AsyncMongoClient

from app import config

log = logging.getLogger(__name__)

client = None
db = None
raw = None
stories = None
source_state = None
pipeline_runs = None


async def init_db(uri=None, db_name=None):
    """Connect and bind collection handles. Called from the app lifespan (and test fixtures)."""
    global client, db, raw, stories, source_state, pipeline_runs

    # tz_aware so stored datetimes come back UTC-aware — decay math mixes them with datetime.now(timezone.utc)
    client = AsyncMongoClient(uri or config.MONGO_URI, tz_aware=True)
    db = client[db_name or config.DB_NAME]
    raw = db["raw"]
    stories = db["stories"]
    source_state = db["source_state"]
    pipeline_runs = db["pipeline_runs"]

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
    except Exception:
        log.exception("failed to ensure mongo indexes")
        raise

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import bcrypt
import pytest_asyncio
from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import auth, config, db
from app.pipeline import ingest_rss, ingest_telegram, runner
from app.routes import sources as sources_routes

TEST_PASSWORD = "correct-horse-battery"

VALID_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A minimal valid feed for tests.</description>
    <item>
      <title>Item One</title>
      <link>https://example.com/item-1</link>
      <description>First item.</description>
    </item>
  </channel>
</rss>
"""


@pytest_asyncio.fixture
async def make_client(test_db, monkeypatch):
    """Factory for a logged-in test client with a configurable Telegram client
    on app.state.tg_client. Mirrors tests/test_routes.py's `client` fixture."""
    pw_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    monkeypatch.setattr(config, "PW_HASH", pw_hash)
    monkeypatch.setattr(config, "JWT_SECRET", "test-secret-thats-at-least-32-bytes-long!")
    monkeypatch.setattr(config, "SECURE_COOKIES", False)

    @asynccontextmanager
    async def _make(tg_client=None):
        app = FastAPI()
        app.include_router(auth.router, prefix="/api")
        app.include_router(sources_routes.router, prefix="/api")
        app.state.tg_client = tg_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
            await test_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
            yield test_client

    return _make


@pytest_asyncio.fixture
async def client(make_client):
    async with make_client() as test_client:
        yield test_client


async def test_get_sources_requires_auth(client):
    client.cookies.clear()

    response = await client.get("/api/sources")

    assert response.status_code == 401


async def test_get_sources_groups_by_type(client, test_db):
    rss_id = await insert_source(test_db, "rss", "BBC World", url="https://bbc.example.com/rss")
    tg_id = await insert_source(test_db, "telegram", "chan1", channel="chan1")

    response = await client.get("/api/sources")

    assert response.status_code == 200
    body = response.json()
    assert body["rss"] == [
        {"id": str(rss_id), "name": "BBC World", "url": "https://bbc.example.com/rss", "enabled": True}
    ]
    assert body["telegram"] == [
        {"id": str(tg_id), "name": "chan1", "channel": "chan1", "enabled": True}
    ]


async def test_post_rss_with_valid_feed_creates_source(client, test_db, monkeypatch):
    async def fake_fetch_feed_text(url):
        return VALID_RSS_XML

    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch_feed_text)

    response = await client.post(
        "/api/sources/rss", json={"name": "Test Feed", "url": "https://example.com/rss"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Source added"
    doc = await test_db.sources.find_one({"url": "https://example.com/rss"})
    assert doc is not None
    assert doc["type"] == "rss"
    assert doc["name"] == "Test Feed"
    assert doc["enabled"] is True
    assert str(doc["_id"]) == body["id"]


async def test_post_rss_with_unreachable_feed_returns_400(client, test_db, monkeypatch):
    async def failing_fetch_feed_text(url):
        raise RuntimeError("feed unreachable")

    monkeypatch.setattr(ingest_rss, "fetch_feed_text", failing_fetch_feed_text)

    response = await client.post(
        "/api/sources/rss", json={"name": "Bad Feed", "url": "https://example.com/bad-rss"}
    )

    assert response.status_code == 400
    assert "detail" in response.json()
    assert await test_db.sources.count_documents({}) == 0


async def test_post_rss_duplicate_url_returns_409(client, test_db, monkeypatch):
    async def fake_fetch_feed_text(url):
        return VALID_RSS_XML

    monkeypatch.setattr(ingest_rss, "fetch_feed_text", fake_fetch_feed_text)
    await insert_source(test_db, "rss", "Existing Feed", url="https://example.com/dup-rss")

    response = await client.post(
        "/api/sources/rss", json={"name": "New Name", "url": "https://example.com/dup-rss"}
    )

    assert response.status_code == 409


async def test_post_telegram_with_valid_channel_creates_source(make_client, test_db):
    tg_client = FakeTelegramClient(entity=SimpleNamespace(id=1))

    async with make_client(tg_client=tg_client) as client:
        response = await client.post("/api/sources/telegram", json={"channel": "newschannel"})

    assert response.status_code == 200
    assert response.json()["success"] is True
    doc = await test_db.sources.find_one({"channel": "newschannel"})
    assert doc is not None
    assert doc["type"] == "telegram"
    assert doc["enabled"] is True


async def test_post_telegram_with_no_tg_client_returns_503(client):
    response = await client.post("/api/sources/telegram", json={"channel": "newschannel"})

    assert response.status_code == 503


async def test_put_toggles_enabled(client, test_db):
    source_id = await insert_source(test_db, "rss", "Toggle Feed", url="https://example.com/toggle")

    response = await client.put(f"/api/sources/{source_id}", json={"enabled": False})

    assert response.status_code == 200
    assert response.json()["success"] is True
    doc = await test_db.sources.find_one({"_id": source_id})
    assert doc["enabled"] is False


async def test_put_does_not_cross_apply_fields_by_type(client, test_db):
    rss_id = await insert_source(test_db, "rss", "RSS Feed", url="https://example.com/rss-guard")
    tg_id = await insert_source(test_db, "telegram", "tgchan", channel="tgchan")

    rss_response = await client.put(
        f"/api/sources/{rss_id}", json={"enabled": False, "channel": "should-not-apply"}
    )
    tg_response = await client.put(
        f"/api/sources/{tg_id}", json={"enabled": False, "url": "https://should-not-apply.example.com"}
    )

    assert rss_response.status_code == 200
    assert tg_response.status_code == 200
    rss_doc = await test_db.sources.find_one({"_id": rss_id})
    tg_doc = await test_db.sources.find_one({"_id": tg_id})
    assert rss_doc["enabled"] is False
    assert rss_doc["channel"] is None
    assert tg_doc["enabled"] is False
    assert tg_doc["url"] is None


async def test_put_unknown_id_returns_404(client):
    missing_id = ObjectId()

    response = await client.put(f"/api/sources/{missing_id}", json={"enabled": False})

    assert response.status_code == 404


async def test_delete_removes_source_but_not_source_state(client, test_db):
    source_id = await insert_source(test_db, "rss", "Delete Me", url="https://example.com/delete-me")
    await test_db.source_state.insert_one(
        {"source_type": "rss", "source_name": "Delete Me", "last_polled_at": datetime.now(timezone.utc)}
    )

    response = await client.delete(f"/api/sources/{source_id}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert await test_db.sources.find_one({"_id": source_id}) is None
    assert await test_db.source_state.find_one({"source_name": "Delete Me"}) is not None


async def test_seed_sources_if_empty_seeds_once(test_db):
    rss_feeds = [{"name": "Feed A", "url": "https://a.example.com/rss"}]
    telegram_channels = ["chanX"]

    await db.seed_sources_if_empty(rss_feeds, telegram_channels)

    docs = [d async for d in test_db.sources.find({})]
    assert len(docs) == 2
    rss_doc = next(d for d in docs if d["type"] == "rss")
    tg_doc = next(d for d in docs if d["type"] == "telegram")
    assert rss_doc["name"] == "Feed A"
    assert rss_doc["url"] == "https://a.example.com/rss"
    assert rss_doc["enabled"] is True
    assert tg_doc["channel"] == "chanX"
    assert tg_doc["enabled"] is True

    await db.seed_sources_if_empty([{"name": "Feed B", "url": "https://b.example.com/rss"}], ["chanY"])

    docs_after = [d async for d in test_db.sources.find({})]
    assert len(docs_after) == 2
    assert await test_db.sources.find_one({"url": "https://b.example.com/rss"}) is None


async def test_ingest_all_reads_sources_and_skips_disabled(test_db, monkeypatch):
    await insert_source(test_db, "telegram", "goodchan", channel="goodchan", enabled=True)
    await insert_source(test_db, "telegram", "offchan", channel="offchan", enabled=False)
    await insert_source(test_db, "rss", "GoodFeed", url="https://good.example.com/rss", enabled=True)
    await insert_source(test_db, "rss", "OffFeed", url="https://off.example.com/rss", enabled=False)

    fetched_channels = []
    fetched_feeds = []

    async def fake_fetch_telegram(tg_client, channel):
        fetched_channels.append(channel)
        return []

    async def fake_fetch_rss(feed_name, feed_url):
        fetched_feeds.append(feed_name)
        return []

    monkeypatch.setattr(ingest_telegram, "fetch_new_channel_messages", fake_fetch_telegram)
    monkeypatch.setattr(ingest_rss, "fetch_new_feed_entries", fake_fetch_rss)

    counts = {"ingested": 0, "deduped": 0}
    errors = []
    await runner.ingest_all(None, counts, errors)

    assert fetched_channels == ["goodchan"]
    assert fetched_feeds == ["GoodFeed"]
    assert errors == []


async def insert_source(test_db, type_, name, enabled=True, url=None, channel=None):
    """Insert a sources doc directly, bypassing the API — for tests that need
    existing data set up rather than exercised."""
    result = await test_db.sources.insert_one(
        {
            "type": type_,
            "name": name,
            "url": url,
            "channel": channel,
            "enabled": enabled,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return result.inserted_id


class FakeTelegramClient:
    """Duck-types the one Telethon method the sources routes call: get_entity.
    Returns an object for a valid channel; raises when it can't resolve."""

    def __init__(self, entity=None, raises=False):
        self.entity = entity
        self.raises = raises

    async def get_entity(self, channel):
        if self.raises:
            raise ValueError(f"no such entity: {channel}")
        return self.entity if self.entity is not None else SimpleNamespace(id=1, title=channel)

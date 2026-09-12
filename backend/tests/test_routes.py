from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
import pytest_asyncio
from bson import ObjectId
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app import auth, config
from app.pipeline import runner
from app.routes import pipeline as pipeline_routes
from app.routes import stories as stories_routes

TEST_PASSWORD = "correct-horse-battery"


@pytest_asyncio.fixture
async def client(test_db, monkeypatch):
    """Async test client on the SAME event loop as the Mongo client (TestClient runs its own)."""
    pw_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    monkeypatch.setattr(config, "PW_HASH", pw_hash)
    monkeypatch.setattr(config, "JWT_SECRET", "test-secret-thats-at-least-32-bytes-long!")
    monkeypatch.setattr(config, "SECURE_COOKIES", False)

    app = FastAPI()
    app.include_router(auth.router, prefix="/api")
    app.include_router(stories_routes.router, prefix="/api")
    app.include_router(pipeline_routes.router, prefix="/api")
    app.state.tg_client = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        await test_client.post("/api/auth/login", json={"password": TEST_PASSWORD})
        yield test_client


def make_story(topic, score, hours_old, status="scored", headline="Headline"):
    now = datetime.now(timezone.utc)
    at = now - timedelta(hours=hours_old)
    return {
        "status": status,
        "dirty": False,
        "topic": topic,
        "headline": headline,
        "summary": "Summary.",
        "score": score,
        "item_count": 1,
        "first_item_at": at,
        "latest_item_at": at,
        "scored_at": at,
        "created_at": at,
        "updated_at": at,
    }


async def test_stories_requires_auth(client):
    client.cookies.clear()
    response = await client.get("/api/stories")
    assert response.status_code == 401


async def test_overview_groups_ranked_scored_stories_by_topic(client, test_db, monkeypatch):
    monkeypatch.setattr(config, "TOPICS", ["Tech", "Markets"])
    monkeypatch.setattr(config, "STORIES_PER_TOPIC", 2)
    await test_db.stories.insert_many(
        [
            make_story("Tech", 50, 0, headline="fresh fifty"),
            make_story("Tech", 90, 48, headline="stale ninety"),  # decays to 22.5
            make_story("Tech", 60, 0, headline="fresh sixty"),
            make_story("Markets", 70, 0, headline="markets story"),
            make_story("Tech", 99, 0, status="pending", headline="unscored"),
            make_story("Tech", 99, 0, status="filtered", headline="filtered out"),
        ]
    )

    response = await client.get("/api/stories")

    assert response.status_code == 200
    body = response.json()
    topics = {t["topic"]: t for t in body["topics"]}
    assert list(topics) == ["Tech", "Markets"]
    tech = topics["Tech"]
    assert tech["total"] == 3
    assert [s["headline"] for s in tech["stories"]] == ["fresh sixty", "fresh fifty"]
    assert tech["stories"][0]["effective_score"] == 60.0
    assert topics["Markets"]["stories"][0]["headline"] == "markets story"


async def test_topic_page_paginates(client, test_db, monkeypatch):
    monkeypatch.setattr(config, "TOPICS", ["Tech"])
    await test_db.stories.insert_many(
        [
            make_story("Tech", 90, 0, headline="first"),
            make_story("Tech", 80, 0, headline="second"),
            make_story("Tech", 70, 0, headline="third"),
        ]
    )

    response = await client.get("/api/stories", params={"topic": "Tech", "limit": 2, "skip": 1})

    body = response.json()
    assert body["topic"] == "Tech"
    assert body["total"] == 3
    assert [s["headline"] for s in body["stories"]] == ["second", "third"]


async def test_unknown_topic_returns_404(client):
    response = await client.get("/api/stories", params={"topic": "Sports"})
    assert response.status_code == 404


async def test_story_detail_returns_items_newest_first(client, test_db):
    insert = await test_db.stories.insert_one(make_story("Tech", 80, 1))
    now = datetime.now(timezone.utc)
    await test_db.raw.insert_many(
        [
            {
                "source_type": "rss",
                "source_name": "Feed",
                "url": "https://example.com/old",
                "title": "Old",
                "text": "old text",
                "published_at": now - timedelta(hours=2),
                "ingested_at": now,
                "content_hash": "h-old",
                "embedding": [1.0],
                "story_id": insert.inserted_id,
            },
            {
                "source_type": "telegram",
                "source_name": "chan",
                "url": "https://t.me/chan/9",
                "title": None,
                "text": "new text",
                "published_at": now - timedelta(hours=1),
                "ingested_at": now,
                "content_hash": "h-new",
                "embedding": [1.0],
                "story_id": insert.inserted_id,
            },
        ]
    )

    response = await client.get(f"/api/stories/{insert.inserted_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(insert.inserted_id)
    assert body["score"] == 80
    assert [i["text"] for i in body["items"]] == ["new text", "old text"]
    assert body["items"][0]["url"] == "https://t.me/chan/9"
    assert "embedding" not in body["items"][0]


async def test_story_detail_bad_or_missing_id_returns_404(client):
    assert (await client.get("/api/stories/not-an-objectid")).status_code == 404
    assert (await client.get("/api/stories/0123456789abcdef01234567")).status_code == 404


async def test_pipeline_status_empty(client):
    response = await client.get("/api/pipeline/status")

    assert response.status_code == 200
    assert response.json() == {"running": False, "paused": True, "run": None}


async def test_pipeline_status_returns_latest_run(client, test_db):
    now = datetime.now(timezone.utc)
    await test_db.pipeline_runs.insert_many(
        [
            {
                "trigger": "schedule",
                "started_at": now - timedelta(minutes=30),
                "finished_at": now - timedelta(minutes=29),
                "status": "success",
                "counts": {"ingested": 1},
                "errors": [],
            },
            {
                "trigger": "manual",
                "started_at": now - timedelta(minutes=5),
                "finished_at": now - timedelta(minutes=4),
                "status": "success",
                "counts": {"ingested": 7},
                "errors": [],
            },
        ]
    )

    body = (await client.get("/api/pipeline/status")).json()

    assert body["running"] is False
    assert body["run"]["trigger"] == "manual"
    assert body["run"]["counts"]["ingested"] == 7


async def test_pipeline_run_starts_background_run(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        runner, "start_background_run", lambda tg_client, trigger: calls.append(trigger) or True
    )

    response = await client.post("/api/pipeline/run")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert calls == ["manual"]


async def test_pipeline_run_conflict_when_already_running(client, monkeypatch):
    monkeypatch.setattr(runner, "start_background_run", lambda tg_client, trigger: False)

    response = await client.post("/api/pipeline/run")

    assert response.status_code == 409


async def test_pipeline_stop_and_resume_toggle_paused(client):
    body = (await client.post("/api/pipeline/stop")).json()
    assert body["success"] is True
    assert (await client.get("/api/pipeline/status")).json()["paused"] is True

    body = (await client.post("/api/pipeline/resume")).json()
    assert body["success"] is True
    assert (await client.get("/api/pipeline/status")).json()["paused"] is False


async def test_pipeline_stop_is_idempotent(client):
    await client.post("/api/pipeline/stop")
    body = (await client.post("/api/pipeline/stop")).json()
    assert body["success"] is True
    assert (await client.get("/api/pipeline/status")).json()["paused"] is True


async def test_pipeline_stop_resume_require_auth(client):
    client.cookies.clear()
    assert (await client.post("/api/pipeline/stop")).status_code == 401
    assert (await client.post("/api/pipeline/resume")).status_code == 401


def make_raw(source_type, source_name, hours_old, story_id=None, embedding=None, suffix=""):
    now = datetime.now(timezone.utc)
    at = now - timedelta(hours=hours_old)
    return {
        "source_type": source_type,
        "source_name": source_name,
        "url": f"https://example.com/{source_name}/{hours_old}{suffix}",
        "title": "Title",
        "text": "some cleaned body text",
        "published_at": at,
        "ingested_at": at,
        "content_hash": f"hash-{source_name}-{hours_old}-{suffix}",
        "embedding": embedding,
        "story_id": story_id,
    }


async def test_pipeline_stats_requires_auth(client):
    client.cookies.clear()
    response = await client.get("/api/pipeline/stats")
    assert response.status_code == 401


async def test_pipeline_stats_empty_db(client, monkeypatch):
    monkeypatch.delenv("FILTER_MODEL", raising=False)
    monkeypatch.delenv("SCORING_MODEL", raising=False)
    monkeypatch.setattr(config, "FILTER_MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(config, "SCORING_MODEL", "gpt-5.6-sol")

    response = await client.get("/api/pipeline/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["running"] is False
    assert body["paused"] is True
    assert body["recent_runs"] == []

    assert set(body["live"]["stages"]) == {"ingest", "embed", "reap", "group", "score"}

    totals = body["totals"]
    assert totals["raw_items"] == 0
    assert totals["raw_embedded"] == 0
    assert totals["raw_ungrouped"] == 0
    assert totals["raw_last_24h"] == 0
    assert totals["stories"] == {"pending": 0, "filtered": 0, "scored": 0, "dirty": 0, "total": 0}
    assert totals["sources"] == {
        "rss": {"enabled": 0, "disabled": 0},
        "telegram": {"enabled": 0, "disabled": 0},
    }
    assert totals["items_by_source"] == []

    assert body["config"] == {
        "poll_interval_minutes": config.POLL_INTERVAL_MINUTES,
        "sim_high": config.SIM_HIGH,
        "sim_low": config.SIM_LOW,
        "active_window_hours": config.ACTIVE_WINDOW_HOURS,
        "decay_half_life_hours": config.DECAY_HALF_LIFE_HOURS,
        "embed_model": config.EMBED_MODEL,
        "filter_model": "gpt-5.6-luna",
        "scoring_model": "gpt-5.6-sol",
    }


async def test_pipeline_stats_recent_runs_and_totals(client, test_db):
    now = datetime.now(timezone.utc)
    await test_db.pipeline_runs.insert_many(
        [
            {
                "trigger": "schedule",
                "started_at": now - timedelta(hours=2),
                "finished_at": now - timedelta(hours=2) + timedelta(minutes=3),
                "status": "success",
                "counts": {"ingested": 5},
                "errors": [],
            },
            {
                "trigger": "manual",
                "started_at": now - timedelta(minutes=30),
                "finished_at": now - timedelta(minutes=25),
                "status": "success",
                "counts": {"ingested": 2},
                "errors": [],
            },
            {
                "trigger": "manual",
                "started_at": now - timedelta(minutes=1),
                "finished_at": None,
                "status": "running",
                "counts": {},
                "errors": [],
            },
        ]
    )

    story_id_a = ObjectId()
    story_id_b = ObjectId()
    await test_db.raw.insert_many(
        [
            make_raw("rss", "Feed A", hours_old=1, story_id=None, embedding=None, suffix="-1"),
            make_raw("rss", "Feed A", hours_old=30, story_id=story_id_a, embedding=[1.0], suffix="-2"),
            make_raw("telegram", "Chan B", hours_old=2, story_id=story_id_b, embedding=[1.0], suffix="-3"),
        ]
    )

    dirty_pending = make_story("Tech", 40, 0, status="pending", headline="dirty pending")
    dirty_pending["dirty"] = True
    await test_db.stories.insert_many(
        [
            make_story("Tech", 80, 0, status="scored", headline="scored one"),
            make_story("Tech", 50, 0, status="pending", headline="pending one"),
            make_story("Tech", 60, 0, status="filtered", headline="filtered one"),
            dirty_pending,
        ]
    )

    response = await client.get("/api/pipeline/stats")

    assert response.status_code == 200
    body = response.json()

    runs = body["recent_runs"]
    assert [r["trigger"] for r in runs] == ["manual", "manual", "schedule"]
    assert runs[0]["finished_at"] is None
    assert runs[0]["duration_seconds"] is None
    assert runs[1]["duration_seconds"] == pytest.approx(300.0)
    assert runs[2]["duration_seconds"] == pytest.approx(180.0)

    totals = body["totals"]
    assert totals["raw_items"] == 3
    assert totals["raw_embedded"] == 2
    assert totals["raw_ungrouped"] == 1
    assert totals["raw_last_24h"] == 2  # the 30h-old item falls outside the window

    assert totals["stories"]["pending"] == 2
    assert totals["stories"]["filtered"] == 1
    assert totals["stories"]["scored"] == 1
    assert totals["stories"]["dirty"] == 1
    assert totals["stories"]["total"] == 4

    items_by_source = {
        (row["source_name"], row["source_type"]): row["count"] for row in totals["items_by_source"]
    }
    assert items_by_source[("Feed A", "rss")] == 2
    assert items_by_source[("Chan B", "telegram")] == 1


async def test_pipeline_stats_sources_counts(client, test_db):
    now = datetime.now(timezone.utc)
    await test_db.sources.insert_many(
        [
            {
                "type": "rss",
                "name": "Feed A",
                "url": "https://a.example.com/feed",
                "channel": None,
                "enabled": True,
                "created_at": now,
            },
            {
                "type": "rss",
                "name": "Feed B",
                "url": "https://b.example.com/feed",
                "channel": None,
                "enabled": False,
                "created_at": now,
            },
            {
                "type": "telegram",
                "name": "chan1",
                "url": None,
                "channel": "chan1",
                "enabled": True,
                "created_at": now,
            },
            {
                "type": "telegram",
                "name": "chan2",
                "url": None,
                "channel": "chan2",
                "enabled": True,
                "created_at": now,
            },
        ]
    )

    response = await client.get("/api/pipeline/stats")

    assert response.status_code == 200
    assert response.json()["totals"]["sources"] == {
        "rss": {"enabled": 1, "disabled": 1},
        "telegram": {"enabled": 2, "disabled": 0},
    }

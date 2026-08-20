import asyncio
import subprocess
import sys
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import config, main
from app.pipeline import embed, ingest_telegram, runner, score
from app.pipeline import filter as importance_filter
from tests.test_ingest_telegram import FakeTelegramClient, make_message


@pytest.fixture
def pipeline_env(monkeypatch):
    monkeypatch.setattr(config, "MIN_TEXT_LENGTH", 5)

    async def fake_embed(texts):
        return [[1.0, 0.0] for _ in texts]

    async def fake_filter(texts):
        return True

    async def fake_score(items):
        return {"score": 77, "topic": "Tech", "headline": "H", "summary": "S"}

    monkeypatch.setattr(embed, "embed_texts", fake_embed)
    monkeypatch.setattr(importance_filter, "is_possibly_important", fake_filter)
    monkeypatch.setattr(score, "score_story", fake_score)
    return monkeypatch


async def insert_telegram_sources(test_db, channels):
    """runner.ingest_all reads channels from db.sources instead of
    config.TELEGRAM_CHANNELS now; insert matching enabled docs, preserving order."""
    docs = [
        {"type": "telegram", "name": channel, "channel": channel, "enabled": True}
        for channel in channels
    ]
    if docs:
        await test_db.sources.insert_many(docs)


async def test_full_cycle_ingests_groups_and_scores(test_db, pipeline_env):
    await insert_telegram_sources(test_db, ["chan"])
    await ingest_telegram.set_bookmark("chan", 100)
    tg_client = FakeTelegramClient(
        new_messages=[
            make_message(101, "big event happened right now"),
            make_message(102, "more details on the big event"),
        ]
    )

    result = await runner.run_pipeline(tg_client, trigger="manual")

    assert result["success"] is True
    items = [d async for d in test_db.raw.find({})]
    assert len(items) == 2
    stories = [s async for s in test_db.stories.find({})]
    assert len(stories) == 1
    story = stories[0]
    assert story["status"] == "scored"
    assert story["score"] == 77
    assert story["topic"] == "Tech"
    assert story["item_count"] == 2
    assert story["dirty"] is False
    assert all(i["story_id"] == story["_id"] for i in items)
    state = await test_db.source_state.find_one({"source_name": "chan"})
    assert state["last_message_id"] == 102
    run = await test_db.pipeline_runs.find_one({})
    assert run["status"] == "success"
    assert run["trigger"] == "manual"
    assert run["counts"]["ingested"] == 2
    assert run["counts"]["stories_created"] == 1
    assert run["counts"]["stories_updated"] == 1
    assert run["counts"]["scored"] == 1
    assert run["errors"] == []
    assert run["finished_at"] is not None


async def test_run_rejected_while_already_running(test_db):
    async with runner._lock:
        result = await runner.run_pipeline(None, trigger="manual")

    assert result["success"] is False
    assert "already running" in result["message"]


async def test_unimportant_story_is_filtered_not_scored(test_db, pipeline_env, monkeypatch):
    async def fake_filter(texts):
        return False

    async def exploding_score(items):
        raise AssertionError("score_story must not be called for filtered stories")

    monkeypatch.setattr(importance_filter, "is_possibly_important", fake_filter)
    monkeypatch.setattr(score, "score_story", exploding_score)
    await insert_telegram_sources(test_db, ["chan"])
    await ingest_telegram.set_bookmark("chan", 100)
    tg_client = FakeTelegramClient(new_messages=[make_message(101, "boring giveaway spam post")])

    await runner.run_pipeline(tg_client, trigger="schedule")

    story = await test_db.stories.find_one({})
    assert story["status"] == "filtered"
    assert story["dirty"] is False
    assert story["score"] is None
    run = await test_db.pipeline_runs.find_one({})
    assert run["counts"]["filtered_out"] == 1
    assert run["counts"]["scored"] == 0


async def test_failing_source_is_isolated_and_recorded(test_db, pipeline_env, monkeypatch):
    await insert_telegram_sources(test_db, ["bad", "good"])

    async def fake_fetch(tg_client, channel):
        if channel == "bad":
            raise RuntimeError("channel unreachable")
        return [
            {
                "source_type": "telegram",
                "source_name": channel,
                "url": f"https://t.me/{channel}/5",
                "title": None,
                "text": "a perfectly good post from the working channel",
                "published_at": datetime(2026, 7, 8, 10, 0, 0, tzinfo=timezone.utc),
                "message_id": 5,
            }
        ]

    monkeypatch.setattr(ingest_telegram, "fetch_new_channel_messages", fake_fetch)

    result = await runner.run_pipeline(FakeTelegramClient(), trigger="schedule")

    assert result["success"] is True
    items = [d async for d in test_db.raw.find({})]
    assert len(items) == 1
    run = await test_db.pipeline_runs.find_one({})
    assert len(run["errors"]) == 1
    assert run["errors"][0]["source"] == "bad"
    assert "channel unreachable" in run["errors"][0]["message"]


async def test_dirty_scored_story_is_rescored_without_filter(test_db, pipeline_env, monkeypatch):
    async def exploding_filter(texts):
        raise AssertionError("filter must not run for already-scored stories")

    async def fake_score(items):
        return {"score": 90, "topic": "Ukraine", "headline": "Updated", "summary": "Grew."}

    monkeypatch.setattr(importance_filter, "is_possibly_important", exploding_filter)
    monkeypatch.setattr(score, "score_story", fake_score)
    now = datetime.now(timezone.utc)
    insert = await test_db.stories.insert_one(
        {
            "status": "scored",
            "dirty": True,
            "topic": "Ukraine",
            "headline": "Old",
            "summary": "Old.",
            "score": 60,
            "item_count": 2,
            "first_item_at": now - timedelta(hours=3),
            "latest_item_at": now,
            "scored_at": now - timedelta(hours=2),
            "created_at": now - timedelta(hours=3),
            "updated_at": now,
        }
    )
    await test_db.raw.insert_one(
        {
            "source_type": "telegram",
            "source_name": "chan",
            "url": "https://t.me/chan/1",
            "title": None,
            "text": "original report",
            "published_at": now - timedelta(hours=3),
            "ingested_at": now,
            "content_hash": "h1",
            "embedding": [1.0, 0.0],
            "story_id": insert.inserted_id,
        }
    )

    await runner.run_pipeline(FakeTelegramClient(), trigger="schedule")

    story = await test_db.stories.find_one({"_id": insert.inserted_id})
    assert story["score"] == 90
    assert story["headline"] == "Updated"
    assert story["dirty"] is False
    assert story["status"] == "scored"


def test_boots_paused_by_default():
    """Fresh-interpreter import: the autouse reset fixture forces _paused = True
    after every test, so an in-process assert can't catch a reverted default."""
    result = subprocess.run(
        [sys.executable, "-c", "from app.pipeline import runner; print(runner.is_paused())"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert result.stdout.strip() == "True", result.stderr


def test_pause_and_resume_toggle_state():
    result = runner.resume()
    assert result["success"] is True
    assert runner.is_paused() is False

    result = runner.pause()
    assert result["success"] is True
    assert runner.is_paused() is True


async def test_stop_mid_run_finalizes_stopped_with_partial_counts(test_db, pipeline_env, monkeypatch):
    vectors = iter([[1.0, 0.0], [0.0, 1.0]])

    async def fake_embed(texts):
        return [next(vectors) for _ in texts]

    scored = []

    async def stopping_score(items):
        runner.pause()
        scored.append(items)
        return {"score": 50, "topic": "Tech", "headline": "H", "summary": "S"}

    monkeypatch.setattr(embed, "embed_texts", fake_embed)
    monkeypatch.setattr(score, "score_story", stopping_score)
    await insert_telegram_sources(test_db, ["chan"])
    await ingest_telegram.set_bookmark("chan", 100)
    tg_client = FakeTelegramClient(
        new_messages=[
            make_message(101, "first completely unrelated event"),
            make_message(102, "second totally different event"),
        ]
    )

    result = await runner.run_pipeline(tg_client, trigger="manual")

    assert result["message"] == "stopped"
    assert len(scored) == 1
    run = await test_db.pipeline_runs.find_one({})
    assert run["status"] == "stopped"
    assert run["finished_at"] is not None
    assert run["counts"]["ingested"] == 2
    assert run["counts"]["scored"] == 1
    assert runner.is_paused() is True
    assert runner._stop_requested is False


async def test_stop_between_sources_skips_remaining(test_db, pipeline_env, monkeypatch):
    await insert_telegram_sources(test_db, ["a", "b"])
    fetched = []

    async def stopping_fetch(tg_client, channel):
        fetched.append(channel)
        runner.pause()
        return []

    monkeypatch.setattr(ingest_telegram, "fetch_new_channel_messages", stopping_fetch)

    result = await runner.run_pipeline(FakeTelegramClient(), trigger="schedule")

    assert result["message"] == "stopped"
    assert fetched == ["a"]


async def test_scheduler_skips_run_while_paused(monkeypatch):
    calls = []

    async def fake_run(tg_client, trigger):
        calls.append(trigger)

    monkeypatch.setattr(runner, "run_pipeline", fake_run)
    runner.pause()
    app = SimpleNamespace(state=SimpleNamespace(tg_client=None))

    task = asyncio.create_task(main.run_pipeline_on_schedule(app))
    await asyncio.sleep(0)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    assert calls == []


async def test_scheduler_runs_when_not_paused(monkeypatch):
    calls = []

    async def fake_run(tg_client, trigger):
        calls.append(trigger)

    monkeypatch.setattr(runner, "run_pipeline", fake_run)
    runner.resume()
    app = SimpleNamespace(state=SimpleNamespace(tg_client=None))

    task = asyncio.create_task(main.run_pipeline_on_schedule(app))
    await asyncio.sleep(0)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    assert calls == ["schedule"]


async def test_failed_scoring_leaves_story_dirty_for_next_cycle(test_db, pipeline_env, monkeypatch):
    async def fake_score(items):
        return None

    monkeypatch.setattr(score, "score_story", fake_score)
    await insert_telegram_sources(test_db, ["chan"])
    await ingest_telegram.set_bookmark("chan", 100)
    tg_client = FakeTelegramClient(new_messages=[make_message(101, "important but scoring failed")])

    await runner.run_pipeline(tg_client, trigger="schedule")

    story = await test_db.stories.find_one({})
    assert story["status"] == "pending"
    assert story["dirty"] is True

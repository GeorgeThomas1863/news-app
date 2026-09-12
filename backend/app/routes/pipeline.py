import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app import config, db
from app import settings as settings_module
from app.auth import require_auth
from app.pipeline import progress, runner

log = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_auth)])


@router.post("/pipeline/run")
async def trigger_run(request: Request):
    started = runner.start_background_run(request.app.state.tg_client, "manual")
    if not started:
        raise HTTPException(status_code=409, detail="Pipeline already running")
    return {"success": True, "message": "pipeline run started"}


@router.post("/pipeline/stop")
async def stop_pipeline():
    return runner.pause()


@router.post("/pipeline/resume")
async def resume_pipeline():
    return runner.resume()


@router.get("/pipeline/status")
async def get_status():
    try:
        docs = [d async for d in db.pipeline_runs.find({}).sort("started_at", -1).limit(1)]
    except Exception:
        log.exception("get_status: failed to load latest pipeline run")
        raise HTTPException(status_code=503, detail="Database unavailable")
    run = serialize_run(docs[0]) if docs else None
    return {"running": runner.is_running(), "paused": runner.is_paused(), "run": run}


@router.get("/pipeline/stats")
async def get_pipeline_stats():
    recent_runs = await load_recent_runs()
    totals = await load_totals()
    config_payload = await build_config_payload()
    return {
        "running": runner.is_running(),
        "paused": runner.is_paused(),
        "live": progress.snapshot(),
        "recent_runs": recent_runs,
        "totals": totals,
        "config": config_payload,
    }


async def load_recent_runs():
    try:
        docs = [d async for d in db.pipeline_runs.find({}).sort("started_at", -1).limit(10)]
    except Exception:
        log.exception("load_recent_runs: failed to load recent pipeline runs")
        raise HTTPException(status_code=503, detail="Database unavailable")
    return [serialize_recent_run(doc) for doc in docs]


async def load_totals():
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        raw_items = await db.raw.count_documents({})
        raw_embedded = await db.raw.count_documents({"embedding": {"$ne": None}})
        raw_ungrouped = await db.raw.count_documents({"story_id": None})
        raw_last_24h = await db.raw.count_documents({"ingested_at": {"$gte": cutoff}})

        stories_totals = {
            "pending": await db.stories.count_documents({"status": "pending"}),
            "filtered": await db.stories.count_documents({"status": "filtered"}),
            "scored": await db.stories.count_documents({"status": "scored"}),
            "dirty": await db.stories.count_documents({"dirty": True}),
            "total": await db.stories.count_documents({}),
        }

        sources_totals = {
            "rss": {
                "enabled": await db.sources.count_documents({"type": "rss", "enabled": True}),
                "disabled": await db.sources.count_documents({"type": "rss", "enabled": False}),
            },
            "telegram": {
                "enabled": await db.sources.count_documents({"type": "telegram", "enabled": True}),
                "disabled": await db.sources.count_documents({"type": "telegram", "enabled": False}),
            },
        }
    except Exception:
        log.exception("load_totals: failed to load pipeline totals")
        raise HTTPException(status_code=503, detail="Database unavailable")

    items_by_source = await load_items_by_source()

    return {
        "raw_items": raw_items,
        "raw_embedded": raw_embedded,
        "raw_ungrouped": raw_ungrouped,
        "raw_last_24h": raw_last_24h,
        "stories": stories_totals,
        "sources": sources_totals,
        "items_by_source": items_by_source,
    }


async def load_items_by_source():
    try:
        pipeline = [
            {"$group": {"_id": {"type": "$source_type", "name": "$source_name"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 15},
        ]
        cursor = await db.raw.aggregate(pipeline)
        rows = [row async for row in cursor]
    except Exception:
        log.exception("load_items_by_source: failed to aggregate items by source")
        raise HTTPException(status_code=503, detail="Database unavailable")

    return [
        {"source_name": row["_id"]["name"], "source_type": row["_id"]["type"], "count": row["count"]}
        for row in rows
    ]


async def build_config_payload():
    try:
        models = await settings_module.get_effective_models()
    except Exception:
        log.exception("build_config_payload: failed to read effective models")
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {
        "poll_interval_minutes": config.POLL_INTERVAL_MINUTES,
        "sim_high": config.SIM_HIGH,
        "sim_low": config.SIM_LOW,
        "active_window_hours": config.ACTIVE_WINDOW_HOURS,
        "decay_half_life_hours": config.DECAY_HALF_LIFE_HOURS,
        "embed_model": config.EMBED_MODEL,
        "filter_model": models["filter_model"],
        "scoring_model": models["scoring_model"],
    }


def serialize_run(run):
    return {
        "trigger": run["trigger"],
        "started_at": run["started_at"].isoformat(),
        "finished_at": run["finished_at"].isoformat() if run["finished_at"] else None,
        "status": run["status"],
        "counts": run["counts"],
        "errors": run["errors"],
    }


def serialize_recent_run(doc):
    payload = serialize_run(doc)
    payload["id"] = str(doc["_id"])
    payload["stages"] = doc.get("stages", {})
    payload["duration_seconds"] = compute_duration_seconds(doc.get("started_at"), doc.get("finished_at"))
    return payload


def compute_duration_seconds(started_at, finished_at):
    if started_at is None or finished_at is None:
        return None
    return (finished_at - started_at).total_seconds()

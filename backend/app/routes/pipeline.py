from fastapi import APIRouter, Depends, HTTPException, Request

from app import db
from app.auth import require_auth
from app.pipeline import runner

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
    docs = [d async for d in db.pipeline_runs.find({}).sort("started_at", -1).limit(1)]
    run = serialize_run(docs[0]) if docs else None
    return {"running": runner.is_running(), "paused": runner.is_paused(), "run": run}


def serialize_run(run):
    return {
        "trigger": run["trigger"],
        "started_at": run["started_at"].isoformat(),
        "finished_at": run["finished_at"].isoformat() if run["finished_at"] else None,
        "status": run["status"],
        "counts": run["counts"],
        "errors": run["errors"],
    }

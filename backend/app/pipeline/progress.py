"""In-memory pipeline progress tracker, module-level state, no DB.

Lets a live status endpoint show what the current (or most recent) pipeline
run is doing without querying Mongo on every poll. All public functions are
non-throwing: called with no run/stage in progress, they no-op instead of
raising, since instrumentation must never break the pipeline itself.
"""

from datetime import datetime, timezone

STAGES = ["ingest", "embed", "reap", "group", "score"]  # score = process_dirty_stories: filter + score
LLM_SITES = ["filter", "verdict", "score"]


def _idle_stage():
    return {
        "status": "idle",
        "started_at": None,
        "finished_at": None,
        "current": 0,
        "total": None,
        "detail": None,
    }


def _zero_llm_bucket():
    return {"calls": 0, "failures": 0}


# --- module state ---

_run = None  # {trigger, started_at, finished_at, status, stage} | None
_stages = {name: _idle_stage() for name in STAGES}
_counts = {}
_llm = {site: _zero_llm_bucket() for site in LLM_SITES}  # cumulative since process boot
_llm_run = {site: _zero_llm_bucket() for site in LLM_SITES}  # reset each run
_embed = _zero_llm_bucket()  # cumulative since process boot
_embed_run = _zero_llm_bucket()  # reset each run
_last_error = None


def begin_run(trigger):
    """Reset all per-run state; call once at the top of a pipeline run."""
    global _run, _stages, _counts, _llm_run, _embed_run, _last_error
    _run = {"trigger": trigger, "started_at": datetime.now(timezone.utc), "finished_at": None, "status": None, "stage": None}
    _stages = {name: _idle_stage() for name in STAGES}
    _counts = {}
    _llm_run = {site: _zero_llm_bucket() for site in LLM_SITES}
    _embed_run = _zero_llm_bucket()
    _last_error = None


def begin_stage(name, total=None):
    """Mark a stage running and record it as the run's current stage."""
    stage = _stages.get(name)
    if stage is None:
        return
    stage["status"] = "running"
    stage["started_at"] = datetime.now(timezone.utc)
    stage["finished_at"] = None
    stage["current"] = 0
    stage["total"] = total
    stage["detail"] = None
    if _run is not None:
        _run["stage"] = name


def update_stage(current=None, total=None, detail=None, counts=None):
    """Update the run's current stage in place. No-ops if no stage is running."""
    global _counts
    if _run is None or _run.get("stage") is None:
        return
    stage = _stages.get(_run["stage"])
    if stage is None:
        return
    if current is not None:
        stage["current"] = current
    if total is not None:
        stage["total"] = total
    if detail is not None:
        stage["detail"] = detail
    if counts is not None:
        _counts = dict(counts)


def end_stage(name, status="done"):
    """Finish one stage. Clears it from the run's current stage if it was that stage."""
    stage = _stages.get(name)
    if stage is None:
        return
    stage["status"] = status
    stage["finished_at"] = datetime.now(timezone.utc)
    if _run is not None and _run.get("stage") == name:
        _run["stage"] = None


def end_run(status):
    """Finish the run. If it errored mid-stage, that stage is marked errored too."""
    if _run is None:
        return
    _mark_running_stage_errored(status)
    _run["finished_at"] = datetime.now(timezone.utc)
    _run["status"] = status
    _run["stage"] = None


def record_llm_call(site, ok):
    """site is one of LLM_SITES (filter/verdict/score). Tallies cumulative + per-run."""
    _bump_llm_bucket(_llm.get(site), ok)
    _bump_llm_bucket(_llm_run.get(site), ok)


def record_embed_call(ok):
    """Tallies one embedding API call, cumulative + per-run."""
    _bump_llm_bucket(_embed, ok)
    _bump_llm_bucket(_embed_run, ok)


def record_error(message):
    """Record the most recent pipeline error message for live display."""
    global _last_error
    _last_error = message


def snapshot():
    """JSON-safe dict of current run/stage/counter state for the stats route."""
    return {
        "run": _run_snapshot(),
        "stages": {name: _stage_snapshot(name) for name in STAGES},
        "counts": dict(_counts),
        "llm": {"run": _llm_group_snapshot(_llm_run), "total": _llm_group_snapshot(_llm)},
        "embed": {"run": dict(_embed_run), "total": dict(_embed)},
        "last_error": _last_error,
    }


def stage_summary():
    """Per-stage timings for the runner to persist onto the pipeline_runs doc."""
    summary = {}
    for name in STAGES:
        stage = _stages.get(name, _idle_stage())
        summary[name] = {
            "status": stage["status"],
            "duration_seconds": _stage_duration(stage),
            "current": stage["current"],
            "total": stage["total"],
        }
    return summary


# --- helpers ---


def _mark_running_stage_errored(status):
    if status != "error":
        return
    stage_name = _run.get("stage")
    if stage_name is None:
        return
    stage = _stages.get(stage_name)
    if stage is None or stage["status"] != "running":
        return
    end_stage(stage_name, "error")


def _bump_llm_bucket(bucket, ok):
    if bucket is None:
        return
    bucket["calls"] += 1
    if not ok:
        bucket["failures"] += 1


def _iso(value):
    return value.isoformat() if value else None


def _run_snapshot():
    if _run is None:
        return None
    return {
        "trigger": _run.get("trigger"),
        "started_at": _iso(_run.get("started_at")),
        "finished_at": _iso(_run.get("finished_at")),
        "status": _run.get("status"),
        "stage": _run.get("stage"),
    }


def _stage_duration(stage):
    if stage["started_at"] is None:
        return None
    end = stage["finished_at"] or datetime.now(timezone.utc)
    return (end - stage["started_at"]).total_seconds()


def _stage_snapshot(name):
    stage = _stages.get(name, _idle_stage())
    return {
        "status": stage["status"],
        "started_at": _iso(stage["started_at"]),
        "finished_at": _iso(stage["finished_at"]),
        "current": stage["current"],
        "total": stage["total"],
        "detail": stage["detail"],
        "duration_seconds": _stage_duration(stage),
    }


def _llm_group_snapshot(buckets):
    return {site: dict(buckets[site]) for site in buckets}

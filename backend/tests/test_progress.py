import json

import pytest

from app.pipeline import progress


def _reset_module_state():
    """Force every module global back to a boot-like state.

    _llm/_embed are process-global cumulative counters that real pipeline code
    (filter/score/verdict/embed, exercised by other test files) also increments,
    so this must run BEFORE each test too, not only after — otherwise leftover
    calls from a previously-run test file leak into this file's assertions.
    """
    progress._run = None
    progress._stages = {name: progress._idle_stage() for name in progress.STAGES}
    progress._counts = {}
    progress._llm = {site: progress._zero_llm_bucket() for site in progress.LLM_SITES}
    progress._llm_run = {site: progress._zero_llm_bucket() for site in progress.LLM_SITES}
    progress._embed = progress._zero_llm_bucket()
    progress._embed_run = progress._zero_llm_bucket()
    progress._last_error = None


@pytest.fixture(autouse=True)
def reset_progress():
    """Module-level state is process-global; give every test a fresh boot-like state."""
    _reset_module_state()
    progress.begin_run("test")
    yield
    _reset_module_state()


def test_begin_run_resets_stages_to_idle():
    progress.begin_stage("ingest", total=10)
    progress.update_stage(current=5, detail="in progress")
    progress.record_llm_call("filter", True)
    progress.record_embed_call(False)

    progress.begin_run("second")

    snap = progress.snapshot()
    assert snap["run"]["trigger"] == "second"
    assert snap["run"]["stage"] is None
    assert snap["run"]["status"] is None
    assert snap["run"]["finished_at"] is None
    for name in progress.STAGES:
        stage = snap["stages"][name]
        assert stage["status"] == "idle"
        assert stage["current"] == 0
        assert stage["total"] is None
        assert stage["detail"] is None
        assert stage["started_at"] is None
        assert stage["finished_at"] is None
    # per-run counters reset, but cumulative totals survive across runs
    assert snap["llm"]["run"]["filter"] == {"calls": 0, "failures": 0}
    assert snap["llm"]["total"]["filter"] == {"calls": 1, "failures": 0}
    assert snap["embed"]["run"] == {"calls": 0, "failures": 0}
    assert snap["embed"]["total"] == {"calls": 1, "failures": 1}
    assert snap["counts"] == {}


def test_begin_stage_marks_running_and_sets_current_run_stage():
    progress.begin_stage("embed", total=20)

    snap = progress.snapshot()
    stage = snap["stages"]["embed"]
    assert stage["status"] == "running"
    assert stage["total"] == 20
    assert stage["current"] == 0
    assert stage["started_at"] is not None
    assert stage["finished_at"] is None
    assert snap["run"]["stage"] == "embed"


def test_update_stage_sets_current_total_detail_and_counts():
    progress.begin_stage("group", total=5)

    progress.update_stage(current=3, total=8, detail="item 3", counts={"ingested": 4})

    snap = progress.snapshot()
    stage = snap["stages"]["group"]
    assert stage["current"] == 3
    assert stage["total"] == 8
    assert stage["detail"] == "item 3"
    assert snap["counts"] == {"ingested": 4}


def test_update_stage_only_touches_the_active_stage():
    progress.begin_stage("group", total=5)

    progress.update_stage(current=2)

    snap = progress.snapshot()
    assert snap["stages"]["group"]["current"] == 2
    assert snap["stages"]["ingest"]["current"] == 0


def test_end_stage_sets_status_and_duration_and_clears_run_stage():
    progress.begin_stage("reap")

    progress.end_stage("reap", "done")

    snap = progress.snapshot()
    stage = snap["stages"]["reap"]
    assert stage["status"] == "done"
    assert stage["finished_at"] is not None
    assert stage["duration_seconds"] is not None
    assert stage["duration_seconds"] >= 0
    assert snap["run"]["stage"] is None


def test_end_stage_defaults_to_done_status():
    progress.begin_stage("ingest")

    progress.end_stage("ingest")

    assert progress.snapshot()["stages"]["ingest"]["status"] == "done"


def test_record_llm_call_increments_run_and_total_counters_and_failures():
    progress.record_llm_call("score", True)
    progress.record_llm_call("score", False)

    snap = progress.snapshot()
    assert snap["llm"]["run"]["score"] == {"calls": 2, "failures": 1}
    assert snap["llm"]["total"]["score"] == {"calls": 2, "failures": 1}
    # untouched sites stay zero
    assert snap["llm"]["run"]["filter"] == {"calls": 0, "failures": 0}
    assert snap["llm"]["total"]["verdict"] == {"calls": 0, "failures": 0}


def test_record_llm_call_run_bucket_resets_but_total_survives_new_run():
    progress.record_llm_call("verdict", True)

    progress.begin_run("another")

    snap = progress.snapshot()
    assert snap["llm"]["total"]["verdict"] == {"calls": 1, "failures": 0}
    assert snap["llm"]["run"]["verdict"] == {"calls": 0, "failures": 0}


def test_record_embed_call_increments_run_and_total_counters():
    progress.record_embed_call(True)
    progress.record_embed_call(False)

    snap = progress.snapshot()
    assert snap["embed"]["run"] == {"calls": 2, "failures": 1}
    assert snap["embed"]["total"] == {"calls": 2, "failures": 1}


def test_end_run_error_marks_the_running_stage_error():
    progress.begin_stage("score", total=1)

    progress.end_run("error")

    snap = progress.snapshot()
    assert snap["run"]["status"] == "error"
    assert snap["run"]["finished_at"] is not None
    assert snap["run"]["stage"] is None
    assert snap["stages"]["score"]["status"] == "error"
    assert snap["stages"]["score"]["finished_at"] is not None


def test_end_run_success_leaves_already_finished_stage_alone():
    progress.begin_stage("ingest", total=1)
    progress.end_stage("ingest", "done")

    progress.end_run("success")

    snap = progress.snapshot()
    assert snap["stages"]["ingest"]["status"] == "done"
    assert snap["run"]["status"] == "success"


def test_end_run_error_with_no_active_stage_does_not_raise():
    progress.end_run("error")

    snap = progress.snapshot()
    assert snap["run"]["status"] == "error"
    for name in progress.STAGES:
        assert snap["stages"][name]["status"] == "idle"


def test_snapshot_is_json_serializable_and_includes_all_stages():
    progress.begin_stage("ingest", total=3)
    progress.update_stage(current=1, detail="rss: some-feed")
    progress.record_llm_call("filter", True)
    progress.record_embed_call(True)

    snap = progress.snapshot()

    serialized = json.dumps(snap)
    assert isinstance(serialized, str)
    assert set(snap["stages"]) == set(progress.STAGES)
    assert len(snap["stages"]) == 5
    assert set(snap) == {"run", "stages", "counts", "llm", "embed", "last_error"}
    assert set(snap["llm"]) == {"run", "total"}
    assert set(snap["embed"]) == {"run", "total"}


def test_update_stage_with_no_active_stage_does_not_raise():
    # fixture's begin_run("test") leaves every stage idle and _run["stage"] None
    progress.update_stage(current=99, total=10, detail="ignored", counts={"x": 1})

    snap = progress.snapshot()
    assert snap["run"]["stage"] is None
    assert snap["counts"] == {}
    for name in progress.STAGES:
        assert snap["stages"][name]["current"] == 0


def test_update_stage_with_no_run_at_all_does_not_raise():
    progress._run = None

    progress.update_stage(current=1, total=2, detail="x")  # must not raise

    assert progress._run is None


def test_unknown_stage_name_is_ignored_without_raising():
    progress.begin_stage("not-a-real-stage", total=1)  # must not raise
    progress.end_stage("not-a-real-stage")  # must not raise

    snap = progress.snapshot()
    assert snap["run"]["stage"] is None
    assert set(snap["stages"]) == set(progress.STAGES)


def test_stage_summary_reflects_status_and_timing():
    progress.begin_stage("group", total=4)
    progress.update_stage(current=4)
    progress.end_stage("group", "done")

    summary = progress.stage_summary()

    assert set(summary) == set(progress.STAGES)
    group_summary = summary["group"]
    assert group_summary["status"] == "done"
    assert group_summary["current"] == 4
    assert group_summary["total"] == 4
    assert group_summary["duration_seconds"] is not None
    assert group_summary["duration_seconds"] >= 0

    idle_summary = summary["ingest"]
    assert idle_summary["status"] == "idle"
    assert idle_summary["duration_seconds"] is None
    assert idle_summary["current"] == 0
    assert idle_summary["total"] is None


def test_record_error_sets_last_error():
    progress.record_error("boom")

    assert progress.snapshot()["last_error"] == "boom"

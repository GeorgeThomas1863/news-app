import pytest

from app import config
from app.pipeline import filter as importance_filter
from app.pipeline import score, verdict


@pytest.fixture
def call_log(monkeypatch):
    """Patch llm.call_json in every consumer module; queue of results, log of calls."""
    state = {"queue": [], "calls": []}

    async def fake_call_json(model, system, user_text, schema):
        state["calls"].append(
            {"model": model, "system": system, "user_text": user_text, "schema": schema}
        )
        return state["queue"].pop(0)

    monkeypatch.setattr(verdict.llm, "call_json", fake_call_json)
    return state


async def test_verdict_true_when_llm_says_same_story(call_log):
    call_log["queue"] = [{"same_story": True}]

    result = await verdict.ask_same_story(
        "New item text", headline="Existing headline", sample_texts=["item a", "item b"]
    )

    assert result is True
    call = call_log["calls"][0]
    assert call["model"] == config.FILTER_MODEL
    assert "New item text" in call["user_text"]
    assert "Existing headline" in call["user_text"]
    assert "item a" in call["user_text"]


async def test_verdict_defaults_to_false_when_llm_fails(call_log):
    call_log["queue"] = [None]

    result = await verdict.ask_same_story("Item", headline=None, sample_texts=["a"])

    assert result is False


async def test_filter_returns_bool_from_llm(call_log):
    call_log["queue"] = [{"important": False}]

    result = await importance_filter.is_possibly_important(["story text one", "story text two"])

    assert result is False
    call = call_log["calls"][0]
    assert call["model"] == config.FILTER_MODEL
    assert "story text one" in call["user_text"]


async def test_filter_returns_none_when_llm_fails(call_log):
    call_log["queue"] = [None]

    result = await importance_filter.is_possibly_important(["story text"])

    assert result is None


def _story_items():
    return [
        {"source_name": "feedA", "text": "Big event happened", "published_at": "2026-07-08T10:00:00Z"},
        {"source_name": "channelB", "text": "More on the big event", "published_at": "2026-07-08T10:05:00Z"},
    ]


async def test_score_story_returns_validated_result(call_log):
    call_log["queue"] = [
        {"score": 85, "topic": "Ukraine", "headline": "Big event", "summary": "It happened."}
    ]

    result = await score.score_story(_story_items())

    assert result == {
        "score": 85,
        "topic": "Ukraine",
        "headline": "Big event",
        "summary": "It happened.",
    }
    call = call_log["calls"][0]
    assert call["model"] == config.SCORING_MODEL
    assert "Big event happened" in call["user_text"]
    assert "feedA" in call["user_text"]
    assert call["schema"]["properties"]["topic"]["enum"] == config.TOPICS


async def test_score_story_rejects_out_of_range_score(call_log):
    call_log["queue"] = [
        {"score": 150, "topic": "Tech", "headline": "H", "summary": "S"}
    ]

    result = await score.score_story(_story_items())

    assert result is None


async def test_score_story_rejects_unknown_topic(call_log):
    call_log["queue"] = [
        {"score": 50, "topic": "Sports", "headline": "H", "summary": "S"}
    ]

    result = await score.score_story(_story_items())

    assert result is None


async def test_score_story_returns_none_when_llm_fails(call_log):
    call_log["queue"] = [None]

    result = await score.score_story(_story_items())

    assert result is None

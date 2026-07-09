from datetime import datetime, timedelta, timezone

from app import ranking


def test_compute_effective_score_zero_elapsed_equals_score():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    result = ranking.compute_effective_score(80, now, now, half_life_hours=24)
    assert result == 80


def test_compute_effective_score_one_half_life_halves_score():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    latest_item_at = now - timedelta(hours=24)
    result = ranking.compute_effective_score(80, latest_item_at, now, half_life_hours=24)
    assert result == 40


def test_compute_effective_score_two_half_lives_quarters_score():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    latest_item_at = now - timedelta(hours=48)
    result = ranking.compute_effective_score(80, latest_item_at, now, half_life_hours=24)
    assert result == 20


def test_compute_effective_score_future_timestamp_clamps_to_full_score():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    latest_item_at = now + timedelta(hours=5)
    result = ranking.compute_effective_score(80, latest_item_at, now, half_life_hours=24)
    assert result == 80


def test_rank_stories_orders_by_effective_score_descending():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    fresh_sixty = {"score": 60, "latest_item_at": now}
    day_old_ninety = {"score": 90, "latest_item_at": now - timedelta(hours=24)}

    result = ranking.rank_stories([day_old_ninety, fresh_sixty], now, half_life_hours=24)

    assert [s["score"] for s in result] == [60, 90]
    assert result[0]["effective_score"] == 60.0
    assert result[1]["effective_score"] == 45.0


def test_rank_stories_rounds_effective_score_to_two_decimals():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    story = {"score": 70, "latest_item_at": now - timedelta(hours=7)}

    result = ranking.rank_stories([story], now, half_life_hours=24)

    assert result[0]["effective_score"] == round(70 * 0.5 ** (7 / 24), 2)


def test_rank_stories_does_not_mutate_input():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    story = {"score": 70, "latest_item_at": now}
    original = dict(story)

    ranking.rank_stories([story], now, half_life_hours=24)

    assert story == original


def test_rank_stories_empty_list_returns_empty_list():
    now = datetime(2026, 7, 8, 12, 0, 0, tzinfo=timezone.utc)
    assert ranking.rank_stories([], now, half_life_hours=24) == []

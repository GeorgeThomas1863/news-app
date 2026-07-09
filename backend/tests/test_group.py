import pytest

from app.pipeline.group import cosine_similarity, decide_placement, find_best_candidate


def test_cosine_similarity_identical_vectors_returns_one():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 2.0, 3.0]

    result = cosine_similarity(a, b)

    assert result == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_returns_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]

    result = cosine_similarity(a, b)

    assert result == pytest.approx(0.0)


def test_cosine_similarity_known_angle_returns_expected_value():
    a = [1.0, 0.0]
    b = [1.0, 1.0]

    result = cosine_similarity(a, b)

    assert result == pytest.approx(0.7071067811865475)


def test_cosine_similarity_length_mismatch_raises_value_error():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 2.0]

    with pytest.raises(ValueError):
        cosine_similarity(a, b)


def test_find_best_candidate_picks_max_item_across_stories():
    embedding = [1.0, 0.0]
    candidates = [
        {
            "story_id": "story-a",
            "embeddings": [[0.0, 1.0], [0.5, 0.8660254037844387]],
        },
        {
            "story_id": "story-b",
            "embeddings": [[0.7071067811865476, 0.7071067811865476]],
        },
    ]

    result = find_best_candidate(embedding, candidates)

    assert result["story_id"] == "story-b"
    assert result["similarity"] == pytest.approx(0.7071067811865476)


def test_cosine_similarity_zero_vector_raises_value_error():
    a = [0.0, 0.0, 0.0]
    b = [1.0, 2.0, 3.0]

    with pytest.raises(ValueError):
        cosine_similarity(a, b)


def _candidate(story_id, vector):
    return {"story_id": story_id, "embeddings": [vector]}


def test_decide_placement_joins_above_high_threshold():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [0.9, 0.1])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "join", "story_id": "s1"}


def test_decide_placement_new_when_no_candidates():
    result = decide_placement([1.0, 0.0], [], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "new"}


def test_decide_placement_new_below_low_threshold():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [0.0, 1.0])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "new"}


def test_decide_placement_verify_in_gray_zone():
    # cosine([1,0], [1,1]) ~= 0.7071 — between 0.70 and 0.85
    result = decide_placement([1.0, 0.0], [_candidate("s1", [1.0, 1.0])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "verify", "story_id": "s1"}


def test_decide_placement_exactly_high_threshold_joins():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [1.0, 0.0])], sim_high=1.0, sim_low=0.70)
    assert result == {"action": "join", "story_id": "s1"}


def test_decide_placement_exactly_low_threshold_verifies():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [1.0, 0.0])], sim_high=1.5, sim_low=1.0)
    assert result == {"action": "verify", "story_id": "s1"}

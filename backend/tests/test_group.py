import numpy as np
import pytest

from app.pipeline.group import (
    append_to_embedding_matrix,
    build_embedding_matrix,
    decide_placement,
    find_best_candidate,
)


def _candidate(story_id, vectors):
    return {"story_id": story_id, "embedding_matrix": build_embedding_matrix(vectors)}


def test_build_embedding_matrix_normalizes_rows_to_unit_length():
    matrix = build_embedding_matrix([[3.0, 4.0], [0.0, 2.0]])

    assert np.allclose(np.linalg.norm(matrix, axis=1), 1.0)
    assert matrix[0] == pytest.approx([0.6, 0.8])
    assert matrix[1] == pytest.approx([0.0, 1.0])


def test_build_embedding_matrix_zero_vector_raises_value_error():
    with pytest.raises(ValueError):
        build_embedding_matrix([[0.0, 0.0, 0.0]])


def test_build_embedding_matrix_length_mismatch_raises_value_error():
    with pytest.raises(ValueError):
        build_embedding_matrix([[1.0, 2.0, 3.0], [1.0, 2.0]])


def test_append_to_embedding_matrix_adds_normalized_row():
    matrix = build_embedding_matrix([[1.0, 0.0]])

    grown = append_to_embedding_matrix(matrix, [0.0, 5.0])

    assert grown.shape == (2, 2)
    assert grown[0] == pytest.approx([1.0, 0.0])
    assert grown[1] == pytest.approx([0.0, 1.0])


def test_find_best_candidate_picks_max_item_across_stories():
    embedding = [1.0, 0.0]
    candidates = [
        _candidate("story-a", [[0.0, 1.0], [0.5, 0.8660254037844387]]),
        _candidate("story-b", [[0.7071067811865476, 0.7071067811865476]]),
    ]

    result = find_best_candidate(embedding, candidates)

    assert result["story_id"] == "story-b"
    assert result["similarity"] == pytest.approx(0.7071067811865476)


def test_find_best_candidate_query_length_mismatch_raises_value_error():
    with pytest.raises(ValueError):
        find_best_candidate([1.0, 0.0, 0.0], [_candidate("s1", [[1.0, 0.0]])])


def test_decide_placement_joins_above_high_threshold():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [[0.9, 0.1]])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "join", "story_id": "s1"}


def test_decide_placement_new_when_no_candidates():
    result = decide_placement([1.0, 0.0], [], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "new"}


def test_decide_placement_new_below_low_threshold():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [[0.0, 1.0]])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "new"}


def test_decide_placement_verify_in_gray_zone():
    # cosine([1,0], [1,1]) ~= 0.7071 — between 0.70 and 0.85
    result = decide_placement([1.0, 0.0], [_candidate("s1", [[1.0, 1.0]])], sim_high=0.85, sim_low=0.70)
    assert result == {"action": "verify", "story_id": "s1"}


def test_decide_placement_exactly_high_threshold_joins():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [[1.0, 0.0]])], sim_high=1.0, sim_low=0.70)
    assert result == {"action": "join", "story_id": "s1"}


def test_decide_placement_exactly_low_threshold_verifies():
    result = decide_placement([1.0, 0.0], [_candidate("s1", [[1.0, 0.0]])], sim_high=1.5, sim_low=1.0)
    assert result == {"action": "verify", "story_id": "s1"}

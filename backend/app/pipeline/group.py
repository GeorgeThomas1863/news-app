import numpy as np


def decide_placement(embedding, candidates, sim_high, sim_low):
    """Pure CPU — the runner calls this off the event loop via asyncio.to_thread."""
    best = find_best_candidate(embedding, candidates)
    if best is None:
        return {"action": "new"}
    if best["similarity"] >= sim_high:
        return {"action": "join", "story_id": best["story_id"]}
    if best["similarity"] < sim_low:
        return {"action": "new"}
    return {"action": "verify", "story_id": best["story_id"]}


def find_best_candidate(embedding, candidates):
    if not candidates:
        return None

    query = build_embedding_matrix([embedding])[0]
    best = None
    for candidate in candidates:
        similarity = float(np.max(candidate["embedding_matrix"] @ query))
        if best is None or similarity > best["similarity"]:
            best = {"story_id": candidate["story_id"], "similarity": similarity}
    return best


def append_to_embedding_matrix(matrix, embedding):
    return np.vstack([matrix, build_embedding_matrix([embedding])])


def build_embedding_matrix(embeddings):
    """Row-normalized float matrix, so cosine similarity is a plain dot product."""
    matrix = np.asarray(embeddings, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0.0):
        raise ValueError("build_embedding_matrix: vectors must not be zero-length")
    return matrix / norms

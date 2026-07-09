def cosine_similarity(a, b):
    if len(a) != len(b):
        raise ValueError("cosine_similarity: vectors must be the same length")

    dot = 0.0
    mag_a = 0.0
    mag_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        mag_a += x * x
        mag_b += y * y

    if mag_a == 0.0 or mag_b == 0.0:
        raise ValueError("cosine_similarity: vectors must not be zero-length")

    return dot / ((mag_a**0.5) * (mag_b**0.5))


def decide_placement(embedding, candidates, sim_high, sim_low):
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

    best = None
    for candidate in candidates:
        for item_embedding in candidate["embeddings"]:
            similarity = cosine_similarity(embedding, item_embedding)
            if best is None or similarity > best["similarity"]:
                best = {"story_id": candidate["story_id"], "similarity": similarity}
    return best

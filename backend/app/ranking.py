def compute_effective_score(score, latest_item_at, now, half_life_hours):
    hours_elapsed = (now - latest_item_at).total_seconds() / 3600
    if hours_elapsed < 0:
        hours_elapsed = 0

    return score * 0.5 ** (hours_elapsed / half_life_hours)


def rank_stories(story_docs, now, half_life_hours):
    ranked = []
    for story in story_docs:
        effective = compute_effective_score(story["score"], story["latest_item_at"], now, half_life_hours)
        ranked.append({**story, "effective_score": round(effective, 2)})

    ranked.sort(key=lambda s: s["effective_score"], reverse=True)
    return ranked

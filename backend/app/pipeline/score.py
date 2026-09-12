import logging

from app import config, prompts, settings
from app.pipeline import llm, progress

log = logging.getLogger(__name__)

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "topic": {"type": "string", "enum": config.TOPICS},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["score", "topic", "headline", "summary"],
    "additionalProperties": False,
}


async def score_story(items):
    """Sonnet structured scoring of one story. Validated result dict, or None (story stays dirty)."""
    user_text = build_scoring_input(items)
    models = await settings.get_effective_models()
    result = await llm.call_json(models["scoring_model"], prompts.SCORING_SYSTEM_PROMPT, user_text, SCHEMA)
    if result is None:
        progress.record_llm_call("score", False)
        return None
    if not validate_score_result(result):
        log.error("scoring result failed validation: %s", result)
        progress.record_llm_call("score", False)
        return None
    progress.record_llm_call("score", True)
    return result


def build_scoring_input(items):
    parts = [f"Story with {len(items)} source item(s). Allowed topics: {', '.join(config.TOPICS)}."]
    for item in items:
        parts.append(f"[{item['source_name']} @ {item['published_at']}]\n{item['text']}")
    return "\n\n".join(parts)


def validate_score_result(result):
    score = result.get("score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        return False
    if result.get("topic") not in config.TOPICS:
        return False
    if not result.get("headline") or not result.get("summary"):
        return False
    return True

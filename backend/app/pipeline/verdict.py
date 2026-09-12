from app import prompts, settings
from app.pipeline import llm, progress

SCHEMA = {
    "type": "object",
    "properties": {"same_story": {"type": "boolean"}},
    "required": ["same_story"],
    "additionalProperties": False,
}


async def ask_same_story(item_text, headline, sample_texts):
    """Haiku verdict for gray-zone grouping. Defaults to False (new story) on LLM failure."""
    user_text = build_verdict_input(item_text, headline, sample_texts)
    models = await settings.get_effective_models()
    result = await llm.call_json(models["filter_model"], prompts.VERDICT_SYSTEM_PROMPT, user_text, SCHEMA)
    progress.record_llm_call("verdict", result is not None)
    if result is None:
        return False
    return bool(result.get("same_story", False))


def build_verdict_input(item_text, headline, sample_texts):
    parts = []
    if headline:
        parts.append(f"Existing story headline: {headline}")
    parts.append("Existing story items:")
    for text in sample_texts:
        parts.append(f"- {text}")
    parts.append(f"New item:\n{item_text}")
    return "\n".join(parts)

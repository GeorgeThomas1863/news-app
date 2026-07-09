from app import config, prompts
from app.pipeline import llm

SCHEMA = {
    "type": "object",
    "properties": {"same_story": {"type": "boolean"}},
    "required": ["same_story"],
    "additionalProperties": False,
}


async def ask_same_story(item_text, headline, sample_texts):
    """Haiku verdict for gray-zone grouping. Defaults to False (new story) on LLM failure."""
    user_text = build_verdict_input(item_text, headline, sample_texts)
    result = await llm.call_json(config.FILTER_MODEL, prompts.VERDICT_SYSTEM_PROMPT, user_text, SCHEMA)
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

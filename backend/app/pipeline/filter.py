from app import config, prompts
from app.pipeline import llm

SCHEMA = {
    "type": "object",
    "properties": {"important": {"type": "boolean"}},
    "required": ["important"],
    "additionalProperties": False,
}


async def is_possibly_important(story_texts):
    """Haiku importance gate. True/False verdict; None when the LLM failed (story stays dirty)."""
    user_text = build_filter_input(story_texts)
    result = await llm.call_json(config.FILTER_MODEL, prompts.FILTER_SYSTEM_PROMPT, user_text, SCHEMA)
    if result is None:
        return None
    return bool(result.get("important", False))


def build_filter_input(story_texts):
    parts = ["Story items:"]
    for text in story_texts:
        parts.append(f"- {text}")
    return "\n".join(parts)

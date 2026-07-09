import json
import logging

import anthropic

from app import config

log = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 1024

_client = None


def get_client():
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


async def call_json(model, system, user_text, schema):
    """Structured-output call; parsed dict, or None after one malformed retry / API failure."""
    for attempt in range(2):
        try:
            response = await get_client().messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_text}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except (anthropic.APIError, anthropic.APIConnectionError) as error:
            log.error("llm call failed (model=%s): %s", model, error)
            return None

        text = extract_text(response)
        if text is None:
            log.warning("llm response had no text block (model=%s, attempt=%d)", model, attempt + 1)
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            log.warning("malformed llm json (model=%s, attempt=%d)", model, attempt + 1)

    log.error("llm produced no valid json after retry (model=%s)", model)
    return None


def extract_text(response):
    for block in response.content:
        if block.type == "text":
            return block.text
    return None

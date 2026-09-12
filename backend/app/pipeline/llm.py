import json
import logging

import anthropic
import openai

from app import config

log = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 1024

_anthropic_client = None
_openai_client = None


def get_client():
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
    return _anthropic_client


def get_openai_client():
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


async def call_json(model, system, user_text, schema):
    """Structured-output call; parsed dict, or None after one malformed retry / API failure."""
    if model.startswith("claude-"):
        return await call_json_anthropic(model, system, user_text, schema)
    if model.startswith("gpt-"):
        return await call_json_openai(model, system, user_text, schema)

    log.error("llm call failed: unknown model provider (model=%s)", model)
    return None


async def call_json_anthropic(model, system, user_text, schema):
    for attempt in range(2):
        try:
            response = await get_client().messages.create(
                model=model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_text}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.AnthropicError as error:
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


async def call_json_openai(model, system, user_text, schema):
    for attempt in range(2):
        try:
            response = await get_openai_client().chat.completions.create(
                model=model,
                max_completion_tokens=MAX_OUTPUT_TOKENS,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "response",
                        "schema": schema,
                        "strict": True,
                    },
                },
            )
        except openai.OpenAIError as error:
            log.error("llm call failed (model=%s): %s", model, error)
            return None

        text = extract_openai_text(response)
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


def extract_openai_text(response):
    if not response.choices:
        return None
    return response.choices[0].message.content

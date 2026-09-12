import json
from types import SimpleNamespace

import anthropic
import httpx
import openai
import pytest

from app.pipeline import llm

SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "boolean"}},
    "required": ["answer"],
    "additionalProperties": False,
}


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=response)]
        )


def fake_client(monkeypatch, responses):
    messages = FakeMessages(responses)
    monkeypatch.setattr(llm, "get_client", lambda: SimpleNamespace(messages=messages))
    return messages


class FakeChatCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        message = SimpleNamespace(content=response)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def fake_openai_client(monkeypatch, responses):
    completions = FakeChatCompletions(responses)
    chat = SimpleNamespace(completions=completions)
    monkeypatch.setattr(llm, "get_openai_client", lambda: SimpleNamespace(chat=chat))
    return completions


async def test_call_json_returns_parsed_dict_and_sends_structured_output(monkeypatch):
    messages = fake_client(monkeypatch, [json.dumps({"answer": True})])

    result = await llm.call_json("claude-some-model", "system prompt", "user text", SCHEMA)

    assert result == {"answer": True}
    call = messages.calls[0]
    assert call["model"] == "claude-some-model"
    assert call["system"] == "system prompt"
    assert call["messages"] == [{"role": "user", "content": "user text"}]
    assert call["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}
    assert "temperature" not in call


async def test_call_json_retries_once_on_malformed_json(monkeypatch):
    messages = fake_client(monkeypatch, ["{not json", json.dumps({"answer": False})])

    result = await llm.call_json("claude-some-model", "system", "user", SCHEMA)

    assert result == {"answer": False}
    assert len(messages.calls) == 2


async def test_call_json_returns_none_after_two_malformed_responses(monkeypatch):
    messages = fake_client(monkeypatch, ["{not json", "also bad"])

    result = await llm.call_json("claude-some-model", "system", "user", SCHEMA)

    assert result is None
    assert len(messages.calls) == 2


async def test_call_json_returns_none_on_api_error(monkeypatch):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIStatusError(
        "overloaded",
        response=httpx.Response(529, request=request),
        body=None,
    )
    messages = fake_client(monkeypatch, [error])

    result = await llm.call_json("claude-some-model", "system", "user", SCHEMA)

    assert result is None
    assert len(messages.calls) == 1


async def test_call_json_openai_returns_parsed_dict_and_sends_json_schema(monkeypatch):
    completions = fake_openai_client(monkeypatch, [json.dumps({"answer": True})])

    result = await llm.call_json("gpt-some-model", "system prompt", "user text", SCHEMA)

    assert result == {"answer": True}
    call = completions.calls[0]
    assert call["model"] == "gpt-some-model"
    assert call["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user text"},
    ]
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "response", "schema": SCHEMA, "strict": True},
    }


async def test_call_json_openai_retries_once_on_malformed_json(monkeypatch):
    completions = fake_openai_client(monkeypatch, ["{not json", json.dumps({"answer": False})])

    result = await llm.call_json("gpt-some-model", "system", "user", SCHEMA)

    assert result == {"answer": False}
    assert len(completions.calls) == 2


async def test_call_json_openai_returns_none_after_two_malformed_responses(monkeypatch):
    completions = fake_openai_client(monkeypatch, ["{not json", "also bad"])

    result = await llm.call_json("gpt-some-model", "system", "user", SCHEMA)

    assert result is None
    assert len(completions.calls) == 2


async def test_call_json_openai_returns_none_on_api_error(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = openai.APIConnectionError(request=request)
    completions = fake_openai_client(monkeypatch, [error])

    result = await llm.call_json("gpt-some-model", "system", "user", SCHEMA)

    assert result is None
    assert len(completions.calls) == 1


async def test_call_json_unknown_prefix_returns_none(monkeypatch):
    result = await llm.call_json("mystery-model", "system", "user", SCHEMA)

    assert result is None

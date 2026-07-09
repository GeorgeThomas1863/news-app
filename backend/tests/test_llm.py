import json
from types import SimpleNamespace

import anthropic
import httpx
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


async def test_call_json_returns_parsed_dict_and_sends_structured_output(monkeypatch):
    messages = fake_client(monkeypatch, [json.dumps({"answer": True})])

    result = await llm.call_json("some-model", "system prompt", "user text", SCHEMA)

    assert result == {"answer": True}
    call = messages.calls[0]
    assert call["model"] == "some-model"
    assert call["system"] == "system prompt"
    assert call["messages"] == [{"role": "user", "content": "user text"}]
    assert call["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}
    assert "temperature" not in call


async def test_call_json_retries_once_on_malformed_json(monkeypatch):
    messages = fake_client(monkeypatch, ["{not json", json.dumps({"answer": False})])

    result = await llm.call_json("some-model", "system", "user", SCHEMA)

    assert result == {"answer": False}
    assert len(messages.calls) == 2


async def test_call_json_returns_none_after_two_malformed_responses(monkeypatch):
    messages = fake_client(monkeypatch, ["{not json", "also bad"])

    result = await llm.call_json("some-model", "system", "user", SCHEMA)

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

    result = await llm.call_json("some-model", "system", "user", SCHEMA)

    assert result is None
    assert len(messages.calls) == 1

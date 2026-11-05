import pytest
import requests

import llm_client
from llm_client import LLMClient, extract_json


def test_extract_json_plain_fenced_and_chatty():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": [1, 2]} Hope that helps.') == {"a": [1, 2]}
    assert extract_json("[1, 2]") == [1, 2]


def test_extract_json_without_json_raises():
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_client_requires_api_key(monkeypatch):
    monkeypatch.setattr(llm_client, "OPENROUTER_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        LLMClient()


class FakeResponse:
    def __init__(self, status=200, data=None, text=""):
        self.status_code, self._data, self.text = status, data, text

    def json(self):
        if self._data is None:
            raise ValueError("not json")
        return self._data


def ok(content):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(llm_client, "OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: None)
    return LLMClient()


def queue_responses(monkeypatch, responses):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(llm_client.requests, "post", fake_post)
    return calls


def test_chat_retries_rate_limit_then_succeeds(client, monkeypatch):
    calls = queue_responses(monkeypatch, [FakeResponse(429), ok("  hello  ")])
    assert client.generate("hi") == "hello"
    assert len(calls) == 2


def test_chat_gives_up_after_connection_errors(client, monkeypatch):
    err = requests.exceptions.ConnectionError("down")
    calls = queue_responses(monkeypatch, [err, err, err])
    with pytest.raises(RuntimeError, match="Could not reach"):
        client.generate("hi")
    assert len(calls) == 3


@pytest.mark.parametrize("response, message", [
    (FakeResponse(401), "rejected the API key"),
    (FakeResponse(400, text="bad"), "error 400"),
    (FakeResponse(200, {"oops": 1}), "unexpected response"),
    (ok("   "), "empty response"),
])
def test_chat_errors_are_clear(client, monkeypatch, response, message):
    queue_responses(monkeypatch, [response])
    with pytest.raises(RuntimeError, match=message):
        client.generate("hi")


def test_generate_json_retries_once_on_bad_output(client, monkeypatch):
    queue_responses(monkeypatch, [ok("not json"), ok('{"x": 1}')])
    assert client.generate_json("p") == {"x": 1}


def test_generate_json_fails_after_two_bad_replies(client, monkeypatch):
    queue_responses(monkeypatch, [ok("nope"), ok("still nope")])
    with pytest.raises(RuntimeError, match="usable structured output"):
        client.generate_json("p")

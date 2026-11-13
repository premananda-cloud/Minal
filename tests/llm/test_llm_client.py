import json

import httpx
import pytest

from minal.llm import (
    ChatMessage,
    CompletionRequest,
    LiteLLMClient,
    LLMAuthFailed,
    LLMBadRequest,
    LLMBadResponse,
    LLMConfig,
    LLMTimeout,
    LLMUnavailable,
)

REQ = CompletionRequest(messages=[ChatMessage(role="system", content="Be brief."),
                                  ChatMessage(role="user", content="Hello")])
OK_BODY = {
    "model": "minal-llm",
    "choices": [{"index": 0, "finish_reason": "stop",
                 "message": {"role": "assistant", "content": "Hi there."}}],
    "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
}


def client(handler, key="sk-test", **cfg):
    config = LLMConfig(api_key=key, **cfg)
    return LiteLLMClient(config, transport=httpx.MockTransport(handler))


def reply(status=200, body=None, text=None):
    def handler(request):
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=body)
    return handler


def test_success_maps_text_usage_and_model():
    res = client(reply(200, OK_BODY)).complete(REQ)
    assert res.text == "Hi there." and res.model == "minal-llm"
    assert res.finish_reason == "stop"
    assert (res.usage.prompt_tokens, res.usage.completion_tokens, res.usage.total_tokens) == (7, 3, 10)


def test_request_shape_url_auth_and_payload():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_BODY)

    client(handler).complete(REQ)
    assert seen["url"] == "http://127.0.0.1:4000/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    b = seen["body"]
    assert b["model"] == "minal-llm" and b["temperature"] == 0.2 and b["max_tokens"] == 512
    assert b["stream"] is False and "stop" not in b
    assert b["messages"] == [{"role": "system", "content": "Be brief."},
                             {"role": "user", "content": "Hello"}]


def test_no_key_sends_no_auth_header_and_stop_is_forwarded():
    seen = {}

    def handler(request):
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_BODY)

    req = CompletionRequest(messages=REQ.messages, stop=["###"])
    client(handler, key=None).complete(req)
    assert "authorization" not in seen["headers"] and seen["body"]["stop"] == ["###"]


def test_missing_usage_defaults_to_zero():
    body = {k: v for k, v in OK_BODY.items() if k != "usage"}
    assert client(reply(200, body)).complete(REQ).usage.total_tokens == 0


@pytest.mark.parametrize("status", [401, 403])
def test_rejected_key_is_auth_failed(status):
    with pytest.raises(LLMAuthFailed) as e:
        client(reply(status, {"error": {"message": "bad key", "type": "auth_error"}})).complete(REQ)
    assert e.value.code == "llm_auth_failed" and e.value.details["status"] == status


def test_gateway_without_db_wrong_key_is_auth_failed():
    body = {"error": {"message": "No connected db.", "type": "no_db_connection", "code": "400"}}
    with pytest.raises(LLMAuthFailed):
        client(reply(400, body)).complete(REQ)


def test_other_4xx_is_bad_request_with_message():
    body = {"error": {"message": "maximum context length is 4096 tokens", "type": "invalid"}}
    with pytest.raises(LLMBadRequest) as e:
        client(reply(400, body)).complete(REQ)
    assert e.value.code == "llm_bad_request" and "4096" in e.value.message


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_overload_and_server_errors_are_unavailable(status):
    with pytest.raises(LLMUnavailable) as e:
        client(reply(status, {"error": {"message": "boom"}})).complete(REQ)
    assert e.value.code == "llm_unavailable"


def test_non_json_error_body_still_maps():
    with pytest.raises(LLMUnavailable) as e:
        client(reply(502, text="<html>Bad gateway</html>")).complete(REQ)
    assert "Bad gateway" in e.value.details["message"]


def test_connection_refused_is_unavailable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)
    with pytest.raises(LLMUnavailable):
        client(handler).complete(REQ)


def test_timeout_is_llm_timeout_not_unavailable():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)
    with pytest.raises(LLMTimeout) as e:
        client(handler).complete(REQ)
    assert e.value.code == "llm_timeout"


@pytest.mark.parametrize("body", [
    {}, {"choices": []}, {"choices": [{"message": {}}]},
    {"choices": [{"message": {"content": None}}]},
    {"choices": [{"message": {"content": 5}}]},
])
def test_malformed_success_body_is_bad_response(body):
    with pytest.raises(LLMBadResponse):
        client(reply(200, body)).complete(REQ)


def test_non_json_success_body_is_bad_response():
    with pytest.raises(LLMBadResponse):
        client(reply(200, text="not json")).complete(REQ)


def test_empty_string_completion_is_returned_not_an_error():
    body = {"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
    res = client(reply(200, body)).complete(REQ)
    assert res.text == "" and res.finish_reason == "length"


def test_context_manager_closes_client():
    with client(reply(200, OK_BODY)) as c:
        c.complete(REQ)
    with pytest.raises(RuntimeError):
        c.complete(REQ)

import pytest
from pydantic import ValidationError

from minal.llm import ChatMessage, CompletionRequest, LLMConfig


def _msg(text="hi"):
    return ChatMessage(role="user", content=text)


def test_request_defaults_are_low_temperature():
    r = CompletionRequest(messages=[_msg()])
    assert r.temperature == 0.2 and r.max_tokens == 512 and r.stop is None


def test_request_needs_at_least_one_message():
    with pytest.raises(ValidationError):
        CompletionRequest(messages=[])


@pytest.mark.parametrize("bad", [{"temperature": -0.1}, {"temperature": 2.5},
                                 {"max_tokens": 0}, {"stop": list("abcde")}])
def test_request_rejects_out_of_range(bad):
    with pytest.raises(ValidationError):
        CompletionRequest(messages=[_msg()], **bad)


def test_unknown_fields_and_roles_rejected():
    with pytest.raises(ValidationError):
        CompletionRequest(messages=[_msg()], top_p=0.9)
    with pytest.raises(ValidationError):
        ChatMessage(role="tool", content="x")


def test_config_defaults_point_at_gateway_not_vllm():
    c = LLMConfig()
    assert c.base_url == "http://127.0.0.1:4000/v1" and c.model == "minal-llm"
    assert c.api_key is None


def test_config_from_env_and_secret_is_hidden():
    c = LLMConfig.from_env({"LITELLM_MASTER_KEY": "sk-abc", "MINAL_LLM_TIMEOUT_S": "30"})
    assert c.api_key.get_secret_value() == "sk-abc" and c.timeout_s == 30.0
    assert "sk-abc" not in repr(c)
    # MINAL_LLM_API_KEY wins over the gateway master key
    c2 = LLMConfig.from_env({"MINAL_LLM_API_KEY": "sk-app", "LITELLM_MASTER_KEY": "sk-abc"})
    assert c2.api_key.get_secret_value() == "sk-app"


def test_config_from_empty_env_is_defaults():
    assert LLMConfig.from_env({}) == LLMConfig()

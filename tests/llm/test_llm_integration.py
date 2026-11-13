"""Opt-in test against the real gateway (and real vLLM behind it). Skipped by default.

    set -a; source configs/litellm.local.env; set +a
    MINAL_LLM_INTEGRATION=1 uv run pytest tests/llm/test_llm_integration.py -v
"""
import os

import pytest

from minal.llm import (
    ChatMessage,
    CompletionRequest,
    LiteLLMClient,
    LLMAuthFailed,
    LLMConfig,
    LLMUnavailable,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("MINAL_LLM_INTEGRATION") != "1",
    reason="set MINAL_LLM_INTEGRATION=1 with the gateway and vLLM running",
)

REQ = CompletionRequest(messages=[ChatMessage(role="user", content="Say hello in five words.")],
                        max_tokens=40)


def test_real_gateway_answers():
    with LiteLLMClient(LLMConfig.from_env()) as c:
        res = c.complete(REQ)
    assert res.text.strip() and res.usage.total_tokens > 0 and res.model == "minal-llm"


def test_real_gateway_rejects_wrong_key():
    cfg = LLMConfig.from_env({"MINAL_LLM_API_KEY": "sk-wrong"})
    with LiteLLMClient(cfg) as c, pytest.raises(LLMAuthFailed):
        c.complete(REQ)


def test_nothing_listening_is_unavailable():
    cfg = LLMConfig(base_url="http://127.0.0.1:9/v1", timeout_s=3)
    with LiteLLMClient(cfg) as c, pytest.raises(LLMUnavailable):
        c.complete(REQ)

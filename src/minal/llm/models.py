"""LLM contract: what callers send and what they get back."""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LLMConfig(_M):
    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str = "http://127.0.0.1:4000/v1"   # the LiteLLM gateway, never vLLM directly
    model: str = "minal-llm"                      # gateway model name (stable across models)
    api_key: SecretStr | None = None
    timeout_s: float = Field(default=120.0, gt=0)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LLMConfig:
        """MINAL_LLM_BASE_URL, MINAL_LLM_MODEL, MINAL_LLM_API_KEY (or LITELLM_MASTER_KEY),
        MINAL_LLM_TIMEOUT_S. Unset values keep the defaults above."""
        e = os.environ if env is None else env
        values: dict[str, object] = {}
        if e.get("MINAL_LLM_BASE_URL"):
            values["base_url"] = e["MINAL_LLM_BASE_URL"]
        if e.get("MINAL_LLM_MODEL"):
            values["model"] = e["MINAL_LLM_MODEL"]
        key = e.get("MINAL_LLM_API_KEY") or e.get("LITELLM_MASTER_KEY")
        if key:
            values["api_key"] = key
        if e.get("MINAL_LLM_TIMEOUT_S"):
            values["timeout_s"] = float(e["MINAL_LLM_TIMEOUT_S"])
        return cls(**values)


class ChatMessage(_M):
    role: Literal["system", "user", "assistant"]
    content: str


class CompletionRequest(_M):
    messages: list[ChatMessage] = Field(min_length=1)
    # Low by default: answers must stick to the retrieved facts. (vLLM's own default is 0.7.)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    stop: list[str] | None = Field(default=None, max_length=4)


class Usage(_M):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CompletionResult(_M):
    text: str
    model: str
    finish_reason: str | None = None     # "stop", "length", ...
    usage: Usage = Field(default_factory=Usage)

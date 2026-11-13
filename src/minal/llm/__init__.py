"""LLM layer: a port, a gateway client, stable errors and a test fake."""
from minal.llm.client import LiteLLMClient
from minal.llm.errors import (
    LLMAuthFailed,
    LLMBadRequest,
    LLMBadResponse,
    LLMError,
    LLMTimeout,
    LLMUnavailable,
)
from minal.llm.fake import FakeLLM
from minal.llm.models import (
    ChatMessage,
    CompletionRequest,
    CompletionResult,
    LLMConfig,
    Usage,
)
from minal.llm.ports import LLM

__all__ = [
    "LLM",
    "ChatMessage",
    "CompletionRequest",
    "CompletionResult",
    "FakeLLM",
    "LLMAuthFailed",
    "LLMBadRequest",
    "LLMBadResponse",
    "LLMConfig",
    "LLMError",
    "LLMTimeout",
    "LLMUnavailable",
    "LiteLLMClient",
    "Usage",
]

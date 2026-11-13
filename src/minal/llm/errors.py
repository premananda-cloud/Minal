"""Stable error types for the LLM layer. Same shape as minal.db.errors: each carries a
machine-readable `code` so the services layer, CLI and a future HTTP layer map them alike."""
from __future__ import annotations

from typing import Any


class LLMError(Exception):
    code = "llm_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class LLMUnavailable(LLMError):
    """Gateway unreachable, or it or the model failed (connection refused, 429, 5xx)."""
    code = "llm_unavailable"


class LLMTimeout(LLMError):
    code = "llm_timeout"


class LLMAuthFailed(LLMError):
    """The gateway rejected our key."""
    code = "llm_auth_failed"


class LLMBadRequest(LLMError):
    """The gateway rejected the request itself (unknown model, prompt too long, ...)."""
    code = "llm_bad_request"


class LLMBadResponse(LLMError):
    """The gateway answered, but not in the expected OpenAI chat-completions shape."""
    code = "llm_bad_response"

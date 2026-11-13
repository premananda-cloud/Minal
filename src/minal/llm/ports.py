"""What the answer chain needs from a language model. LiteLLMClient satisfies this;
tests pass FakeLLM. Synchronous, like the rest of the codebase."""
from __future__ import annotations

from typing import Protocol

from minal.llm.models import CompletionRequest, CompletionResult


class LLM(Protocol):
    def complete(self, req: CompletionRequest) -> CompletionResult: ...

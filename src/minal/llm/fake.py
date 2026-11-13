"""FakeLLM for tests: scripted replies, and a record of every request it received.
Lives in the package so any test directory can import it without path tricks."""
from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from minal.llm.models import CompletionRequest, CompletionResult


class FakeLLM:
    """`replies` is either one string (returned for every call) or a sequence consumed in
    order. Items may be a str, a CompletionResult, or an Exception instance (raised)."""

    def __init__(
        self,
        replies: str | Sequence[str | CompletionResult | Exception] = "OK",
        *,
        model: str = "fake-llm",
    ) -> None:
        self._model = model
        self._default: str | None = replies if isinstance(replies, str) else None
        self._queue = deque([] if isinstance(replies, str) else replies)
        self.calls: list[CompletionRequest] = []

    @property
    def last(self) -> CompletionRequest:
        return self.calls[-1]

    def last_prompt_text(self) -> str:
        """All message contents of the last request, for 'prompt contains X' assertions."""
        return "\n".join(m.content for m in self.last.messages)

    def complete(self, req: CompletionRequest) -> CompletionResult:
        self.calls.append(req)
        if self._default is not None:
            item: str | CompletionResult | Exception = self._default
        elif self._queue:
            item = self._queue.popleft()
        else:
            raise AssertionError("FakeLLM has no scripted replies left")
        if isinstance(item, Exception):
            raise item
        if isinstance(item, CompletionResult):
            return item
        return CompletionResult(text=item, model=self._model, finish_reason="stop")

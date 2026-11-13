"""What the answer chain needs from retrieval. minal.retrieval's retriever satisfies this;
tests pass a fake. Read-only by construction."""
from __future__ import annotations

from typing import Protocol

from minal.retrieval.models import RetrievalRequest, RetrievalResult


class Retriever(Protocol):
    def retrieve(self, req: RetrievalRequest) -> RetrievalResult: ...

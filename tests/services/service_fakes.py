"""Test helpers for the answer chain: a fake retriever and RetrievalResult builders."""
from __future__ import annotations

import typing
from datetime import date

from minal.retrieval.models import Passage, RetrievalRequest, RetrievalResult

TODAY = date(2026, 11, 13)


def kind_value(i: int = 0):
    """Some valid `Kind` value, without hard-coding what minal.db calls them."""
    from minal.db import Kind
    args = typing.get_args(Kind)
    return args[i % len(args)] if args else list(Kind)[i % len(list(Kind))]


def passage(ref: int, text: str, key: str | None = None) -> Passage:
    return Passage(ref=ref, kind=kind_value(0), key=key or f"K{ref}", version=1, text=text,
                   score=0.9, match="semantic", record={})


def result_of(*passages: Passage, as_of: date = TODAY) -> RetrievalResult:
    context = "\n\n".join(f"[{p.ref}] {p.text}" for p in passages)
    return RetrievalResult(question="q", as_of=as_of, passages=list(passages), context=context,
                           dropped=0, empty=not passages)


class FakeRetriever:
    def __init__(self, result: RetrievalResult) -> None:
        self._result = result
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        self.requests.append(req)
        return self._result

"""Orchestration: exact lookup + semantic search + budgeted context.

Takes a read-only handle. It cannot write, because it is never given a writer.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from minal.db import KeyRequest, Kind, ListRequest, NotFound, SearchRequest
from minal.db.contract import StoredRecord
from minal.db.records import record_class

from .formatter import build_context
from .lookup import (
    code_variants,
    extract_course_codes,
    is_valid_on,
    matches_filters,
)
from .models import Passage, RetrievalConfig, RetrievalRequest, RetrievalResult
from .ports import Reader


def _text(stored: StoredRecord) -> str:
    return record_class(stored.kind).model_validate(stored.record).to_text()


class Retriever:
    def __init__(
        self,
        reader: Reader,
        config: RetrievalConfig | None = None,
        *,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._reader = reader
        self._cfg = config or RetrievalConfig()
        self._today = today

    def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        day = req.as_of or self._today()
        passages: list[Passage] = []
        seen: set[tuple[Kind, str]] = set()

        def want(kind: Kind) -> bool:
            return req.kinds is None or kind in req.kinds

        def add(stored: StoredRecord, text: str, score: float | None, match: str) -> None:
            ident = (stored.kind, stored.key)
            if ident in seen:
                return
            seen.add(ident)
            passages.append(
                Passage(
                    ref=len(passages) + 1,
                    kind=stored.kind,
                    key=stored.key,
                    version=stored.version,
                    text=text,
                    score=score,
                    match=match,  # type: ignore[arg-type]
                    record=stored.record,
                )
            )

        # 1. Exact: course codes named in the question, plus who teaches them.
        if self._cfg.exact_lookup and want(Kind.COURSE):
            for course in self._exact_courses(req, day):
                add(course, _text(course), 1.0, "exact")
                if self._cfg.expand_alignments and want(Kind.ALIGNMENT):
                    for al in self._alignments(course.key, day):
                        add(al, _text(al), None, "related")

        # 2. Semantic: meaning-based search over everything requested.
        result = self._reader.search(
            SearchRequest(
                text=req.question,
                kinds=req.kinds,
                top_k=req.top_k,
                filters=req.filters,
                as_of=day,
            )
        )
        for hit in result.hits:
            if self._cfg.min_score is not None and hit.score < self._cfg.min_score:
                continue
            add(hit.stored, hit.text, hit.score, "semantic")

        context, included, dropped = build_context(passages, self._cfg.max_context_chars)
        return RetrievalResult(
            question=req.question,
            as_of=day,
            passages=included,
            context=context,
            dropped=dropped,
            empty=not included,
        )

    # -- helpers ----------------------------------------------------------------
    def _exact_courses(self, req: RetrievalRequest, day: date) -> list[StoredRecord]:
        found: list[StoredRecord] = []
        for candidate in extract_course_codes(req.question):
            for variant in code_variants(candidate):
                try:
                    stored = self._reader.get(KeyRequest(kind=Kind.COURSE, key=variant))
                except NotFound:
                    continue
                if is_valid_on(stored.record, day) and matches_filters(stored.record, req.filters):
                    found.append(stored)
                break  # a variant existed; don't try the other spellings
        return found

    def _alignments(self, course_code: str, day: date) -> list[StoredRecord]:
        res = self._reader.list_records(
            ListRequest(
                kind=Kind.ALIGNMENT,
                filters={"course_code": course_code},
                as_of=day,
                limit=self._cfg.max_alignments,
            )
        )
        return res.items

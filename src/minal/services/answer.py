"""The answer chain: question -> retrieve -> prompt -> LLM -> checked answer."""
from __future__ import annotations

from datetime import date

from minal.db.errors import InvalidRequest
from minal.llm.models import CompletionRequest, Usage
from minal.llm.ports import LLM
from minal.llm.prompts import DECLINE_PREFIX
from minal.retrieval.models import RetrievalRequest
from minal.services.citations import process_citations
from minal.services.models import Answer, AnswerConfig, CitedRecord
from minal.services.ports import Retriever
from minal.services.prompt import build_messages, build_small_talk_messages
from minal.services.smalltalk import is_small_talk


def _declines(text: str) -> bool:
    return text.lstrip().lower().replace("’", "'").startswith(DECLINE_PREFIX.lower())


class AnswerService:
    def __init__(self, retriever: Retriever, llm: LLM, config: AnswerConfig | None = None) -> None:
        self._retriever = retriever
        self._llm = llm
        self._cfg = config or AnswerConfig()

    def answer(self, question: str, *, as_of: date | None = None) -> Answer:
        q = question.strip()
        if not q:
            raise InvalidRequest("question must not be empty")

        if is_small_talk(q):
            return self._small_talk(q)

        result = self._retriever.retrieve(
            RetrievalRequest(question=q, top_k=self._cfg.top_k, as_of=as_of)
        )
        if result.empty or not result.passages:
            return Answer(question=q, text=self._cfg.no_records_text(), status="no_records",
                          as_of=result.as_of)

        completion = self._llm.complete(CompletionRequest(
            messages=build_messages(q, result, office_contact=self._cfg.office_contact),
            temperature=self._cfg.temperature,
            max_tokens=self._cfg.max_tokens,
        ))
        by_ref = {p.ref: p for p in result.passages}
        checked = process_citations(completion.text, set(by_ref))
        citations = [CitedRecord(ref=r, kind=by_ref[r].kind, key=by_ref[r].key)
                     for r in checked.cited]
        if citations:
            status = "answered"
        elif _declines(checked.text):
            status = "declined"
        else:
            status = "uncited"
        return Answer(question=q, text=checked.text, status=status, citations=citations,
                      removed_citations=checked.removed, passages=result.passages,
                      as_of=result.as_of, usage=completion.usage)

    def _small_talk(self, q: str) -> Answer:
        completion = self._llm.complete(CompletionRequest(
            messages=build_small_talk_messages(q, office_contact=self._cfg.office_contact),
            temperature=self._cfg.temperature,
            max_tokens=min(self._cfg.max_tokens, 150),
        ))
        return Answer(question=q, text=completion.text.strip(), status="chat",
                      usage=completion.usage or Usage())

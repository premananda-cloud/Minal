from datetime import date

import pytest
from db_fakes import FakeEmbedder

from minal.db import Database, EmbeddingModelMismatch, InvalidRequest, Kind
from minal.db.backends.memory import MemoryBackend
from minal.retrieval import RetrievalConfig, RetrievalRequest, Retriever


def make(db, today, **cfg):
    return Retriever(db.as_reader(), RetrievalConfig(**cfg) if cfg else None, today=today)


def keys(result):
    return [p.key for p in result.passages]


def test_semantic_search_finds_relevant_course(db, today):
    res = make(db, today).retrieve(RetrievalRequest(question="neural networks", kinds=[Kind.COURSE]))
    assert res.passages[0].key == "CS201" and res.passages[0].match == "semantic"
    assert res.context.startswith("[1] ") and not res.empty


def test_course_code_resolves_exactly_with_instructor(db, today):
    res = make(db, today).retrieve(RetrievalRequest(question="who teaches CS201?"))
    assert (res.passages[0].key, res.passages[0].match) == ("CS201", "exact")
    related = [p for p in res.passages if p.match == "related"]
    assert related and "Dr Rao" in related[0].text
    assert len(keys(res)) == len(set(keys(res)))  # no duplicates across exact/semantic


def test_code_spelling_variants_are_found(db, today):
    for q in ("credits for cs201", "credits for CS 201", "credits for CS-201"):
        res = make(db, today).retrieve(RetrievalRequest(question=q, kinds=[Kind.COURSE]))
        assert res.passages[0].key == "CS201" and res.passages[0].match == "exact", q


def test_unknown_code_falls_back_to_semantic(db, today):
    res = make(db, today).retrieve(RetrievalRequest(question="tell me about ZZ999 chemistry"))
    assert res.passages and all(p.match != "exact" for p in res.passages)


def test_exact_lookup_can_be_disabled(db, today):
    res = make(db, today, exact_lookup=False).retrieve(RetrievalRequest(question="CS201"))
    assert all(p.match == "semantic" for p in res.passages)


def test_future_records_hidden_until_as_of_reaches_them(db, today):
    now = make(db, today).retrieve(RetrievalRequest(question="quantum computing", kinds=[Kind.COURSE]))
    assert "FUT100" not in keys(now)
    later = make(db, today).retrieve(
        RetrievalRequest(question="quantum computing", kinds=[Kind.COURSE], as_of=date(2027, 6, 1))
    )
    assert later.as_of == date(2027, 6, 1) and "FUT100" in keys(later)


def test_exact_lookup_respects_validity_window(db, today):
    res = make(db, today).retrieve(RetrievalRequest(question="about FUT100", kinds=[Kind.COURSE]))
    assert "FUT100" not in keys(res)


def test_filters_apply_to_semantic_and_exact(db, today):
    res = make(db, today).retrieve(
        RetrievalRequest(question="CS201 and CH101", kinds=[Kind.COURSE], filters={"department": "CHEM"})
    )
    assert set(keys(res)) == {"CH101"}


def test_invalid_filter_for_requested_kind_is_rejected(db, today):
    with pytest.raises(InvalidRequest):
        make(db, today).retrieve(
            RetrievalRequest(question="x", kinds=[Kind.COURSE], filters={"colour": "red"})
        )


def test_min_score_drops_weak_matches(db, today):
    res = make(db, today, min_score=0.95).retrieve(RetrievalRequest(question="zzz qqq unrelated"))
    assert res.empty and res.context == ""


def test_context_budget_drops_tail_but_keeps_first(db, today):
    res = make(db, today, max_context_chars=100).retrieve(
        RetrievalRequest(question="programming", kinds=[Kind.COURSE], top_k=4)
    )
    assert len(res.passages) >= 1 and res.dropped >= 1
    assert [p.ref for p in res.passages] == list(range(1, len(res.passages) + 1))


def test_empty_store_returns_empty_result(today):
    empty = Database(MemoryBackend(), FakeEmbedder())
    res = Retriever(empty.as_reader(), today=today).retrieve(RetrievalRequest(question="anything"))
    assert res.empty and res.passages == [] and res.context == ""


def test_embedding_model_mismatch_propagates(db, backend, today):
    other = Database(backend, FakeEmbedder("another-model")).as_reader()
    with pytest.raises(EmbeddingModelMismatch):
        Retriever(other, today=today).retrieve(RetrievalRequest(question="programming"))


def test_result_is_json_serialisable(db, today):
    res = make(db, today).retrieve(RetrievalRequest(question="who teaches CS201?"))
    assert RetrievalResult_roundtrip(res)


def RetrievalResult_roundtrip(res):
    from minal.retrieval import RetrievalResult
    return RetrievalResult.model_validate_json(res.model_dump_json()) == res

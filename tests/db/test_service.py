"""Contract tests: run against the memory backend and, if installed, Chroma."""
from datetime import date

import pytest
from db_fakes import FakeEmbedder

from minal.db import (
    Alignment, Course, Database, DatabaseReader, EmbeddingModelMismatch, Empty, Faculty,
    InvalidRequest, KeyRequest, Kind, ListRequest, NotFound, PutRequest, ReferenceMissing,
    ReindexRequest, SearchRequest,
)


def course(code="CS101", **kw):
    base = dict(code=code, title="Intro to Programming", department="CS", credits=4,
                description="Python basics and problem solving")
    return Course(**{**base, **kw})


def put(db, record):
    return db.put(PutRequest.of(record))


def key(kind, k):
    return KeyRequest(kind=kind, key=k)


def test_create_then_get(db):
    r = put(db, course())
    assert (r.action, r.version, r.key) == ("created", 1, "CS101")
    got = db.get(key(Kind.COURSE, "CS101"))
    assert got.status == "active" and got.record["title"] == "Intro to Programming"


def test_get_missing_raises_not_found(db):
    with pytest.raises(NotFound):
        db.get(key(Kind.COURSE, "NOPE"))


def test_identical_put_is_unchanged_and_not_re_embedded(db, embedder):
    put(db, course())
    calls = embedder.doc_calls
    assert put(db, course()).action == "unchanged"
    assert embedder.doc_calls == calls


def test_update_bumps_version_and_keeps_history(db, clock):
    put(db, course(credits=3))
    clock.tick()
    r = put(db, course(credits=4))
    assert (r.action, r.version) == ("updated", 2)
    assert db.get(key(Kind.COURSE, "CS101")).record["credits"] == 4
    versions = db.history(key(Kind.COURSE, "CS101")).versions
    assert [(v.version, v.status) for v in versions] == [(2, "active"), (1, "superseded")]
    assert versions[1].record["credits"] == 3


def test_search_ranks_relevant_record_first(db):
    put(db, course("CS201", title="Machine Learning", description="neural networks and deep learning"))
    put(db, course("CH101", title="Organic Chemistry", department="CHEM",
                   description="synthesis and spectroscopy"))
    hits = db.search(SearchRequest(text="neural networks", top_k=2)).hits
    assert hits[0].stored.key == "CS201"
    assert hits[0].score >= hits[-1].score


def test_search_on_empty_store_returns_nothing(db):
    assert db.search(SearchRequest(text="anything")).hits == []


def test_search_ignores_history_unless_asked(db):
    put(db, course(description="legacy curriculum"))
    put(db, course(description="modern curriculum"))
    active = db.search(SearchRequest(text="curriculum", kinds=[Kind.COURSE])).hits
    assert [h.stored.version for h in active] == [2]
    allv = db.search(SearchRequest(text="curriculum", kinds=[Kind.COURSE], include_history=True)).hits
    assert sorted(h.stored.version for h in allv) == [1, 2]


def test_filters_and_unknown_filter(db):
    put(db, course("CS101"))
    put(db, course("CH101", department="CHEM"))
    res = db.list_records(ListRequest(kind=Kind.COURSE, filters={"department": "CHEM"}))
    assert [i.key for i in res.items] == ["CH101"] and res.total == 1
    with pytest.raises(InvalidRequest):
        db.list_records(ListRequest(kind=Kind.COURSE, filters={"colour": "red"}))


def test_as_of_selects_records_valid_on_that_day(db):
    put(db, course("OLD1", valid_from=date(2023, 1, 1), valid_to=date(2024, 12, 31)))
    put(db, course("NEW1", valid_from=date(2025, 1, 1)))
    put(db, course("ANY1"))  # no window: always valid
    def keys(day):
        return sorted(i.key for i in db.list_records(ListRequest(kind=Kind.COURSE, as_of=day)).items)
    assert keys(date(2024, 6, 1)) == ["ANY1", "OLD1"]
    assert keys(date(2025, 6, 1)) == ["ANY1", "NEW1"]


def test_retire_hides_from_active_but_keeps_history(db):
    put(db, course())
    db.retire(key(Kind.COURSE, "CS101"))
    with pytest.raises(NotFound):
        db.get(key(Kind.COURSE, "CS101"))
    assert db.list_records(ListRequest(kind=Kind.COURSE)).total == 0
    assert db.history(key(Kind.COURSE, "CS101")).versions[0].status == "retired"


def test_reintroducing_a_retired_key_gets_a_new_version(db):
    put(db, course())
    db.retire(key(Kind.COURSE, "CS101"))
    assert put(db, course()).version == 2
    assert len(db.history(key(Kind.COURSE, "CS101")).versions) == 2


def test_purge_removes_everything(db):
    put(db, course(credits=3))
    put(db, course(credits=4))
    assert db.purge(key(Kind.COURSE, "CS101")).removed == 2
    with pytest.raises(NotFound):
        db.history(key(Kind.COURSE, "CS101"))
    with pytest.raises(NotFound):
        db.purge(key(Kind.COURSE, "CS101"))


def test_alignment_requires_existing_course_and_faculty(db):
    a = Alignment(course_code="CS101", faculty_id="F1", term="2026-Fall")
    with pytest.raises(ReferenceMissing):
        put(db, a)
    put(db, course())
    with pytest.raises(ReferenceMissing):
        put(db, a)
    put(db, Faculty(id="F1", name="Dr Rao", department="CS"))
    assert put(db, a).action == "created"


def test_alignment_is_enriched_and_searchable_by_name(db):
    put(db, course())
    put(db, Faculty(id="F1", name="Dr Rao", department="CS"))
    put(db, Alignment(course_code="CS101", faculty_id="F1", term="2026-Fall"))
    stored = db.get(key(Kind.ALIGNMENT, "CS101|F1|2026-Fall")).record
    assert stored["faculty_name"] == "Dr Rao" and stored["course_title"] == "Intro to Programming"
    hits = db.search(SearchRequest(text="Dr Rao", kinds=[Kind.ALIGNMENT])).hits
    assert hits and hits[0].stored.key == "CS101|F1|2026-Fall"


def test_failed_embedding_leaves_stored_data_untouched(db, embedder):
    put(db, course(credits=3))
    embedder.fail = True
    with pytest.raises(RuntimeError):
        put(db, course(credits=4))
    embedder.fail = False
    assert db.get(key(Kind.COURSE, "CS101")).record["credits"] == 3
    assert len(db.history(key(Kind.COURSE, "CS101")).versions) == 1


def test_embedding_model_mismatch_is_refused(db, backend, clock):
    put(db, course())
    other = Database(backend, FakeEmbedder("another-model"), clock)
    with pytest.raises(EmbeddingModelMismatch):
        put(other, course("CS102"))
    with pytest.raises(EmbeddingModelMismatch):
        other.search(SearchRequest(text="programming", kinds=[Kind.COURSE]))
    assert other.stats().compatible is False


def test_reindex_switches_model(db, backend, clock):
    put(db, course())
    put(db, course(credits=3))  # creates history too
    other = Database(backend, FakeEmbedder("another-model"), clock)
    res = other.reindex(ReindexRequest())
    assert res.reindexed == 2 and res.embedding_model == "another-model"
    assert other.search(SearchRequest(text="programming", kinds=[Kind.COURSE])).hits
    assert other.stats().compatible is True


def test_reader_cannot_write(db):
    reader = db.as_reader()
    assert isinstance(reader, DatabaseReader)
    for name in ("put", "retire", "purge", "reindex"):
        assert not hasattr(reader, name)
    put(db, course())
    assert reader.get(key(Kind.COURSE, "CS101")).key == "CS101"


def test_stats_counts_active_and_history(db):
    put(db, course(credits=3))
    put(db, course(credits=4))
    stats = {k.kind: k for k in db.stats(Empty()).kinds}
    assert (stats[Kind.COURSE].active, stats[Kind.COURSE].history) == (1, 1)
    assert stats[Kind.COURSE].embedding_model == "fake-bow-512"
    assert stats[Kind.FACULTY].active == 0

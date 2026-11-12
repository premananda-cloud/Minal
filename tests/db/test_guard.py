"""retire/purge safety: records still used by alignments are protected."""
from datetime import date

import pytest

from minal.db import (
    Alignment, Course, Dispatcher, Faculty, InUse, KeyRequest, Kind, NotFound,
    PutRequest, RemoveRequest,
)


def put(db, record):
    return db.put(PutRequest.of(record))


def setup(db, **alignment_kw):
    put(db, Course(code="CS201", title="Machine Learning", department="CS", credits=3))
    put(db, Faculty(id="F1", name="Dr Rao", department="CS"))
    put(db, Alignment(course_code="CS201", faculty_id="F1", term="2026-Fall", **alignment_kw))


AL = "CS201|F1|2026-Fall"


def remove(kind, key, **flags):
    return RemoveRequest(kind=kind, key=key, **flags)


def test_retire_course_blocked_by_current_alignment(db):
    setup(db)
    with pytest.raises(InUse) as exc:
        db.retire(remove(Kind.COURSE, "CS201"))
    assert exc.value.details["alignments"] == [AL] and exc.value.details["count"] == 1
    assert db.get(KeyRequest(kind=Kind.COURSE, key="CS201")).status == "active"


def test_retire_faculty_blocked_by_current_alignment(db):
    setup(db)
    with pytest.raises(InUse):
        db.retire(remove(Kind.FACULTY, "F1"))


def test_plain_key_request_is_also_guarded(db):
    setup(db)
    with pytest.raises(InUse):
        db.retire(KeyRequest(kind=Kind.COURSE, key="CS201"))


def test_past_alignment_does_not_block_retire_but_does_block_purge(db):
    # FakeClock starts 2026-01-01; this assignment ended in 2025.
    setup(db, valid_to=date(2025, 12, 31))
    with pytest.raises(InUse):
        db.purge(remove(Kind.COURSE, "CS201"))
    assert db.retire(remove(Kind.COURSE, "CS201")).cascaded == []


def test_future_alignment_does_not_block_retire(db):
    setup(db, valid_from=date(2027, 1, 1))
    assert db.retire(remove(Kind.FACULTY, "F1")).cascaded == []


def test_cascade_retires_alignments_then_the_record(db):
    setup(db)
    res = db.retire(remove(Kind.COURSE, "CS201", cascade=True))
    assert res.cascaded == [AL]
    with pytest.raises(NotFound):
        db.get(KeyRequest(kind=Kind.ALIGNMENT, key=AL))
    assert db.history(KeyRequest(kind=Kind.ALIGNMENT, key=AL)).versions[0].status == "retired"
    with pytest.raises(NotFound):
        db.get(KeyRequest(kind=Kind.COURSE, key="CS201"))


def test_force_leaves_alignment_in_place(db):
    setup(db)
    res = db.retire(remove(Kind.COURSE, "CS201", force=True))
    assert res.cascaded == []
    assert db.get(KeyRequest(kind=Kind.ALIGNMENT, key=AL)).status == "active"


def test_purge_cascade_removes_alignment_history_too(db):
    setup(db)
    res = db.purge(remove(Kind.FACULTY, "F1", cascade=True))
    assert res.cascaded == [AL]
    with pytest.raises(NotFound):
        db.history(KeyRequest(kind=Kind.ALIGNMENT, key=AL))


def test_missing_record_is_not_found_before_any_cascade(db):
    setup(db)
    with pytest.raises(NotFound):
        db.retire(remove(Kind.COURSE, "NOPE", cascade=True))
    assert db.get(KeyRequest(kind=Kind.ALIGNMENT, key=AL)).status == "active"


def test_alignments_themselves_are_never_blocked(db):
    setup(db)
    assert db.retire(remove(Kind.ALIGNMENT, AL)).cascaded == []


def test_dispatcher_reports_in_use_and_accepts_flags(db):
    setup(db)
    d = Dispatcher(db)
    blocked = d.handle("retire", {"kind": "course", "key": "CS201"})
    assert blocked["error"]["code"] == "in_use"
    ok = d.handle("retire", {"kind": "course", "key": "CS201", "cascade": True})
    assert ok["ok"] and ok["result"]["cascaded"] == [AL]

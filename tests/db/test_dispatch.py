import json

from db_fakes import FakeEmbedder

from minal.db import Database, Dispatcher
from minal.db.backends.memory import MemoryBackend

COURSE = {"code": "cs101", "title": "Intro", "department": "CS", "credits": 4}


def test_put_get_search_round_trip_is_json_serialisable(db):
    d = Dispatcher(db)
    out = d.handle("put", {"kind": "course", "record": COURSE})
    assert out == {"ok": True, "result": {"action": "created", "kind": "course", "key": "CS101", "version": 1}}
    assert d.handle("get", {"kind": "course", "key": "CS101"})["ok"]
    res = d.handle("search", {"text": "intro", "top_k": 3})
    assert res["ok"] and res["result"]["hits"][0]["stored"]["key"] == "CS101"
    json.dumps(res)  # must not raise


def test_unknown_command(db):
    out = Dispatcher(db).handle("drop_everything")
    assert out["ok"] is False and out["error"]["code"] == "unknown_command"


def test_invalid_payload_reports_validation_errors(db):
    out = Dispatcher(db).handle("put", {"kind": "course", "record": {"code": "X"}})
    assert out["error"]["code"] == "invalid_request"
    out = Dispatcher(db).handle("search", {"text": "", "top_k": 999})
    assert out["error"]["code"] == "invalid_request"


def test_domain_errors_map_to_codes(db):
    d = Dispatcher(db)
    assert d.handle("get", {"kind": "course", "key": "NOPE"})["error"]["code"] == "not_found"
    alignment = {"course_code": "CS101", "faculty_id": "F1", "term": "T1"}
    assert d.handle("put", {"kind": "alignment", "record": alignment})["error"]["code"] == "reference_missing"


def test_reader_dispatcher_has_no_write_commands(db):
    d = Dispatcher(db.as_reader())
    assert d.commands == ["get", "history", "list", "search", "stats"]
    out = d.handle("put", {"kind": "course", "record": COURSE})
    assert out["error"]["code"] == "unknown_command"


def test_unexpected_errors_do_not_leak_details():
    class Boom(MemoryBackend):
        def get(self, *a, **k):
            raise RuntimeError("secret internals")

    out = Dispatcher(Database(Boom(), FakeEmbedder())).handle("get", {"kind": "course", "key": "A"})
    assert out["error"]["code"] == "internal_error"
    assert "secret" not in json.dumps(out)

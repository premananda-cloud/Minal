import io
import json

import pytest

from minal.admin.cli import main, parse_pairs, parse_value, CliError


def run(db, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), db=db, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def seed(db):
    run(db, "add", "faculty", "--set", "id=F1", "--set", "name=Dr Rao", "--set", "department=CS")
    run(db, "add", "course", "--set", "code=CS201", "--set", "title=Machine Learning",
        "--set", "department=CS", "--set", "credits=3")
    run(db, "add", "alignment", "--set", "course_code=CS201", "--set", "faculty_id=F1",
        "--set", "term=2026-Fall")


def test_parse_value_types():
    assert parse_value("3") == 3
    assert parse_value("true") is True
    assert parse_value("null") is None
    assert parse_value('["A","B"]') == ["A", "B"]
    assert parse_value("Dr Rao") == "Dr Rao"
    assert parse_value("2026-Fall") == "2026-Fall"


def test_parse_pairs_rejects_missing_equals():
    assert parse_pairs(["a=1", "b=x=y"]) == {"a": 1, "b": "x=y"}
    with pytest.raises(CliError):
        parse_pairs(["oops"])


def test_add_then_show(db):
    code, out, _ = run(db, "add", "course", "--set", "code=cs201", "--set", "title=Machine Learning",
                       "--set", "department=CS", "--set", "credits=3")
    assert code == 0 and "created course CS201 (version 1)" in out
    code, out, _ = run(db, "show", "course", "CS201")
    assert code == 0 and "Machine Learning" in out


def test_add_with_record_json_and_overrides(db):
    rec = json.dumps({"id": "F9", "name": "Dr X", "department": "CS"})
    code, out, _ = run(db, "add", "faculty", "--record", rec, "--set", "designation=Professor")
    assert code == 0
    assert "Professor" in run(db, "show", "faculty", "F9")[1]


def test_add_without_data_is_usage_error(db):
    code, _, err = run(db, "add", "course")
    assert code == 2 and "nothing to add" in err


def test_invalid_record_reports_field_errors(db):
    code, _, err = run(db, "add", "course", "--set", "code=X")
    assert code == 1 and "invalid_request" in err and "title" in err


def test_edit_updates_and_bumps_version(db):
    seed(db)
    code, out, _ = run(db, "edit", "course", "CS201", "--set", "credits=4")
    assert code == 0 and "updated course CS201 (version 2)" in out
    assert run(db, "show", "course", "CS201")[1].count("4") >= 1


def test_edit_cannot_change_key_fields(db):
    seed(db)
    code, _, err = run(db, "edit", "course", "CS201", "--set", "code=CS999")
    assert code == 2 and "key field" in err
    code, _, err = run(db, "edit", "alignment", "CS201|F1|2026-Fall", "--set", "term=2027")
    assert code == 2


def test_edit_missing_record(db):
    code, _, err = run(db, "edit", "course", "NOPE", "--set", "credits=1")
    assert code == 1 and "not_found" in err


def test_edit_can_clear_a_field_with_null(db):
    seed(db)
    run(db, "edit", "course", "CS201", "--set", "level=UG")
    assert "UG" in run(db, "show", "course", "CS201")[1]
    run(db, "edit", "course", "CS201", "--set", "level=null")
    assert "UG" not in run(db, "show", "course", "CS201")[1]


def test_list_with_filter(db):
    seed(db)
    code, out, _ = run(db, "list", "course", "--filter", "department=CS")
    assert code == 0 and "CS201" in out and "1 of 1" in out
    assert "(none)" in run(db, "list", "course", "--filter", "department=XX")[1]


def test_list_unknown_filter_is_an_error(db):
    code, _, err = run(db, "list", "course", "--filter", "colour=red")
    assert code == 1 and "invalid_request" in err


def test_search_and_history_and_stats(db):
    seed(db)
    run(db, "edit", "course", "CS201", "--set", "credits=4")
    assert "CS201" in run(db, "search", "machine learning", "--kind", "course")[1]
    hist = run(db, "history", "course", "CS201")[1]
    assert "superseded" in hist and "active" in hist
    stats = run(db, "stats")[1]
    assert "course" in stats and "fake-bow-512" in stats


def test_retire_is_blocked_then_cascade_works(db):
    seed(db)
    code, _, err = run(db, "retire", "course", "CS201")
    assert code == 1 and "in_use" in err and "CS201|F1|2026-Fall" in err
    code, out, _ = run(db, "retire", "course", "CS201", "--cascade")
    assert code == 0 and "CS201|F1|2026-Fall" in out


def test_retire_force_and_exclusive_flags(db):
    seed(db)
    assert run(db, "retire", "faculty", "F1", "--force")[0] == 0
    assert run(db, "retire", "course", "CS201", "--force", "--cascade")[0] == 2


def test_purge_requires_confirmation(db):
    seed(db)
    code, _, err = run(db, "purge", "alignment", "CS201|F1|2026-Fall")
    assert code == 2 and "--yes" in err
    code, out, _ = run(db, "purge", "alignment", "CS201|F1|2026-Fall", "--yes")
    assert code == 0 and "purged" in out


def test_json_output_is_machine_readable(db):
    seed(db)
    code, out, _ = run(db, "stats", "--json")
    payload = json.loads(out)
    assert code == 0 and payload["ok"] is True
    code, out, _ = run(db, "show", "course", "NOPE", "--json")
    assert code == 1  # exit code still signals failure; the envelope is on stdout
    assert json.loads(out)["error"]["code"] == "not_found"


def test_usage_errors_exit_2(db):
    assert main(["bogus"], db=db, stdout=io.StringIO(), stderr=io.StringIO()) == 2

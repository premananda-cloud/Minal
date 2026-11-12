import io
import json

from minal.admin.cli import main
from minal.admin.importer import (
    ImportFileError, export_all, load_import_file, run_import,
)
from minal.db import Dispatcher

import pytest

GOOD = {
    "version": 1,
    "faculty": [{"id": "F1", "name": "Dr Rao", "department": "CS"}],
    "courses": [
        {"code": "CS101", "title": "Intro", "department": "CS", "credits": 4},
        {"code": "CS201", "title": "Machine Learning", "department": "CS", "credits": 3,
         "prerequisites": ["CS101"]},
    ],
    "alignments": [{"course_code": "CS201", "faculty_id": "F1", "term": "2026-Fall"}],
}


def active_total(d):
    return sum(k["active"] for k in d.handle("stats")["result"]["kinds"])


def write(tmp_path, data, name="data.json"):
    p = tmp_path / name
    p.write_text(json.dumps(data) if not isinstance(data, str) else data)
    return p


def test_dry_run_reports_and_writes_nothing(db):
    d = Dispatcher(db)
    report = run_import(d, GOOD, apply=False)
    assert report.ok and not report.applied
    assert report.counts == {"create": 4, "update": 0, "unchanged": 0, "error": 0}
    assert active_total(d) == 0


def test_apply_writes_in_dependency_order(db):
    d = Dispatcher(db)
    report = run_import(d, GOOD, apply=True)
    assert report.applied and report.counts["create"] == 4
    got = d.handle("get", {"kind": "alignment", "key": "CS201|F1|2026-Fall"})
    assert got["result"]["record"]["faculty_name"] == "Dr Rao"


def test_reimport_is_unchanged_then_edit_is_update(db):
    d = Dispatcher(db)
    run_import(d, GOOD, apply=True)
    assert run_import(d, GOOD, apply=False).counts == {"create": 0, "update": 0, "unchanged": 4, "error": 0}
    changed = json.loads(json.dumps(GOOD))
    changed["courses"][0]["credits"] = 5
    again = run_import(d, changed, apply=True)
    assert again.counts["update"] == 1 and again.counts["unchanged"] == 3


def test_any_error_blocks_the_whole_apply(db):
    d = Dispatcher(db)
    bad = json.loads(json.dumps(GOOD))
    bad["courses"].append({"code": "X"})  # missing fields
    report = run_import(d, bad, apply=True)
    assert not report.ok and not report.applied
    assert report.errors[0].section == "courses" and report.errors[0].index == 3
    assert active_total(d) == 0  # nothing written


def test_duplicate_keys_and_missing_references_are_errors(db):
    d = Dispatcher(db)
    data = json.loads(json.dumps(GOOD))
    data["courses"].append(dict(data["courses"][0]))
    data["alignments"].append({"course_code": "NOPE1", "faculty_id": "F1", "term": "T"})
    report = run_import(d, data, apply=False)
    messages = " | ".join(i.message or "" for i in report.errors)
    assert "duplicate key" in messages and "missing course 'NOPE1'" in messages


def test_alignment_may_reference_records_already_in_the_database(db):
    d = Dispatcher(db)
    run_import(d, {k: v for k, v in GOOD.items() if k != "alignments"}, apply=True)
    only_alignment = {"alignments": GOOD["alignments"]}
    assert run_import(d, only_alignment, apply=False).counts["create"] == 1


@pytest.mark.parametrize("content, text", [
    ("not json", "not valid JSON"),
    ("[]", "JSON object"),
    ('{"colour": 1}', "unknown top-level keys"),
    ('{"courses": {"a": 1}}', "must be a list of objects"),
    ('{"version": 99}', "unsupported file version"),
])
def test_bad_files_are_rejected(tmp_path, content, text):
    with pytest.raises(ImportFileError, match=text):
        load_import_file(write(tmp_path, content))


def test_missing_file(tmp_path):
    with pytest.raises(ImportFileError, match="cannot read"):
        load_import_file(tmp_path / "nope.json")


def test_export_then_import_into_fresh_database_round_trips(db, fresh_db, tmp_path):
    run_import(Dispatcher(db), GOOD, apply=True)
    path = tmp_path / "backup.json"
    out = io.StringIO()
    assert main(["export", str(path)], db=db, stdout=out, stderr=io.StringIO()) == 0
    assert "1 faculty, 2 courses, 1 alignments" in out.getvalue()
    assert not (tmp_path / "backup.json.tmp").exists()

    d2 = Dispatcher(fresh_db)
    assert run_import(d2, load_import_file(path), apply=True).counts["create"] == 4
    assert run_import(d2, load_import_file(path), apply=False).counts["unchanged"] == 4
    assert export_all(d2)["courses"] == export_all(Dispatcher(db))["courses"]


def test_export_excludes_retired_records(db):
    d = Dispatcher(db)
    run_import(d, GOOD, apply=True)
    d.handle("retire", {"kind": "course", "key": "CS101"})
    assert [c["code"] for c in export_all(d)["courses"]] == ["CS201"]


def test_cli_import_dry_run_then_apply(db, tmp_path):
    path = write(tmp_path, GOOD)
    out, err = io.StringIO(), io.StringIO()
    assert main(["import", str(path)], db=db, stdout=out, stderr=err) == 0
    assert "Dry run: 4 to create" in out.getvalue()
    out = io.StringIO()
    assert main(["import", str(path), "--apply"], db=db, stdout=out, stderr=err) == 0
    assert "Applied: 4 to create" in out.getvalue()


def test_cli_import_with_errors_exits_1_and_names_the_item(db, tmp_path):
    bad = {"courses": [{"code": "X"}]}
    out = io.StringIO()
    code = main(["import", str(write(tmp_path, bad)), "--apply"], db=db, stdout=out, stderr=io.StringIO())
    assert code == 1 and "courses #1" in out.getvalue() and "Not applied" in out.getvalue()


def test_cli_import_bad_file_exits_2(db, tmp_path):
    err = io.StringIO()
    code = main(["import", str(write(tmp_path, "nope"))], db=db, stdout=io.StringIO(), stderr=err)
    assert code == 2 and "not valid JSON" in err.getvalue()

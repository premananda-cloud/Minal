from datetime import date

import pytest
from pydantic import ValidationError

from minal.db import Alignment, Course, Faculty


def make_course(**kw):
    base = dict(code="cs101", title="Intro to Programming", department="CS", credits=4)
    return Course(**{**base, **kw})


def test_course_code_and_prereqs_are_normalised():
    c = make_course(prerequisites=["ma100"])
    assert c.code == "CS101" and c.key == "CS101"
    assert c.prerequisites == ["MA100"]


@pytest.mark.parametrize("bad", ["CS#101", "CS|101", "  "])
def test_reserved_characters_rejected_in_keys(bad):
    with pytest.raises(ValidationError):
        make_course(code=bad)


def test_negative_credits_rejected():
    with pytest.raises(ValidationError):
        make_course(credits=-1)


def test_validity_window_must_be_ordered():
    with pytest.raises(ValidationError):
        make_course(valid_from=date(2025, 1, 1), valid_to=date(2024, 1, 1))


def test_unknown_fields_rejected():
    with pytest.raises(ValidationError):
        make_course(colour="red")


def test_text_contains_searchable_facts():
    text = make_course(description="Python basics", prerequisites=["ma100"]).to_text()
    for expected in ("CS101", "Intro to Programming", "Python basics", "MA100"):
        assert expected in text


def test_alignment_key_and_text():
    a = Alignment(course_code="cs101", faculty_id="F1", term="2026-Fall",
                  course_title="Intro", faculty_name="Dr Rao")
    assert a.key == "CS101|F1|2026-Fall"
    assert "Dr Rao" in a.to_text() and "Intro" in a.to_text()


def test_filter_fields_skip_none():
    f = Faculty(id="F1", name="Dr Rao", department="CS")
    assert f.filter_fields() == {"department": "CS"}

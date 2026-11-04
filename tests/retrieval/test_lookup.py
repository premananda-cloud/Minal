from datetime import date

from minal.retrieval.lookup import (
    code_variants, extract_course_codes, is_valid_on, matches_filters,
)


def test_extracts_codes_in_various_spellings():
    q = "Compare cs101, CS 201 and ma-301a please"
    assert extract_course_codes(q) == [("CS", "101"), ("CS", "201"), ("MA", "301A")]


def test_duplicates_collapsed_and_plain_words_ignored():
    assert extract_course_codes("who teaches CS101? is CS101 hard?") == [("CS", "101")]
    assert extract_course_codes("what is machine learning") == []


def test_variants_cover_common_spellings():
    assert code_variants(("CS", "101")) == ["CS101", "CS 101", "CS-101"]


def test_validity_window():
    rec = {"valid_from": "2025-01-01", "valid_to": "2025-12-31"}
    assert is_valid_on(rec, date(2025, 6, 1))
    assert not is_valid_on(rec, date(2024, 12, 31))
    assert not is_valid_on(rec, date(2026, 1, 1))
    assert is_valid_on({}, date(2030, 1, 1))
    assert is_valid_on({"valid_from": "2025-01-01"}, date(2090, 1, 1))


def test_matches_filters():
    assert matches_filters({"department": "CS"}, {"department": "CS"})
    assert not matches_filters({"department": "CS"}, {"department": "CHEM"})
    assert matches_filters({"department": "CS"}, {})

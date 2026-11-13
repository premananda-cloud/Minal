import pytest

from minal.services.citations import process_citations


def test_valid_markers_are_kept_and_ordered_by_first_use():
    r = process_citations("CS201 has 3 credits [2]. Taught by Dr Rao [1]. Again [2].", {1, 2, 3})
    assert r.cited == [2, 1] and r.removed == 0
    assert r.text == "CS201 has 3 credits [2]. Taught by Dr Rao [1]. Again [2]."


@pytest.mark.parametrize("text", ["fact [1][2].", "fact [1, 2].", "fact [1,2]."])
def test_adjacent_and_grouped_markers_are_recognised(text):
    assert process_citations(text, {1, 2}).cited == [1, 2]


def test_invalid_marker_is_removed_and_counted_with_clean_spacing():
    r = process_citations("The course has 4 credits [9].", {1, 2})
    assert r.text == "The course has 4 credits." and r.cited == [] and r.removed == 1


def test_mixed_group_keeps_only_valid_numbers():
    r = process_citations("Fact [1, 9].", {1, 2})
    assert r.text == "Fact [1]." and r.cited == [1] and r.removed == 1


def test_no_markers_means_nothing_cited():
    r = process_citations("I made this up.", {1})
    assert r.cited == [] and r.removed == 0 and r.text == "I made this up."


def test_newlines_are_preserved():
    r = process_citations("- A [1]\n- B [7]\n- C [2]", {1, 2})
    assert r.text == "- A [1]\n- B\n- C [2]"


def test_non_numeric_brackets_are_left_alone():
    assert process_citations("See [note] and [1].", {1}).text == "See [note] and [1]."

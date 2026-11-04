from minal.db import Kind
from minal.retrieval.formatter import build_context, render_passage
from minal.retrieval.models import Passage


def passage(ref, text="x" * 40, **record):
    return Passage(ref=ref, kind=Kind.COURSE, key=f"K{ref}", version=1, text=text,
                   score=0.5, match="semantic", record=record)


def test_render_includes_ref_and_validity():
    p = passage(1, "Course A.", valid_from="2025-01-01")
    assert render_passage(p) == "[1] Course A. (valid 2025-01-01 to open-ended)"
    assert render_passage(passage(2, "Course B.")) == "[2] Course B."


def test_all_fit_when_budget_is_large():
    ctx, included, dropped = build_context([passage(1), passage(2)], 1000)
    assert len(included) == 2 and dropped == 0
    assert ctx.count("\n\n") == 1


def test_budget_cuts_from_the_tail():
    ps = [passage(i) for i in range(1, 6)]
    ctx, included, dropped = build_context(ps, 100)
    assert [p.ref for p in included] == [1, 2]
    assert dropped == 3 and len(ctx) <= 100


def test_first_passage_always_kept_even_over_budget():
    ctx, included, dropped = build_context([passage(1, "y" * 500), passage(2)], 50)
    assert [p.ref for p in included] == [1] and dropped == 1
    assert ctx.startswith("[1]")


def test_empty_input():
    assert build_context([], 100) == ("", [], 0)

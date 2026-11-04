"""Pure context building: turn passages into prompt-ready text within a budget."""
from __future__ import annotations

from .models import Passage


def render_passage(p: Passage) -> str:
    window = ""
    start, end = p.record.get("valid_from"), p.record.get("valid_to")
    if start or end:
        window = f" (valid {start or 'always'} to {end or 'open-ended'})"
    return f"[{p.ref}] {p.text}{window}"


def build_context(passages: list[Passage], max_chars: int) -> tuple[str, list[Passage], int]:
    """Join passages in order until the budget is hit.

    The first passage is always kept (even if over budget) so an answer is never
    starved of its best evidence. Returns (context, included, dropped_count).
    """
    included: list[Passage] = []
    parts: list[str] = []
    used = 0
    for p in passages:
        text = render_passage(p)
        cost = len(text) + (2 if parts else 0)
        if parts and used + cost > max_chars:
            break
        parts.append(text)
        included.append(p)
        used += cost
    return "\n\n".join(parts), included, len(passages) - len(included)

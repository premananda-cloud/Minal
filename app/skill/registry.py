"""
Skill registry — the upgradable point.

Each "skill" is a zero-argument function that returns a string fact
to inject into the prompt context (or "" if it has nothing to add).
`build_context()` in context_builder.py runs every skill in SKILLS
on every user query, in order, and joins the results.

Today: just datetime, because that's the one thing the model can
never know on its own and visitors will ask relative-time questions
("is there an exam this Friday?").

Later, when you're ready (not now — real time-sink risk):
    - add `web_search.py` with a `get_web_context(query)` skill that
      only fires for queries db/ can't answer (e.g. "CCC exam date"),
      hits a search API, and returns a short verified snippet.
    - register it below. Nothing else in the app needs to change —
      main.py and context_builder.py stay untouched.
"""

from typing import Callable, List
from app.skill.datetime_util import get_datetime_context

# Add new zero-arg skills here as you build them.
SKILLS: List[Callable[[], str]] = [
    get_datetime_context,
]


def run_all_skills() -> str:
    facts = [skill() for skill in SKILLS]
    return "\n".join(f for f in facts if f)

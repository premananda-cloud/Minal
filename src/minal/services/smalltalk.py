"""Detect pure small talk so greetings do not trigger a records search. Whole-message
match only: "hi, who teaches CS201?" is a real question and goes through retrieval."""
from __future__ import annotations

import re

_PATTERNS = [
    r"h+i+", r"hello+", r"hey+", r"hiya", r"namaste", r"good (morning|afternoon|evening|day)",
    r"thanks?( a lot| so much| you)?", r"thank you( so much| very much)?",
    r"(ok|okay|great|cool|nice)( thanks| thank you)?", r"bye+|goodbye|see you|good night",
    r"who are you", r"what are you", r"what('s| is) your name", r"what can you do",
    r"how are you", r"help",
]
_RE = re.compile("(?:" + "|".join(_PATTERNS) + ")")


def is_small_talk(question: str) -> bool:
    norm = re.sub(r"[^a-z' ]+", " ", question.lower().replace("’", "'"))
    norm = re.sub(r"\s+", " ", norm).strip()
    return bool(norm) and _RE.fullmatch(norm) is not None

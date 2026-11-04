"""Pure helpers for exact lookups. Semantic search is poor at 'what are the credits
for CS101?', so course codes in a question are resolved exactly first."""
from __future__ import annotations

import re
from datetime import date
from typing import Any

# letters then digits, optional separator: CS101, cs 101, CS-101, MA201A
_CODE = re.compile(r"\b([A-Za-z]{2,6})[ \-]?(\d{2,4}[A-Za-z]?)\b")


def extract_course_codes(question: str) -> list[tuple[str, str]]:
    """Return unique (letters, digits) candidates in order of appearance, upper-cased."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for letters, digits in _CODE.findall(question):
        item = (letters.upper(), digits.upper())
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def code_variants(candidate: tuple[str, str]) -> list[str]:
    """Spellings a stored course code might use, most likely first."""
    letters, digits = candidate
    return [f"{letters}{digits}", f"{letters} {digits}", f"{letters}-{digits}"]


def is_valid_on(record: dict[str, Any], day: date) -> bool:
    """Is a stored record's validity window open on `day`? (Missing bound = open.)"""
    start, end = record.get("valid_from"), record.get("valid_to")
    if start and date.fromisoformat(start) > day:
        return False
    if end and date.fromisoformat(end) < day:
        return False
    return True


def matches_filters(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    return all(record.get(k) == v for k, v in filters.items())

"""Find and validate [n] citation markers in a model answer. Pure functions."""
from __future__ import annotations

import re
from dataclasses import dataclass

# [1]  [12]  [1, 2]  [1,2,3]
_MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


@dataclass(frozen=True)
class CitationResult:
    text: str                 # answer with invalid references removed
    cited: list[int]          # valid refs, in order of first use, no duplicates
    removed: int              # number of invalid references dropped


def process_citations(text: str, valid_refs: set[int]) -> CitationResult:
    cited: list[int] = []
    removed = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal removed
        nums = [int(n) for n in re.split(r"\s*,\s*", m.group(1))]
        keep = [n for n in nums if n in valid_refs]
        removed += len(nums) - len(keep)
        for n in keep:
            if n not in cited:
                cited.append(n)
        if not keep:
            return ""
        return "[" + ", ".join(str(n) for n in keep) + "]"

    out = _MARKER.sub(repl, text)
    if removed:
        out = re.sub(r"[ \t]+([.,;:!?])", r"\1", out)   # "fact [9]." -> "fact."
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r"[ \t]+\n", "\n", out)             # no trailing space left on a line
    return CitationResult(text=out.strip(), cited=cited, removed=removed)

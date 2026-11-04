"""Retrieval contract: what callers ask for and what the LLM layer receives."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from minal.db import Kind
from minal.db.contract import Scalar


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RetrievalConfig(_M):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_context_chars: int = Field(default=6000, ge=100)
    min_score: float | None = None      # drop semantic hits below this cosine score
    exact_lookup: bool = True           # resolve course codes in the question exactly
    expand_alignments: bool = True      # add who-teaches-it records for exact courses
    max_alignments: int = Field(default=10, ge=1, le=100)


class RetrievalRequest(_M):
    question: str = Field(min_length=1)
    kinds: list[Kind] | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Scalar] = Field(default_factory=dict)
    as_of: date | None = None           # defaults to today


class Passage(_M):
    ref: int                            # citation number used in `context`
    kind: Kind
    key: str
    version: int
    text: str
    score: float | None                 # None for records added by expansion
    match: Literal["exact", "related", "semantic"]
    record: dict[str, Any]


class RetrievalResult(_M):
    question: str
    as_of: date
    passages: list[Passage]
    context: str                        # ready to drop into a prompt
    dropped: int                        # passages cut by the context budget
    empty: bool

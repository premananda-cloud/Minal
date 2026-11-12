"""Requests and results: the contract shared by Python calls, the CLI and HTTP."""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .records import Kind, Record

Scalar = str | int | float | bool
Status = Literal["active", "superseded", "retired", "all"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- requests ---------------------------------------------------------------
class Empty(_M):
    pass


class PutRequest(_M):
    kind: Kind
    record: dict[str, Any]

    @classmethod
    def of(cls, record: Record) -> "PutRequest":
        return cls(kind=record.kind, record=record.model_dump(mode="json"))


class KeyRequest(_M):
    kind: Kind
    key: str = Field(min_length=1)


class RemoveRequest(KeyRequest):
    """retire / purge. By default blocked while alignments still use the record.
    cascade: remove those alignments too. force: leave them (they become dangling)."""

    cascade: bool = False
    force: bool = False


class ListRequest(_M):
    kind: Kind
    filters: dict[str, Scalar] = Field(default_factory=dict)
    status: Status = "active"
    as_of: date | None = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class SearchRequest(_M):
    text: str = Field(min_length=1)
    kinds: list[Kind] | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, Scalar] = Field(default_factory=dict)
    as_of: date | None = None
    include_history: bool = False


class ReindexRequest(_M):
    kinds: list[Kind] | None = None


# ---- results ----------------------------------------------------------------
class StoredRecord(_M):
    kind: Kind
    key: str
    version: int
    status: str
    updated_at: str
    record: dict[str, Any]


class PutResult(_M):
    action: Literal["created", "updated", "unchanged"]
    kind: Kind
    key: str
    version: int


class RetireResult(_M):
    kind: Kind
    key: str
    version: int
    cascaded: list[str] = Field(default_factory=list)


class PurgeResult(_M):
    kind: Kind
    key: str
    removed: int
    cascaded: list[str] = Field(default_factory=list)


class HistoryResult(_M):
    kind: Kind
    key: str
    versions: list[StoredRecord]


class ListResult(_M):
    items: list[StoredRecord]
    total: int
    limit: int
    offset: int


class Hit(_M):
    kind: Kind
    score: float
    text: str
    stored: StoredRecord


class SearchResult(_M):
    hits: list[Hit]


class KindStats(_M):
    kind: Kind
    active: int
    history: int
    embedding_model: str | None


class StatsResult(_M):
    embedder: str
    compatible: bool
    kinds: list[KindStats]


class ReindexResult(_M):
    reindexed: int
    embedding_model: str

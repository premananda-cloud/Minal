"""Interfaces the service depends on. Backends and embedders plug in here."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

Scalar = str | int | float | bool
# {"field": value} for equality, {"field": {"$lte": 5}} for operators.
# Supported operators: $eq $ne $gt $gte $lt $lte $in
Where = dict[str, Any]


@dataclass(frozen=True)
class Row:
    id: str
    document: str
    metadata: dict[str, Scalar]
    embedding: list[float] | None = None


class Embedder(Protocol):
    model_name: str

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class VectorBackend(Protocol):
    def upsert(self, collection: str, rows: Sequence[Row]) -> None: ...

    def get(
        self, collection: str, ids: Sequence[str], *, with_embeddings: bool = False
    ) -> list[Row]: ...

    def delete(self, collection: str, ids: Sequence[str]) -> int: ...

    def query(
        self, collection: str, embedding: Sequence[float], top_k: int, where: Where | None
    ) -> list[tuple[Row, float]]:
        """Returns (row, score) best first; score is cosine similarity (higher = closer)."""
        ...

    def scan(
        self,
        collection: str,
        where: Where | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Row]: ...

    def count(self, collection: str, where: Where | None = None) -> int: ...

    def get_meta(self, collection: str, key: str) -> str | None: ...

    def set_meta(self, collection: str, key: str, value: str) -> None: ...

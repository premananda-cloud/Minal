"""In-memory backend. Used by unit tests and as the reference behaviour that
the Chroma backend must match."""
from __future__ import annotations

import math
from collections.abc import Sequence

from ..ports import Row, Where
from ..where import matches


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else dot / (na * nb)


class MemoryBackend:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Row]] = {}
        self._meta: dict[tuple[str, str], str] = {}

    def _col(self, name: str) -> dict[str, Row]:
        return self._data.setdefault(name, {})

    @staticmethod
    def _out(row: Row, with_embedding: bool) -> Row:
        return Row(
            id=row.id,
            document=row.document,
            metadata=dict(row.metadata),
            embedding=list(row.embedding) if with_embedding and row.embedding else None,
        )

    def upsert(self, collection: str, rows: Sequence[Row]) -> None:
        col = self._col(collection)
        for r in rows:
            if r.embedding is None:
                raise ValueError("embedding is required")
            col[r.id] = Row(r.id, r.document, dict(r.metadata), list(r.embedding))

    def get(self, collection, ids, *, with_embeddings=False):
        col = self._col(collection)
        return [self._out(col[i], with_embeddings) for i in ids if i in col]

    def delete(self, collection, ids):
        col = self._col(collection)
        return sum(1 for i in ids if col.pop(i, None) is not None)

    def query(self, collection, embedding, top_k, where):
        scored = [
            (row, _cosine(embedding, row.embedding or []))
            for row in self._col(collection).values()
            if where is None or matches(row.metadata, where)
        ]
        scored.sort(key=lambda t: (-t[1], t[0].id))
        return [(self._out(r, False), s) for r, s in scored[:top_k]]

    def scan(self, collection, where: Where | None = None, limit=None, offset=0):
        rows = [
            r
            for r in self._col(collection).values()
            if where is None or matches(r.metadata, where)
        ]
        rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return [self._out(r, False) for r in rows]

    def count(self, collection, where: Where | None = None):
        return sum(
            1
            for r in self._col(collection).values()
            if where is None or matches(r.metadata, where)
        )

    def get_meta(self, collection, key):
        return self._meta.get((collection, key))

    def set_meta(self, collection, key, value):
        self._meta[(collection, key)] = value

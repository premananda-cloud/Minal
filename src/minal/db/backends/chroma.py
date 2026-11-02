"""ChromaDB backend (embedded via PersistentClient, or server via HttpClient).

Embedded Chroma should be opened by one process at a time.
`prefix` namespaces collections, which also lets tests share one client.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..ports import Row, Where
from ..where import to_chroma


class ChromaBackend:
    def __init__(self, client: Any, *, prefix: str = "") -> None:
        self._client = client
        self._prefix = prefix
        self._cols: dict[str, Any] = {}
        self._meta: dict[tuple[str, str], str] = {}

    def _col(self, name: str) -> Any:
        col = self._cols.get(name)
        if col is None:
            col = self._client.get_or_create_collection(
                name=self._prefix + name,
                configuration={"hnsw": {"space": "cosine"}},
            )
            self._cols[name] = col
        return col

    @staticmethod
    def _rows(res: dict[str, Any], with_embeddings: bool) -> list[Row]:
        ids = res["ids"]
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        embs = res.get("embeddings") if with_embeddings else None
        out: list[Row] = []
        for i, id_ in enumerate(ids):
            emb = [float(x) for x in embs[i]] if embs is not None else None
            out.append(Row(id=id_, document=docs[i], metadata=dict(metas[i]), embedding=emb))
        return out

    def upsert(self, collection: str, rows: Sequence[Row]) -> None:
        if not rows:
            return
        if any(r.embedding is None for r in rows):
            raise ValueError("embedding is required")
        self._col(collection).upsert(
            ids=[r.id for r in rows],
            embeddings=[list(r.embedding) for r in rows],  # type: ignore[arg-type]
            documents=[r.document for r in rows],
            metadatas=[dict(r.metadata) for r in rows],
        )

    def get(self, collection, ids, *, with_embeddings=False):
        if not ids:
            return []
        include = ["documents", "metadatas"] + (["embeddings"] if with_embeddings else [])
        res = self._col(collection).get(ids=list(ids), include=include)
        return self._rows(res, with_embeddings)

    def delete(self, collection, ids):
        if not ids:
            return 0
        col = self._col(collection)
        existing = col.get(ids=list(ids), include=[])["ids"]
        if existing:
            col.delete(ids=existing)
        return len(existing)

    def query(self, collection, embedding, top_k, where: Where | None):
        col = self._col(collection)
        if col.count() == 0:
            return []
        res = col.query(
            query_embeddings=[list(embedding)],
            n_results=top_k,
            where=to_chroma(where),
            include=["documents", "metadatas", "distances"],
        )
        rows = self._rows(
            {
                "ids": res["ids"][0],
                "documents": res["documents"][0],
                "metadatas": res["metadatas"][0],
            },
            False,
        )
        # Chroma returns cosine distance; convert to similarity.
        return [(row, 1.0 - float(d)) for row, d in zip(rows, res["distances"][0], strict=True)]

    def scan(self, collection, where: Where | None = None, limit=None, offset=0):
        kwargs: dict[str, Any] = {"include": ["documents", "metadatas"]}
        chroma_where = to_chroma(where)
        if chroma_where is not None:
            kwargs["where"] = chroma_where
        if limit is not None:
            kwargs["limit"] = limit
        if offset:
            kwargs["offset"] = offset
        return self._rows(self._col(collection).get(**kwargs), False)

    def count(self, collection, where: Where | None = None):
        col = self._col(collection)
        if where is None:
            return col.count()
        return len(col.get(where=to_chroma(where), include=[])["ids"])

    def get_meta(self, collection, key):
        if (collection, key) in self._meta:
            return self._meta[(collection, key)]
        value = (self._col(collection).metadata or {}).get(key)
        return None if value is None else str(value)

    def set_meta(self, collection, key, value):
        col = self._col(collection)
        meta = dict(col.metadata or {})
        meta[key] = value
        col.modify(metadata=meta)
        self._meta[(collection, key)] = value

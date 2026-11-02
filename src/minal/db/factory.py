"""Convenience constructors that wire real components together."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .ports import Embedder
from .service import Database


def open_database(
    path: str | Path | None = None,
    *,
    embedder: Embedder | None = None,
    client: Any = None,
    prefix: str = "",
) -> Database:
    """Open (or create) the embedded Chroma store at `path`.

    Pass `client` instead to use a Chroma server (chromadb.HttpClient).
    Embedded Chroma should be opened by one process at a time; give retrieval
    `db.as_reader()` rather than opening the path a second time.
    """
    from .backends.chroma import ChromaBackend

    if client is None:
        if path is None:
            raise ValueError("provide a path or a client")
        import chromadb

        client = chromadb.PersistentClient(path=str(path))
    if embedder is None:
        from .embedders import SentenceTransformerEmbedder

        embedder = SentenceTransformerEmbedder()
    return Database(ChromaBackend(client, prefix=prefix), embedder)

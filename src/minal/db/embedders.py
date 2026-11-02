"""Real embedder. Imported lazily so tests never need to download a model."""
from __future__ import annotations

from collections.abc import Sequence

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class SentenceTransformerEmbedder:
    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        *,
        query_prefix: str = BGE_QUERY_PREFIX,
        device: str | None = None,
    ) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._query_prefix = query_prefix
        self._model = SentenceTransformer(model_name, device=device)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vecs = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return vecs.tolist()

    def embed_query(self, text: str) -> list[float]:
        vec = self._model.encode(self._query_prefix + text, normalize_embeddings=True)
        return vec.tolist()

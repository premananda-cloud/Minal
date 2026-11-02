"""Test doubles: a deterministic embedder (no model download) and a fake clock."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import UTC, datetime, timedelta

DIM = 512


class FakeEmbedder:
    """Bag-of-words hashing: texts sharing words get similar vectors."""

    def __init__(self, model_name: str = "fake-bow-512") -> None:
        self.model_name = model_name
        self.doc_calls = 0
        self.fail = False

    @staticmethod
    def _vec(text: str) -> list[float]:
        v = [0.0] * DIM
        for tok in re.findall(r"\w+", text.lower()):
            v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, texts):
        if self.fail:
            raise RuntimeError("embedder down")
        self.doc_calls += len(texts)
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 1, 1, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def tick(self, days: int = 1) -> None:
        self.now += timedelta(days=days)

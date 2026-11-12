"""Stable error types. Each carries a machine-readable `code` so that the
CLI, Python callers and a future HTTP layer can all map errors the same way."""
from __future__ import annotations

from typing import Any


class DatabaseError(Exception):
    code = "database_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidRequest(DatabaseError):
    code = "invalid_request"


class UnknownCommand(DatabaseError):
    code = "unknown_command"


class NotFound(DatabaseError):
    code = "not_found"


class ReferenceMissing(DatabaseError):
    code = "reference_missing"


class InUse(DatabaseError):
    code = "in_use"


class EmbeddingModelMismatch(DatabaseError):
    code = "embedding_model_mismatch"


class BackendError(DatabaseError):
    code = "backend_error"

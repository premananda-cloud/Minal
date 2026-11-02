"""Minal database: schema, storage workers and the command contract."""
from .contract import (
    Empty,
    KeyRequest,
    ListRequest,
    PutRequest,
    ReindexRequest,
    SearchRequest,
)
from .dispatch import Dispatcher
from .errors import (
    BackendError,
    DatabaseError,
    EmbeddingModelMismatch,
    InvalidRequest,
    NotFound,
    ReferenceMissing,
    UnknownCommand,
)
from .records import Alignment, Course, Faculty, Kind
from .service import Database, DatabaseReader, DatabaseWriter

__all__ = [
    "Alignment", "BackendError", "Course", "Database", "DatabaseError", "DatabaseReader",
    "DatabaseWriter", "Dispatcher", "Empty", "EmbeddingModelMismatch", "Faculty",
    "InvalidRequest", "Kind", "KeyRequest", "ListRequest", "NotFound", "PutRequest",
    "ReferenceMissing", "ReindexRequest", "SearchRequest", "UnknownCommand",
]

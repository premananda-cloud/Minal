"""What retrieval needs from the database. minal.db.DatabaseReader satisfies this;
tests can pass any object with these methods. Note: no write methods here."""
from __future__ import annotations

from typing import Protocol

from minal.db.contract import (
    KeyRequest,
    ListRequest,
    ListResult,
    SearchRequest,
    SearchResult,
    StoredRecord,
)


class Reader(Protocol):
    def get(self, req: KeyRequest) -> StoredRecord: ...

    def list_records(self, req: ListRequest) -> ListResult: ...

    def search(self, req: SearchRequest) -> SearchResult: ...

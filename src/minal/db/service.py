"""The database workers.

DatabaseReader  - get / list / search / history / stats   (give this to retrieval)
DatabaseWriter  - put / retire / purge / reindex          (admin only)
Database        - both

Every method takes one typed request and returns one typed result. No printing,
no global state: backend, embedder and clock are injected.

Versioning: the current version of a record lives at id=<key>. When it is
replaced or retired, the old version is copied to id=<key>#v<N> with status
"superseded" / "retired". Search and list only see status "active" unless asked.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from typing import Any

from .contract import (
    Empty,
    HistoryResult,
    Hit,
    KeyRequest,
    KindStats,
    ListRequest,
    ListResult,
    PurgeResult,
    PutRequest,
    PutResult,
    ReindexRequest,
    ReindexResult,
    RetireResult,
    SearchRequest,
    SearchResult,
    StatsResult,
    StoredRecord,
)
from .errors import (
    BackendError,
    EmbeddingModelMismatch,
    InvalidRequest,
    NotFound,
    ReferenceMissing,
)
from .ports import Embedder, Row, VectorBackend, Where
from .records import SCHEMA_VERSION, Alignment, Kind, Record, record_class

MODEL_KEY = "embedding_model"
MIN_DATE, MAX_DATE = 0, 99991231
_EMPTY = Empty()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _date_int(d: date | None, default: int) -> int:
    return default if d is None else d.year * 10000 + d.month * 100 + d.day


def _col(kind: Kind) -> str:
    return kind.value


def _history_id(key: str, version: int) -> str:
    return f"{key}#v{version}"


class _Core:
    def __init__(
        self,
        backend: VectorBackend,
        embedder: Embedder,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._backend = backend
        self._embedder = embedder
        self._clock = clock

    # -- embedding model consistency ------------------------------------------
    def _guard(self, kind: Kind) -> None:
        stored = self._backend.get_meta(_col(kind), MODEL_KEY)
        current = self._embedder.model_name
        if stored is not None and stored != current:
            raise EmbeddingModelMismatch(
                f"{kind.value} index was built with {stored!r} but this process uses "
                f"{current!r}; run reindex to switch models",
                details={"stored": stored, "current": current},
            )

    def _claim(self, kind: Kind) -> None:
        if self._backend.get_meta(_col(kind), MODEL_KEY) is None:
            self._backend.set_meta(_col(kind), MODEL_KEY, self._embedder.model_name)

    # -- lookups ----------------------------------------------------------------
    def _current(self, kind: Kind, key: str, with_embedding: bool = False) -> Row | None:
        rows = self._backend.get(_col(kind), [key], with_embeddings=with_embedding)
        return rows[0] if rows else None

    def _versions(self, kind: Kind, key: str) -> list[Row]:
        return self._backend.scan(_col(kind), {"key": key})

    @staticmethod
    def _stored(row: Row) -> StoredRecord:
        m = row.metadata
        return StoredRecord(
            kind=Kind(str(m["kind"])),
            key=str(m["key"]),
            version=int(m["version"]),
            status=str(m["status"]),
            updated_at=str(m["updated_at"]),
            record=json.loads(str(m["payload"])),
        )

    @staticmethod
    def _where(
        cls: type[Record], filters: dict[str, Any], as_of: date | None, status: str
    ) -> Where:
        unknown = set(filters) - cls.FILTERABLE
        if unknown:
            raise InvalidRequest(
                f"cannot filter {cls.kind.value} by {sorted(unknown)}",
                details={"allowed": sorted(cls.FILTERABLE)},
            )
        where: Where = {}
        if status != "all":
            where["status"] = status
        where.update(filters)
        if as_of is not None:
            n = _date_int(as_of, MIN_DATE)
            where["valid_from_int"] = {"$lte": n}
            where["valid_to_int"] = {"$gte": n}
        return where


class DatabaseReader(_Core):
    """Read-only operations. This is the only handle retrieval should receive."""

    def get(self, req: KeyRequest) -> StoredRecord:
        row = self._current(req.kind, req.key)
        if row is None:
            raise NotFound(f"{req.kind.value} {req.key!r} not found")
        return self._stored(row)

    def history(self, req: KeyRequest) -> HistoryResult:
        rows = self._versions(req.kind, req.key)
        if not rows:
            raise NotFound(f"{req.kind.value} {req.key!r} not found")
        versions = sorted((self._stored(r) for r in rows), key=lambda s: -s.version)
        return HistoryResult(kind=req.kind, key=req.key, versions=versions)

    def list_records(self, req: ListRequest) -> ListResult:
        cls = record_class(req.kind)
        where = self._where(cls, req.filters, req.as_of, req.status)
        col = _col(req.kind)
        rows = self._backend.scan(col, where, req.limit, req.offset)
        items = sorted((self._stored(r) for r in rows), key=lambda s: (s.key, -s.version))
        return ListResult(
            items=items,
            total=self._backend.count(col, where),
            limit=req.limit,
            offset=req.offset,
        )

    def search(self, req: SearchRequest) -> SearchResult:
        explicit = req.kinds is not None
        kinds = req.kinds or list(Kind)
        if not explicit:
            # Without explicit kinds, skip kinds that cannot satisfy the filters.
            kinds = [k for k in kinds if set(req.filters) <= record_class(k).FILTERABLE]
            if not kinds:
                raise InvalidRequest("no record kind supports all of these filters")
        status = "all" if req.include_history else "active"
        wheres = {
            k: self._where(record_class(k), req.filters, req.as_of, status) for k in kinds
        }
        for k in kinds:
            self._guard(k)
        vec = self._embedder.embed_query(req.text)
        hits: list[Hit] = []
        for k in kinds:
            for row, score in self._backend.query(_col(k), vec, req.top_k, wheres[k]):
                hits.append(Hit(kind=k, score=score, text=row.document, stored=self._stored(row)))
        hits.sort(key=lambda h: -h.score)
        return SearchResult(hits=hits[: req.top_k])

    def stats(self, req: Empty = _EMPTY) -> StatsResult:
        kinds: list[KindStats] = []
        compatible = True
        for k in Kind:
            model = self._backend.get_meta(_col(k), MODEL_KEY)
            if model is not None and model != self._embedder.model_name:
                compatible = False
            active = self._backend.count(_col(k), {"status": "active"})
            total = self._backend.count(_col(k), None)
            kinds.append(
                KindStats(kind=k, active=active, history=total - active, embedding_model=model)
            )
        return StatsResult(embedder=self._embedder.model_name, compatible=compatible, kinds=kinds)


class DatabaseWriter(_Core):
    """Mutating operations. Admin only."""

    batch_size = 64

    def _embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            out.extend(self._embedder.embed_documents(texts[i : i + self.batch_size]))
        if len(out) != len(texts):
            raise BackendError("embedder returned the wrong number of vectors")
        return out

    def _enrich(self, rec: Record) -> Record:
        """Alignments must point at existing records; copy their names in so the
        alignment text is searchable by title and person."""
        if not isinstance(rec, Alignment):
            return rec
        course = self._current(Kind.COURSE, rec.course_code)
        if course is None:
            raise ReferenceMissing(
                f"course {rec.course_code!r} does not exist",
                details={"kind": "course", "key": rec.course_code},
            )
        faculty = self._current(Kind.FACULTY, rec.faculty_id)
        if faculty is None:
            raise ReferenceMissing(
                f"faculty {rec.faculty_id!r} does not exist",
                details={"kind": "faculty", "key": rec.faculty_id},
            )
        return rec.model_copy(
            update={
                "course_title": json.loads(str(course.metadata["payload"]))["title"],
                "faculty_name": json.loads(str(faculty.metadata["payload"]))["name"],
            }
        )

    @staticmethod
    def _metadata(rec: Record, version: int, status: str, now: str) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "key": rec.key,
            "kind": rec.kind.value,
            "status": status,
            "version": version,
            "schema_version": SCHEMA_VERSION,
            "updated_at": now,
            "valid_from_int": _date_int(rec.valid_from, MIN_DATE),
            "valid_to_int": _date_int(rec.valid_to, MAX_DATE),
            "payload": rec.model_dump_json(),
        }
        meta.update(rec.filter_fields())
        return meta

    def _next_version(self, kind: Kind, key: str) -> int:
        rows = self._versions(kind, key)
        return max((int(r.metadata["version"]) for r in rows), default=0) + 1

    def put(self, req: PutRequest) -> PutResult:
        kind = req.kind
        rec = self._enrich(record_class(kind).model_validate(req.record))
        key = rec.key
        col = _col(kind)
        self._guard(kind)

        current = self._current(kind, key, with_embedding=True)
        if current is not None:
            if json.loads(str(current.metadata["payload"])) == rec.model_dump(mode="json"):
                return PutResult(
                    action="unchanged", kind=kind, key=key,
                    version=int(current.metadata["version"]),
                )

        now = self._clock().isoformat()
        text = rec.to_text()
        vector = self._embed([text])[0]  # embed first: a failure must not touch stored data

        if current is not None:
            old_version = int(current.metadata["version"])
            old_vec = current.embedding or self._embed([current.document])[0]
            self._backend.upsert(
                col,
                [Row(
                    id=_history_id(key, old_version),
                    document=current.document,
                    metadata={**current.metadata, "status": "superseded", "archived_at": now},
                    embedding=old_vec,
                )],
            )
            version, action = old_version + 1, "updated"
        else:
            version, action = self._next_version(kind, key), "created"

        self._claim(kind)
        self._backend.upsert(
            col,
            [Row(id=key, document=text,
                 metadata=self._metadata(rec, version, "active", now), embedding=vector)],
        )
        return PutResult(action=action, kind=kind, key=key, version=version)

    def retire(self, req: KeyRequest) -> RetireResult:
        """Take a record out of active use but keep it as history."""
        row = self._current(req.kind, req.key, with_embedding=True)
        if row is None:
            raise NotFound(f"{req.kind.value} {req.key!r} not found")
        version = int(row.metadata["version"])
        vec = row.embedding or self._embed([row.document])[0]
        now = self._clock().isoformat()
        self._backend.upsert(
            _col(req.kind),
            [Row(
                id=_history_id(req.key, version),
                document=row.document,
                metadata={**row.metadata, "status": "retired", "archived_at": now},
                embedding=vec,
            )],
        )
        self._backend.delete(_col(req.kind), [req.key])
        return RetireResult(kind=req.kind, key=req.key, version=version)

    def purge(self, req: KeyRequest) -> PurgeResult:
        """Hard delete: the record and every historical version."""
        rows = self._versions(req.kind, req.key)
        if not rows:
            raise NotFound(f"{req.kind.value} {req.key!r} not found")
        removed = self._backend.delete(_col(req.kind), [r.id for r in rows])
        return PurgeResult(kind=req.kind, key=req.key, removed=removed)

    def reindex(self, req: ReindexRequest = ReindexRequest()) -> ReindexResult:
        """Re-render and re-embed every stored version with the current embedder.
        Use after changing the embedding model or a record's to_text()."""
        total = 0
        for kind in req.kinds or list(Kind):
            cls = record_class(kind)
            rows: list[Row] = []
            offset = 0
            while True:
                page = self._backend.scan(_col(kind), None, 500, offset)
                rows.extend(page)
                if len(page) < 500:
                    break
                offset += 500
            if rows:
                texts = [cls.model_validate_json(str(r.metadata["payload"])).to_text() for r in rows]
                vectors = self._embed(texts)
                self._backend.upsert(
                    _col(kind),
                    [Row(id=r.id, document=t, metadata=r.metadata, embedding=v)
                     for r, t, v in zip(rows, texts, vectors, strict=True)],
                )
                total += len(rows)
            self._backend.set_meta(_col(kind), MODEL_KEY, self._embedder.model_name)
        return ReindexResult(reindexed=total, embedding_model=self._embedder.model_name)


class Database(DatabaseReader, DatabaseWriter):
    """Full access. Hand `as_reader()` to anything that must not write."""

    def as_reader(self) -> DatabaseReader:
        return DatabaseReader(self._backend, self._embedder, self._clock)

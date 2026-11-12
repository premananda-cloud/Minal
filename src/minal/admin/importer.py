"""Bulk import / export of college data as one JSON file.

    {"version": 1, "faculty": [...], "courses": [...], "alignments": [...]}

Import is two-phase: validate everything (dry run), then write only if the whole
file is clean. Records load in dependency order: faculty, courses, alignments.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from minal.db import Dispatcher, Kind
from minal.db.records import record_class

FORMAT_VERSION = 1
ORDER: tuple[tuple[str, Kind], ...] = (
    ("faculty", Kind.FACULTY),
    ("courses", Kind.COURSE),
    ("alignments", Kind.ALIGNMENT),
)
_ALLOWED_TOP_LEVEL = {"version"} | {name for name, _ in ORDER}
# Filled in by the writer, so ignored when comparing a file entry to stored data.
_DERIVED = {Kind.ALIGNMENT: ("course_title", "faculty_name")}


class ImportFileError(Exception):
    """The file itself is unusable (not JSON, wrong shape)."""


class ExportError(Exception):
    pass


@dataclass
class ItemResult:
    section: str
    index: int            # 1-based position within its section
    key: str | None
    action: str           # create | update | unchanged | error
    message: str | None = None


@dataclass
class ImportReport:
    applied: bool
    items: list[ItemResult] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out = {"create": 0, "update": 0, "unchanged": 0, "error": 0}
        for item in self.items:
            out[item.action] += 1
        return out

    @property
    def errors(self) -> list[ItemResult]:
        return [i for i in self.items if i.action == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "ok": self.ok,
            "counts": self.counts,
            "items": [vars(i) for i in self.items],
        }


def load_import_file(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ImportFileError(f"cannot read {path}: {exc.strerror or exc}") from exc
    except json.JSONDecodeError as exc:
        raise ImportFileError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ImportFileError("top level of the file must be a JSON object")
    unknown = set(data) - _ALLOWED_TOP_LEVEL
    if unknown:
        raise ImportFileError(
            f"unknown top-level keys {sorted(unknown)}; allowed: {sorted(_ALLOWED_TOP_LEVEL)}"
        )
    if data.get("version", FORMAT_VERSION) != FORMAT_VERSION:
        raise ImportFileError(f"unsupported file version {data['version']!r}")
    for section, _ in ORDER:
        entries = data.get(section, [])
        if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
            raise ImportFileError(f"'{section}' must be a list of objects")
    return data


def _describe(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors(include_url=False, include_context=False, include_input=False):
        where = ".".join(str(p) for p in err["loc"]) or "record"
        parts.append(f"{where}: {err['msg']}")
    return "; ".join(parts)


def _stored(dispatcher: Dispatcher, kind: Kind, key: str) -> dict[str, Any] | None:
    res = dispatcher.handle("get", {"kind": kind.value, "key": key})
    if res["ok"]:
        return res["result"]["record"]
    if res["error"]["code"] == "not_found":
        return None
    raise RuntimeError(res["error"]["message"])


def run_import(dispatcher: Dispatcher, data: dict[str, Any], *, apply: bool) -> ImportReport:
    report = ImportReport(applied=False)
    seen: dict[Kind, set[str]] = {k: set() for _, k in ORDER}
    to_write: list[tuple[ItemResult, Kind, dict[str, Any]]] = []

    for section, kind in ORDER:
        cls = record_class(kind)
        for index, raw in enumerate(data.get(section, []), start=1):
            item = ItemResult(section, index, None, "error")
            report.items.append(item)
            try:
                rec = cls.model_validate(raw)
            except ValidationError as exc:
                item.message = _describe(exc)
                continue
            item.key = rec.key
            if rec.key in seen[kind]:
                item.message = "duplicate key in file"
                continue
            seen[kind].add(rec.key)

            if kind is Kind.ALIGNMENT:
                missing = []
                for ref_kind, ref in ((Kind.COURSE, rec.course_code), (Kind.FACULTY, rec.faculty_id)):
                    if ref not in seen[ref_kind] and _stored(dispatcher, ref_kind, ref) is None:
                        missing.append(f"{ref_kind.value} {ref!r}")
                if missing:
                    item.message = "refers to missing " + " and ".join(missing)
                    continue

            dumped = rec.model_dump(mode="json")
            existing = _stored(dispatcher, kind, rec.key)
            if existing is None:
                item.action = "create"
            else:
                derived = _DERIVED.get(kind, ())
                a = {k: v for k, v in dumped.items() if k not in derived}
                b = {k: v for k, v in existing.items() if k not in derived}
                item.action = "unchanged" if a == b else "update"
            to_write.append((item, kind, dumped))

    if not apply or not report.ok:
        return report

    for item, kind, dumped in to_write:
        res = dispatcher.handle("put", {"kind": kind.value, "record": dumped})
        if res["ok"]:
            item.action = {"created": "create", "updated": "update"}.get(
                res["result"]["action"], "unchanged"
            )
        else:
            item.action, item.message = "error", res["error"]["message"]
    report.applied = report.ok
    return report


def export_all(dispatcher: Dispatcher) -> dict[str, Any]:
    """Current (active) records only. History is not included."""
    out: dict[str, Any] = {"version": FORMAT_VERSION}
    for section, kind in ORDER:
        records: list[dict[str, Any]] = []
        offset = 0
        while True:
            res = dispatcher.handle(
                "list", {"kind": kind.value, "status": "active", "limit": 500, "offset": offset}
            )
            if not res["ok"]:
                raise ExportError(res["error"]["message"])
            items = res["result"]["items"]
            records.extend(i["record"] for i in items)
            offset += len(items)
            if not items or offset >= res["result"]["total"]:
                break
        out[section] = records
    return out


def write_json_atomic(path: str | Path, data: dict[str, Any]) -> None:
    target = Path(path)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)

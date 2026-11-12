"""Human-readable output. Machine output (--json) bypasses this module."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .importer import ImportReport

Getter = Callable[[dict[str, Any]], Any]


def _cut(text: str, width: int = 48) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def table(rows: list[dict[str, Any]], columns: list[tuple[str, Getter]]) -> str:
    if not rows:
        return "(none)"
    headers = [h for h, _ in columns]
    cells = [[_cut("" if g(r) is None else str(g(r))) for _, g in columns] for r in rows]
    widths = [max(len(h), *(len(c[i]) for c in cells)) for i, h in enumerate(headers)]
    line = lambda vals: "  ".join(v.ljust(w) for v, w in zip(vals, widths)).rstrip()  # noqa: E731
    return "\n".join([line(headers), line(["-" * w for w in widths]), *(line(c) for c in cells)])


def _rec(name: str) -> Getter:
    return lambda s: s["record"].get(name)


def _credits(s: dict[str, Any]) -> str:
    v = s["record"].get("credits")
    return "" if v is None else f"{v:g}"


LIST_COLUMNS: dict[str, list[tuple[str, Getter]]] = {
    "course": [("KEY", lambda s: s["key"]), ("TITLE", _rec("title")),
               ("DEPT", _rec("department")), ("CREDITS", _credits), ("VER", lambda s: s["version"])],
    "faculty": [("KEY", lambda s: s["key"]), ("NAME", _rec("name")),
                ("DEPT", _rec("department")), ("DESIGNATION", _rec("designation")),
                ("VER", lambda s: s["version"])],
    "alignment": [("KEY", lambda s: s["key"]), ("FACULTY", _rec("faculty_name")),
                  ("COURSE", _rec("course_title")), ("TERM", _rec("term")),
                  ("VER", lambda s: s["version"])],
}


def _put(r: dict, kind: str | None) -> str:
    return f"{r['action']} {r['kind']} {r['key']} (version {r['version']})"


def _get(r: dict, kind: str | None) -> str:
    head = f"{r['kind']} {r['key']}  (version {r['version']}, {r['status']}, updated {r['updated_at']})"
    rec = r["record"]
    width = max((len(k) for k in rec), default=0)
    lines = [f"{k.ljust(width)}  {v}" for k, v in rec.items() if v not in (None, [], "")]
    return "\n".join([head, *lines])


def _list(r: dict, kind: str | None) -> str:
    cols = LIST_COLUMNS.get(kind or "", LIST_COLUMNS["course"])
    body = table(r["items"], cols)
    return f"{body}\n\n{len(r['items'])} of {r['total']} (offset {r['offset']})"


def _history(r: dict, kind: str | None) -> str:
    rows = r["versions"]
    return f"{r['kind']} {r['key']}\n" + table(
        rows, [("VER", lambda s: s["version"]), ("STATUS", lambda s: s["status"]),
               ("UPDATED", lambda s: s["updated_at"])]
    )


def _search(r: dict, kind: str | None) -> str:
    if not r["hits"]:
        return "(no matches)"
    return "\n".join(
        f"{i}. [{h['score']:.2f}] {h['kind']} {h['stored']['key']}: {_cut(h['text'], 110)}"
        for i, h in enumerate(r["hits"], start=1)
    )


def _stats(r: dict, kind: str | None) -> str:
    body = table(r["kinds"], [("KIND", lambda s: s["kind"]), ("ACTIVE", lambda s: s["active"]),
                              ("HISTORY", lambda s: s["history"]),
                              ("INDEX MODEL", lambda s: s["embedding_model"] or "-")])
    note = "" if r["compatible"] else "\nWARNING: index was built with a different embedding model; run reindex."
    return f"{body}\n\nembedder: {r['embedder']}{note}"


def _cascade(r: dict) -> str:
    return f"\n  also removed alignments: {', '.join(r['cascaded'])}" if r.get("cascaded") else ""


def _retire(r: dict, kind: str | None) -> str:
    return f"retired {r['kind']} {r['key']} (version {r['version']}){_cascade(r)}"


def _purge(r: dict, kind: str | None) -> str:
    return f"purged {r['kind']} {r['key']} ({r['removed']} version(s) deleted){_cascade(r)}"


def _reindex(r: dict, kind: str | None) -> str:
    return f"reindexed {r['reindexed']} record(s) with model {r['embedding_model']}"


_RENDERERS: dict[str, Callable[[dict, str | None], str]] = {
    "put": _put, "get": _get, "list": _list, "history": _history, "search": _search,
    "stats": _stats, "retire": _retire, "purge": _purge, "reindex": _reindex,
}


def render_result(command: str, result: dict[str, Any], kind: str | None = None) -> str:
    return _RENDERERS[command](result, kind)


def render_error(error: dict[str, Any]) -> str:
    text = f"error [{error['code']}]: {error['message']}"
    details = error.get("details")
    if isinstance(details, dict) and details.get("alignments"):
        shown = "\n".join(f"  - {k}" for k in details["alignments"])
        more = details["count"] - len(details["alignments"])
        text += f"\n{shown}" + (f"\n  ... and {more} more" if more > 0 else "")
    elif isinstance(details, list):  # validation errors
        text += "".join(f"\n  - {'.'.join(str(p) for p in d['loc'])}: {d['msg']}" for d in details)
    return text


def render_report(report: ImportReport) -> str:
    lines = []
    for item in report.items:
        if item.action in ("error", "create", "update"):
            note = f": {item.message}" if item.message else ""
            lines.append(f"  {item.action:<7} {item.section} #{item.index} {item.key or ''}{note}")
    c = report.counts
    summary = (f"{c['create']} to create, {c['update']} to update, "
               f"{c['unchanged']} unchanged, {c['error']} error(s)")
    if report.applied:
        verdict = f"Applied: {summary}."
    elif report.ok:
        verdict = f"Dry run: {summary}. Nothing written; re-run with --apply to write."
    else:
        verdict = f"Not applied: {summary}. Fix the errors above; nothing was written."
    return "\n".join([*lines, verdict]) if lines else verdict

"""Admin CLI. Parsing and printing only: every action goes through Dispatcher.

    minal-admin add course --set code=CS201 --set title="Machine Learning" \\
        --set department=CS --set credits=3
    minal-admin import data.json            # dry run
    minal-admin import data.json --apply

main() returns an exit code: 0 ok, 1 the operation failed, 2 bad usage or file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from minal.db import Dispatcher, Kind

from .importer import (
    ExportError,
    ImportFileError,
    export_all,
    load_import_file,
    run_import,
    write_json_atomic,
)
from .lock import StoreBusy, store_lock
from .render import render_error, render_report, render_result

KINDS = [k.value for k in Kind]
DEFAULT_DATA_DIR = "data/chroma"
# Changing these would create a different record, so `edit` refuses to touch them.
KEY_FIELDS = {
    "course": {"code"},
    "faculty": {"id"},
    "alignment": {"course_code", "faculty_id", "term"},
}


class CliError(Exception):
    """Bad usage; reported as exit code 2."""


# ---- argument parsing -------------------------------------------------------
def parse_value(text: str) -> Any:
    """'3' -> 3, 'true' -> True, '["A"]' -> list, 'null' -> None, anything else -> str."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def parse_pairs(items: Sequence[str] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise CliError(f"expected key=value, got {item!r}")
        key, value = item.split("=", 1)
        if not key:
            raise CliError(f"empty key in {item!r}")
        out[key] = parse_value(value)
    return out


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", help=f"store location (env MINAL_DATA_DIR, default {DEFAULT_DATA_DIR})")
    common.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")

    parser = argparse.ArgumentParser(prog="minal-admin", description="Manage Minal college data.")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, help_: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_, parents=[common])

    p = add("add", "create a record")
    p.add_argument("kind", choices=KINDS)
    p.add_argument("--record", help="record as a JSON object")
    p.add_argument("--file", help="read the record from a JSON file")
    p.add_argument("--set", action="append", metavar="K=V", help="set a field (repeatable)")

    p = add("edit", "change fields of an existing record")
    p.add_argument("kind", choices=KINDS)
    p.add_argument("key")
    p.add_argument("--set", action="append", metavar="K=V", required=True)

    for name, help_ in (("show", "show one record"), ("history", "show all versions of a record")):
        p = add(name, help_)
        p.add_argument("kind", choices=KINDS)
        p.add_argument("key")

    p = add("list", "list records")
    p.add_argument("kind", choices=KINDS)
    p.add_argument("--filter", action="append", metavar="K=V", dest="filters")
    p.add_argument("--status", choices=["active", "superseded", "retired", "all"], default="active")
    p.add_argument("--as-of", metavar="YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--offset", type=int, default=0)

    p = add("search", "semantic search")
    p.add_argument("text")
    p.add_argument("--kind", action="append", choices=KINDS, dest="kinds")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--filter", action="append", metavar="K=V", dest="filters")
    p.add_argument("--as-of", metavar="YYYY-MM-DD")
    p.add_argument("--include-history", action="store_true")

    add("stats", "counts and embedding-model status")

    p = add("reindex", "re-embed stored records with the current model")
    p.add_argument("--kind", action="append", choices=KINDS, dest="kinds")

    for name, help_ in (("retire", "take a record out of use, keeping history"),
                        ("purge", "permanently delete a record and its history")):
        p = add(name, help_)
        p.add_argument("kind", choices=KINDS)
        p.add_argument("key")
        group = p.add_mutually_exclusive_group()
        group.add_argument("--cascade", action="store_true", help="also remove the alignments that use it")
        group.add_argument("--force", action="store_true", help="proceed and leave those alignments dangling")
        if name == "purge":
            p.add_argument("--yes", action="store_true", help="confirm permanent deletion")

    p = add("import", "load records from a JSON file (dry run unless --apply)")
    p.add_argument("file")
    p.add_argument("--apply", action="store_true")

    p = add("export", "write current records to a JSON file")
    p.add_argument("file")
    return parser


# ---- running ----------------------------------------------------------------
def _emit(args: argparse.Namespace, command: str, envelope: dict[str, Any],
          out: TextIO, err: TextIO, kind: str | None = None) -> int:
    if args.as_json:
        print(json.dumps(envelope, indent=2, ensure_ascii=False, default=str), file=out)
    elif envelope["ok"]:
        print(render_result(command, envelope["result"], kind), file=out)
    else:
        print(render_error(envelope["error"]), file=err)
    return 0 if envelope["ok"] else 1


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _read_record(args: argparse.Namespace) -> dict[str, Any]:
    record: dict[str, Any] = {}
    if args.file:
        try:
            record = json.loads(Path(args.file).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CliError(f"cannot read record from {args.file}: {exc}") from exc
    if args.record:
        try:
            record.update(json.loads(args.record))
        except json.JSONDecodeError as exc:
            raise CliError(f"--record is not valid JSON: {exc}") from exc
    if not isinstance(record, dict):
        raise CliError("a record must be a JSON object")
    record.update(parse_pairs(args.set))
    if not record:
        raise CliError("nothing to add: give --set key=value, --record or --file")
    return record


def _run(args: argparse.Namespace, d: Dispatcher, out: TextIO, err: TextIO) -> int:
    cmd = args.command

    if cmd == "add":
        record = _read_record(args)
        return _emit(args, "put", d.handle("put", {"kind": args.kind, "record": record}), out, err)

    if cmd == "edit":
        changes = parse_pairs(args.set)
        touched = set(changes) & KEY_FIELDS[args.kind]
        if touched:
            raise CliError(
                f"cannot change key field(s) {sorted(touched)}; "
                "add a new record (and retire the old one) instead"
            )
        current = d.handle("get", {"kind": args.kind, "key": args.key})
        if not current["ok"]:
            return _emit(args, "get", current, out, err)
        record = {**current["result"]["record"], **changes}
        return _emit(args, "put", d.handle("put", {"kind": args.kind, "record": record}), out, err)

    if cmd in ("show", "history"):
        command = "get" if cmd == "show" else "history"
        return _emit(args, command, d.handle(command, {"kind": args.kind, "key": args.key}), out, err)

    if cmd == "list":
        payload = _drop_none({
            "kind": args.kind, "filters": parse_pairs(args.filters), "status": args.status,
            "as_of": args.as_of, "limit": args.limit, "offset": args.offset,
        })
        return _emit(args, "list", d.handle("list", payload), out, err, kind=args.kind)

    if cmd == "search":
        payload = _drop_none({
            "text": args.text, "kinds": args.kinds, "top_k": args.top_k,
            "filters": parse_pairs(args.filters), "as_of": args.as_of,
            "include_history": args.include_history,
        })
        return _emit(args, "search", d.handle("search", payload), out, err)

    if cmd == "stats":
        return _emit(args, "stats", d.handle("stats"), out, err)

    if cmd == "reindex":
        return _emit(args, "reindex", d.handle("reindex", _drop_none({"kinds": args.kinds})), out, err)

    if cmd in ("retire", "purge"):
        if cmd == "purge" and not args.yes:
            raise CliError("purge permanently deletes the record and all its history; pass --yes to confirm")
        payload = {"kind": args.kind, "key": args.key, "cascade": args.cascade, "force": args.force}
        return _emit(args, cmd, d.handle(cmd, payload), out, err)

    if cmd == "import":
        try:
            data = load_import_file(args.file)
        except ImportFileError as exc:
            raise CliError(str(exc)) from exc
        report = run_import(d, data, apply=args.apply)
        if args.as_json:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), file=out)
        else:
            print(render_report(report), file=out)
        return 0 if report.ok else 1

    if cmd == "export":
        try:
            data = export_all(d)
            write_json_atomic(args.file, data)
        except (ExportError, OSError) as exc:
            print(f"error: {exc}", file=err)
            return 1
        counts = ", ".join(f"{len(data[s])} {s}" for s in ("faculty", "courses", "alignments"))
        print(f"exported {counts} to {args.file} (current records only; history not included)", file=out)
        return 0

    raise CliError(f"unhandled command {cmd!r}")  # pragma: no cover


def main(argv: Sequence[str] | None = None, *, db: Any = None,
         stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    out, err = stdout or sys.stdout, stderr or sys.stderr
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exc:  # argparse exits on --help and on bad usage
        return int(exc.code or 0)
    try:
        if db is not None:  # tests inject a ready-made Database
            return _run(args, Dispatcher(db), out, err)
        data_dir = args.data_dir or os.environ.get("MINAL_DATA_DIR", DEFAULT_DATA_DIR)
        with store_lock(Path(f"{data_dir}.lock")):
            from minal.db.factory import open_database

            return _run(args, Dispatcher(open_database(data_dir)), out, err)
    except StoreBusy as exc:
        print(f"error: {exc}", file=err)
        return 1
    except CliError as exc:
        print(f"error: {exc}", file=err)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

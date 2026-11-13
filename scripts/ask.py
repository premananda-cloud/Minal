#!/usr/bin/env python
"""Manual check for P5b: ask the real answer chain real questions.

Wires the real parts together: Chroma store -> read-only Retriever -> LiteLLM gateway.
Needs vLLM (scripts/serve_vllm.sh) and the gateway (scripts/serve_litellm.sh) running,
and data already loaded with `minal-admin import` (P3.1).

    set -a; source configs/litellm.local.env; set +a
    python scripts/ask.py --data-dir data/chroma "Who teaches CS201?"      # one question
    python scripts/ask.py --data-dir data/chroma --file scripts/questions.txt --log run1.jsonl
    python scripts/ask.py --data-dir data/chroma                            # interactive

The embedder runs on the CPU by default so it does not compete with vLLM for the 12 GB GPU
(only ~1 GB was free). Pass --gpu-embedder to allow the GPU.
Do not run this while `minal-admin` has the store open (embedded Chroma has one owner).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("question", nargs="*", help="question to ask (omit for interactive mode)")
    p.add_argument("--data-dir", default=os.environ.get("MINAL_DATA_DIR", "data/chroma"),
                   help="Chroma store directory (env MINAL_DATA_DIR; default data/chroma, "
                        "the same as minal-admin)")
    p.add_argument("--file", help="text file with one question per line (# comments allowed)")
    p.add_argument("--log", help="append each answer to this JSONL file")
    p.add_argument("--show-context", action="store_true", help="print the retrieved passages")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--gpu-embedder", action="store_true", help="allow the embedder on the GPU")
    return p.parse_args(argv)


def describe_store(reader) -> tuple[str, int]:
    """Record counts per kind, e.g. 'course=12 faculty=8 alignment=15'."""
    from minal.db import Kind, ListRequest

    parts, total = [], 0
    for kind in Kind:
        name = getattr(kind, "value", str(kind))
        try:
            n = len(reader.list_records(ListRequest(kind=kind, limit=100)).items)
        except Exception:  # noqa: BLE001  (display only)
            parts.append(f"{name}=?")
            continue
        total += n
        parts.append(f"{name}={n}{'+' if n >= 100 else ''}")
    return " ".join(parts), total


def build_service(data_dir: str, top_k: int):
    from minal.db.factory import open_database
    from minal.llm import LiteLLMClient, LLMConfig
    from minal.retrieval import Retriever
    from minal.services import AnswerConfig, AnswerService

    # Opening a Chroma path creates a store if none exists, so check first.
    if not (Path(data_dir) / "chroma.sqlite3").exists():
        sys.exit(f"No Chroma store at {data_dir} (no chroma.sqlite3 there).\n"
                 "Load data first with minal-admin import, or pass the right --data-dir.")
    db = open_database(data_dir)
    reader = db.as_reader()
    summary, total = describe_store(reader)
    print(f"Store {data_dir}: {summary}")
    if total == 0:
        sys.exit("The store is empty. Load a department first (minal-admin import ...).")
    llm_cfg = LLMConfig.from_env()
    if llm_cfg.api_key is None:
        print("Warning: no API key set (source configs/litellm.local.env); the gateway will reject us.")
    cfg = AnswerConfig(top_k=top_k, office_contact=os.environ.get("MINAL_OFFICE_CONTACT"))
    return AnswerService(Retriever(reader), LiteLLMClient(llm_cfg), cfg)


def ask_once(service, question: str, *, show_context: bool = False, log: Path | None = None,
             out=sys.stdout) -> dict:
    from minal.db.errors import InvalidRequest
    from minal.llm import LLMError

    t0 = time.perf_counter()
    record: dict = {"question": question}
    print(f"\nQ: {question}", file=out)
    try:
        ans = service.answer(question)
    except (LLMError, InvalidRequest) as e:
        record.update(error=e.code, message=e.message)
        print(f"A: [ERROR {e.code}] {e.message}", file=out)
    else:
        dt = time.perf_counter() - t0
        cites = ", ".join(f"[{c.ref}] {getattr(c.kind, 'value', c.kind)} {c.key}"
                          for c in ans.citations) or "none"
        print(f"A: {ans.text}", file=out)
        print(f"   status={ans.status}  cited: {cites}  "
              f"tokens={ans.usage.prompt_tokens}+{ans.usage.completion_tokens}  {dt:.1f}s",
              file=out)
        if ans.removed_citations:
            print(f"   removed {ans.removed_citations} citation(s) to records that do not exist",
                  file=out)
        if show_context:
            for p in ans.passages:
                kind = getattr(p.kind, "value", p.kind)
                score = "-" if p.score is None else f"{p.score:.2f}"
                print(f"   passage [{p.ref}] {kind} {p.key} ({p.match}, {score}): "
                      f"{p.text[:160]!r}", file=out)
        record.update(ans.model_dump(mode="json"), seconds=round(dt, 2))
    if log:
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def questions_from_file(path: str) -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.gpu_embedder:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""      # before torch is imported
    service = build_service(args.data_dir, args.top_k)
    log = Path(args.log) if args.log else None

    questions = [" ".join(args.question)] if args.question else []
    if args.file:
        questions += questions_from_file(args.file)
    if questions:
        for q in questions:
            ask_once(service, q, show_context=args.show_context, log=log)
        return 0
    print("Interactive mode. Empty line or 'quit' to stop.")
    while True:
        try:
            q = input("\n> ").strip()
        except EOFError:
            break
        if not q or q.lower() in {"quit", "exit"}:
            break
        ask_once(service, q, show_context=args.show_context, log=log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

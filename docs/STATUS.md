# STATUS.md

**Project:** Minal
**Last updated:** 2026-11-06
**Current patch:** P3 closed out by a manual smoke test, then P4/P5
**See also:** `PLAN.md`

---

## Summary

| # | Patch | State | Evidence |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | Done | `uv sync` and `uv run pytest` work |
| P1 | Database | Done (automated) | Memory and Chroma contract tests pass, incl. persistence across reopen |
| P2 | Retrieval | Done | `uv run pytest tests/retrieval`: 24 passed |
| P3 | Admin CLI | Done (automated); manual smoke test pending | Full suite: 145 passed, 0 skipped |
| P4 | Model serving | Not started | |
| P5 | LLM layer | Not started | |
| P6 | Public API | Not started | |
| P7 | Observability and evaluation | Not started | |
| P8 | Auth and visibility | Not started | |
| P9 | Document ingestion | Not started | |
| P10 | Hardening and docs refresh | Not started | |

## What changed in P3
- **db:** retire/purge are now guarded (`InUse` error, `cascade` / `force` flags via `RemoveRequest`); the BGE embedder loads its model lazily so read-only commands are fast.
- **admin:** `minal-admin` CLI (add, edit, show, list, history, search, stats, reindex, retire, purge, import, export), JSON import with dry run, JSON export, single-owner lock file.
- **tests:** `tests/db/test_guard.py`, `tests/admin/` (CLI, importer, lock).

## Verified vs not verified

| Item | State |
| :--- | :--- |
| Full suite (db, retrieval, admin) | 145 passed, 0 skipped (Chroma-backed tests ran) |
| Chroma cosine config and collection metadata calls | Verified by the Chroma-backed tests |
| Real BGE embedder end to end | Not yet run |
| `minal-admin` against a real on-disk store | Not yet run |
| Retrieval quality on real questions | Not measured (needs real data, then P7) |

**Next verification step:** manual smoke test: import a small JSON file, list, search, blocked retire, `retire --cascade`, with the real embedder.

## Decisions made
- ChromaDB only; one collection per kind; history kept as `<key>#v<N>`.
- Retrieval gets a read-only handle; admin holds the writer and is local-only.
- Import format: one JSON file. CSV later if admins need spreadsheets.
- Retire/purge blocked while alignments use the record (`--cascade`, `--force` to override).
- Alignment = faculty teaching a course in a term. Program/outcome mapping deferred.
- Evolve the schema over time; aim for coherent and safe now, not perfect.

## Known issues and cleanup
- Remove stray folders: `zip/`, `src/minal/vectorstore/`.
- `src/minal/_legacy/` still a placeholder; decide, then delete.
- `requirements.txt` redundant; `opencv-contrib-python` unused.
- Set `asyncio_default_fixture_loop_scope = "function"` in the pytest config to silence the warning (remaining warning is from third-party plugins).
- Cascade is not atomic; import never deletes; export omits history.
- `docs/00`-`06` and `TECH_Stack.md` outdated (refreshed in P10).

## Next actions
1. Smoke-test the CLI on a real store with the real embedder.
2. Load a real department's data.
3. Start P4 (model serving) or P5 (LLM layer).

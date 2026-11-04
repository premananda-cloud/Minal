# STATUS.md

**Project:** Minal
**Last updated:** 2026-11-04
**Current patch:** P3: Admin CLI (not started)
**See also:** `PLAN.md` for the full patch list.

---

## Summary

| # | Patch | State | Evidence |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | Done | Package installs with `uv sync`; `uv run pytest` runs |
| P1 | Database | Code complete, partly verified | Used by retrieval tests (24 pass); db's own tests not yet reported |
| P2 | Retrieval | Done | `uv run pytest tests/retrieval`: 24 passed |
| P3 | Admin CLI | Not started | Folder `src/minal/admin/` is a placeholder |
| P4 | Model serving | Not started | |
| P5 | LLM layer | Not started | `src/minal/llm/` is a placeholder |
| P6 | Public API | Not started | `src/minal/api/` is a placeholder |
| P7 | Observability and evaluation | Not started | |
| P8 | Auth and visibility | Not started | `src/minal/auth/` is a placeholder |
| P9 | Document ingestion | Not started | |
| P10 | Hardening and docs refresh | Not started | |

---

## What exists

- **`src/minal/db/`:** schema (Course, Faculty, Alignment), reader/writer workers, versioned history, date-window filtering, command `Dispatcher`, in-memory and Chroma backends, sentence-transformers embedder.
- **`src/minal/retrieval/`:** exact course-code lookup, semantic search, context budget, LangChain adapter.
- **`tests/db/`, `tests/retrieval/`:** unit tests using a fake embedder and the in-memory backend. The same db contract tests also run against Chroma when `chromadb` is installed.
- **`docs/features/`:** `db.md` and `retrieval.md` filled in; `admin.md`, `ingestion.md`, `query.md` are still template copies.

## Verified vs not verified

| Item | State |
| :--- | :--- |
| Retrieval tests (in-memory backend) | Passing (24) |
| db tests on in-memory backend | Not yet run on their own |
| db tests on Chroma backend | Not yet run; two Chroma calls are the most likely to need a fix (`configuration={"hnsw": ...}` and `collection.modify(metadata=...)`) |
| Real embedder (BGE) end to end | Not run |
| Persistence across reopen | Not run |

**Next verification step:** `uv run pytest -q` for the whole suite, with `chromadb` installed, and fix anything in the Chroma-backed tests.

---

## Known issues and cleanup

- Remove stray folders: `zip/` and `src/minal/vectorstore/` (replaced by `db/`).
- `src/minal/_legacy/` is still a placeholder; decide what, if anything, moves out of it, then delete.
- `requirements.txt` is redundant with `pyproject.toml` and `uv.lock`; remove after P10 or earlier if nothing uses it.
- `opencv-contrib-python` is in dependencies but not part of the stack; remove if unused.
- Pytest prints a `pytest-asyncio` warning: set `asyncio_default_fixture_loop_scope = "function"` in the pytest config.
- `docs/00`–`06` and `TECH_Stack.md` are outdated (they predate the Chroma-only, vLLM-in-separate-env decisions); refreshed in P10.

## Decisions made so far

- ChromaDB only; no separate relational database for now.
- One collection per record kind; history kept as `<key>#v<N>`.
- Retrieval receives a read-only handle; admin holds the writer.
- Admin is local-only and separate from the public API.
- vLLM runs in its own environment, outside the main lockfile.
- Dates: `as_of` defaults to today in retrieval.

## Next actions

1. Run the full test suite and fix any db/Chroma failures.
2. Clean up the stray folders listed above.
3. Fill in `docs/features/admin.md` (import format, blocking rules), then start P3.

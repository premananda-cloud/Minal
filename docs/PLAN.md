# PLAN.md

**Project:** Minal
**Purpose:** Break the refactor into patches (small, shippable units of work), in build order.
**Companion:** `STATUS.md` says which patch we are on.

---

## Principles

1. **One-way layers.** `api` and `admin` call `services`; `services` calls `retrieval`, `llm`, `db`. Nothing lower imports anything higher.
2. **Read/write split.** AI-facing code receives only a `DatabaseReader`. Writes go through admin only.
3. **Contract first.** Every feature takes typed requests and returns typed results, so it can be called from Python, the CLI, or HTTP unchanged.
4. **Decide before coding.** Each feature gets a short doc in `docs/features/` (data flow, permissions, connections) before its patch starts.
5. **Tested in isolation.** Unit tests use fakes (in-memory backend, fake embedder). No model downloads or running services in unit tests.
6. **Admin is local-only.** The admin surface is a CLI (or offline page), never exposed on the public API.

---

## Patch overview

| # | Patch | Depends on | Size |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | none | S |
| P1 | Database (`db`) | P0 | L |
| P2 | Retrieval | P1 | M |
| P3 | Admin CLI | P1 | M |
| P4 | Model serving (vLLM + LiteLLM) | P0 | M |
| P5 | LLM layer and answer chain | P2, P4 | M |
| P6 | Public API | P5 | M |
| P7 | Observability and evaluation | P5 | M |
| P8 | Auth and visibility | P3, P6 | M |
| P9 | Document ingestion (Docling) | P1, P2 | L |
| P10 | Hardening and docs refresh | all | M |

Suggested order: P0 → P1 → P2 → **P3** → P4 → P5 → P6 → P7 → P8 → P9 → P10.
P3 comes before the AI layers because real data is needed to test everything after it. P4 can run in parallel with P3 if time allows.

---

## P0: Foundation

**Goal:** a repo anyone can clone, install and test.
**Scope:** layout, environment, packaging, test setup.
**Deliverables:** `src/minal/` package layout, `environment.yml`, `pyproject.toml` with build system, `uv.lock`, pytest config, `.gitignore`.
**Done when:** `uv sync && uv run pytest` works from a clean clone.

## P1: Database (`minal.db`)

**Goal:** a standalone worker that stores and returns college data in ChromaDB.
**Scope:**
- Schema: `Course`, `Faculty`, `Alignment` (faculty assigned to a course per term).
- Operations: put, get, list, search, history, retire, purge, reindex, stats.
- Version history on update; `valid_from`/`valid_to` with `as_of` filtering.
- Embedding model recorded per collection; mismatches refused until reindex.
- `Dispatcher` command layer (JSON in, JSON out) for CLI and HTTP.
- Backends: in-memory (tests) and Chroma.
**Done when:** contract tests pass on both backends, including persistence across reopen.

## P2: Retrieval (`minal.retrieval`)

**Goal:** given a question, return the records the LLM should read.
**Scope:** exact course-code lookup (plus who teaches it), semantic search, dedupe, `as_of` defaulting to today, context budget, optional LangChain adapter.
**Done when:** retrieval tests pass and it works with a `DatabaseReader` only.
**Later tweaks:** faculty exact lookup, `min_score` tuning with real questions.

## P3: Admin CLI (`minal.admin`)

**Goal:** a local tool for admins to manage data, built on `Dispatcher` with no logic of its own.
**Scope:**
- Commands: add, edit, retire, purge, show, list, history, search, stats, reindex.
- Bulk import from JSON/CSV with a dry-run (validate, report, then apply).
- Export / backup to JSON; restore from it.
- Clear, readable errors that show the stable error codes.
**Decide first:** import file format; whether retire/purge should be blocked when active alignments exist.
**Done when:** an admin can load a real department's data and inspect it without writing Python.

## P4: Model serving

**Goal:** a local model reachable through one stable endpoint.
**Scope:** vLLM serving a quantized 7-8B model sized for 12 GB VRAM, in its own environment (it conflicts with Docling/torch in one lockfile); LiteLLM gateway config with virtual keys; launch scripts in `scripts/` and config in `configs/`.
**Done when:** `curl` against LiteLLM's `/v1/chat/completions` returns an answer.
**Rule:** the app calls LiteLLM, never vLLM directly.

## P5: LLM layer and answer chain (`minal.llm`, `minal.services`)

**Goal:** question in, grounded answer out.
**Scope:** LiteLLM client, system prompts (`docs/03_System_Prompts.md` refreshed), chain: retrieve → prompt → LLM → answer with passage citations, "I don't know" behaviour when retrieval is empty, conversation follow-up handling (query rewriting).
**Done when:** answers cite passage numbers and refuse to invent facts when context is empty; unit tests run with a fake LLM.

## P6: Public API (`minal.api`)

**Goal:** a thin FastAPI layer over the answer service.
**Scope:** query endpoint, request/response schemas, health endpoint, error mapping from stable codes to HTTP statuses, config via `pydantic-settings`.
**Not in scope:** any admin or write endpoint.
**Done when:** a client can ask a question over HTTP and get an answer with sources.

## P7: Observability and evaluation

**Goal:** see what the system did, and know whether it is getting better.
**Scope:** Langfuse tracing (retrieved passages, prompt, tokens, latency); a small evaluation set of real institute questions with expected facts; a script that scores retrieval hit rate and answer correctness.
**Done when:** every request has a trace, and an eval run gives a comparable score after any change.

## P8: Auth and visibility

**Goal:** control who can see and change what.
**Scope:** visibility tag on records (e.g. public, faculty-only), role-aware filtering in retrieval, auth middleware on the API, admin identity and change log.
**Decide first:** the role model and who the admins are.
**Done when:** a restricted record is never returned to an unauthorised caller, with tests proving it.

## P9: Document ingestion (Docling)

**Goal:** bring in documents (handbooks, regulations, syllabi PDFs), not just structured records.
**Scope:** Docling parse to Markdown, chunking, a new record kind for document chunks, ingestion script, `replace` semantics so re-ingesting a changed file leaves no stale chunks.
**Decide first:** chunk size and strategy; whether syllabi can also populate `Course` records.
**Done when:** a PDF can be ingested and its content retrieved with a source reference.

## P10: Hardening and docs refresh

**Goal:** make it maintainable.
**Scope:** update `docs/00`–`06` and `TECH_Stack.md` to match what was actually built (Chroma-only, vLLM in a separate env), remove `_legacy/` and `requirements.txt`, backup and restore runbook, `CHANGELOG.md`, pin a release.
**Done when:** a new contributor can follow the docs from clone to running system.

---

## Open decisions

| Decision | Needed by |
| :--- | :--- |
| Meaning of "alignment" beyond faculty-to-course-per-term (e.g. program outcome mapping) | P3 |
| Import file format for admin bulk load | P3 |
| Block retire/purge of records that still have active alignments | P3 |
| Role model and who counts as admin | P8 |
| Chunking strategy and production embedding model | P9 |
| How to run admin CLI and API together, since embedded Chroma wants one owning process (shared process, or switch to Chroma server mode) | P6 |

## Known risks

- **Embedded Chroma is single-owner.** The CLI and the API cannot both open the store at once. Plan: either run admin only while the API is stopped, or move to Chroma server mode on localhost.
- **12 GB VRAM** limits model size and context length; confirm the chosen model fits with vLLM's memory settings.
- **Retrieval quality is unmeasured** until real data and an evaluation set exist (P3, P7).

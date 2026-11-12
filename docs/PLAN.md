# PLAN.md

**Project:** Minal
**Purpose:** the build order, split into small patches. Each patch is finished, tested and recorded before the next starts.
**Companion:** `STATUS.md` says which patch we are on.

---

## Principles

1. **One-way layers.** `api` and `admin` call `services`; `services` calls `retrieval`, `llm`, `db`. Nothing lower imports anything higher.
2. **Read/write split.** AI-facing code receives only a `DatabaseReader`. Writes go through admin only.
3. **Contract first.** Every feature takes typed requests and returns typed results, so it works from Python, the CLI or HTTP unchanged.
4. **Decide before coding.** Each feature gets a short doc in `docs/features/` before its patch starts.
5. **Tested in isolation.** Unit tests use fakes (in-memory backend, fake embedder, fake LLM). No downloads or running services in unit tests.
6. **Admin is local-only.** Never exposed on the public API.
7. **The app calls LiteLLM, never vLLM directly.** No Ollama.

## Patch workflow (every patch)

1. **Decide:** fill in or update the feature doc; settle the "decide first" items.
2. **Build:** the smallest change that meets the goal.
3. **Test gate:** automated tests pass (`uv run pytest`), plus the patch's manual check if it has one.
4. **Record:** update `STATUS.md` (state, evidence, decisions) and `CHANGELOG.md`.
5. **Commit** with the patch id, then start the next patch.

A patch is not done until its test gate is met and `STATUS.md` says so.

---

## Patch overview

| # | Patch | Depends on | Size | State |
| :-- | :--- | :--- | :--- | :--- |
| P0 | Foundation | none | S | Done |
| P1 | Database | P0 | L | Done |
| P2 | Retrieval | P1 | M | Done |
| P3 | Admin CLI | P1 | M | Done (automated) |
| **P3.1** | **Close-out: smoke test with real data** | P3 | S | In progress |
| **P3.5** | **Docs and repo reset (README, stack, cleanup)** | P3 | S | In progress |
| P4a | vLLM serving | P0 | M | Model decided |
| P4b | LiteLLM gateway | P4a | S | |
| P5a | LLM client and fake LLM | P4b | S | |
| P5b | Prompts and answer chain | P2, P5a | M | |
| P5c | Follow-up rewriting | P5b | S | |
| P6a | API skeleton (config, health) | P5b | S | |
| P6b | Query endpoint and error mapping | P6a | M | |
| P6c | Admin + API process model | P6b | S | |
| P7a | Langfuse tracing | P6b | S | |
| P7b | Evaluation set and scorer | P5b | M | |
| P8a | Visibility on records and retrieval filter | P3, P5b | M | |
| P8b | API auth and admin change log | P6b, P8a | M | |
| P9a | Docling parse and chunking | P1 | M | |
| P9b | Document record kind and ingest/replace | P9a, P2 | M | |
| P9c | Retrieval over documents | P9b | S | |
| P10 | Hardening and final docs | all | M | |

Order: P3.1 + P3.5 → P4a → P4b → P5a → P5b → P5c → P6a → P6b → P6c → P7a/P7b → P8a → P8b → P9a → P9b → P9c → P10.
P4a/P4b can run alongside P3.1 if time allows. A first end-to-end answer over real data arrives at P5b.

---

## P3.1: Close-out (smoke test with real data)

**Goal:** prove the data layer works outside the unit tests.
**Scope:** with the real BGE embedder and an on-disk store: import a small JSON file, list, search, try a blocked retire, run `retire --cascade`, export and re-import. Then load one real department.
**Test gate:** all steps above work without writing Python; record the result in `STATUS.md`.

## P3.5: Docs and repo reset

**Goal:** the repo describes the stack we are actually building.
**Scope:**
- `README.md` and `docs/TECH_STACK.md` rewritten (vLLM + LiteLLM + Chroma; no Ollama).
- Old `docs/00`-`06` either rewritten or moved to `docs/archive/`, so nothing contradicts `PLAN.md`.
- Delete `zip/`, `src/minal/vectorstore/`, `requirements.txt`; decide and remove `_legacy/`; drop `opencv-contrib-python`.
- Set `asyncio_default_fixture_loop_scope = "function"` in the pytest config.
- Add `CHANGELOG.md`; fill in `docs/features/query.md`.
**Test gate:** `uv sync && uv run pytest` still passes after cleanup; grep finds no "ollama" outside the archive and changelog.

## P4a: vLLM serving

**Goal:** a local model running on the machine.
**Decided:** `Qwen/Qwen2.5-7B-Instruct-AWQ`, `awq_marlin`, `max_model_len 4096`, `gpu_memory_utilization 0.80` (see `docs/features/serving.md`).
**Scope:** separate serving environment, launch script in `scripts/`, config in `configs/`.
**Test gate:** `curl` to vLLM's `/v1/chat/completions` returns text; VRAM use recorded.

## P4b: LiteLLM gateway

**Goal:** one stable endpoint in front of the model.
**Scope:** LiteLLM config routing to vLLM, a virtual key for the app, launch script.
**Test gate:** `curl` to LiteLLM with the key returns an answer; a wrong key is rejected.

## P5a: LLM client and fake LLM

**Goal:** the app can talk to LiteLLM, and tests never need it.
**Scope:** `minal.llm` client behind a port, a `FakeLLM` for tests, timeouts and error mapping to stable codes.
**Test gate:** unit tests with the fake; one opt-in integration test against the real gateway.

## P5b: Prompts and answer chain

**Goal:** question in, grounded answer with citations out.
**Scope:** system prompt (identity, safety, tone), chain retrieve -> prompt -> LLM -> answer with passage citations, "I don't know" when retrieval is empty.
**Test gate:** unit tests prove citations appear, empty context gives a refusal, and the prompt contains only retrieved text. Manual check: 10 real questions over the loaded department.

## P5c: Follow-up rewriting

**Goal:** "and who teaches it?" works.
**Scope:** rewrite a follow-up into a standalone query using the conversation so far.
**Test gate:** unit tests with the fake LLM; manual multi-turn check.

## P6a: API skeleton

**Scope:** FastAPI app, `pydantic-settings` config, `/health`.
**Test gate:** health test via the test client.

## P6b: Query endpoint and error mapping

**Scope:** query endpoint, request/response schemas with sources, stable error codes mapped to HTTP statuses. No admin or write endpoints.
**Test gate:** API tests with fake LLM and in-memory data; manual `curl` question returns an answer with sources.

## P6c: Admin and API process model

**Decide first:** shared process, run admin only while the API is stopped, or Chroma server mode.
**Scope:** implement the decision and document it.
**Test gate:** admin can update data and the API sees the change without corruption.

## P7a: Langfuse tracing
**Scope:** trace retrieved passages, prompt, tokens, latency per request.
**Test gate:** a request produces a trace; tracing failure never breaks an answer.

## P7b: Evaluation set and scorer
**Scope:** about 30-50 real institute questions with expected facts; a script scoring retrieval hit rate and answer correctness; tune `min_score`.
**Test gate:** one command prints a score; the baseline is recorded in `STATUS.md`.

## P8a: Visibility on records and retrieval filter
**Decide first:** role model and who counts as admin.
**Scope:** visibility tag on records, role-aware filtering in retrieval.
**Test gate:** tests prove a restricted record is never returned to an unauthorised caller.

## P8b: API auth and admin change log
**Scope:** auth middleware, caller role passed into retrieval, admin identity recorded on changes.
**Test gate:** unauthenticated and under-privileged requests are rejected or filtered, with tests.

## P9a: Docling parse and chunking
**Decide first:** chunk size and strategy; production embedding model.
**Scope:** Docling PDF -> Markdown -> chunks, as a standalone script.
**Test gate:** a sample handbook PDF produces sensible chunks (checked by eye and a unit test on fixtures).

## P9b: Document record kind and ingest/replace
**Scope:** new record kind for chunks with a source reference; re-ingesting a changed file leaves no stale chunks.
**Test gate:** contract tests on both backends, including re-ingest replacement.

## P9c: Retrieval over documents
**Scope:** include document chunks in retrieval with source references in citations.
**Test gate:** a question answered from a PDF cites the file and page; eval score does not drop on structured questions.

## P10: Hardening and final docs
**Scope:** refresh all docs to match what was built, backup and restore runbook, tag a release.
**Test gate:** a new contributor follows the docs from clone to a running system.

---

## Open decisions

| Decision | Needed by |
| :--- | :--- |
| Rewrite or archive old `docs/00`-`06` | P3.5 |
| Admin CLI and API sharing embedded Chroma | P6c |
| Role model and who counts as admin | P8a |
| Chunking strategy and production embedding model | P9a |
| Program-outcome mapping for alignments | later |

## Known risks

- **Embedded Chroma is single-owner:** CLI and API cannot both open the store.
- **12 GB VRAM** limits model size and context length.
- **Retrieval quality is unmeasured** until real data (P3.1) and the eval set (P7b) exist.

# STATUS.md

**Project:** Minal
**Last updated:** 2026-11-12
**Current patch:** P3.1 (smoke test) and P3.5 (docs and repo reset); P4a model decided

---

| # | Patch | State | Evidence |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | Done | `uv sync` and `uv run pytest` work |
| P1 | Database | Done | Memory and Chroma contract tests pass |
| P2 | Retrieval | Done | `tests/retrieval`: 24 passed |
| P3 | Admin CLI | Done (automated) | Full suite: 145 passed |
| P3.1 | Smoke test, real data | In progress | Not yet run |
| P3.5 | Docs and repo reset | In progress | README, TECH_STACK, PLAN written; cleanup pending |
| P4a | vLLM serving | Scripts written, not yet run | `scripts/setup_vllm_env.sh`, `serve_vllm.sh`, `check_vllm.sh`, `configs/vllm.env` |
| P4b-P10 | See `PLAN.md` | Not started | |

## Decisions
- ChromaDB only; one collection per kind; history kept as `<key>#v<N>`.
- Retrieval gets a read-only handle; admin holds the writer and is local-only.
- Import format: one JSON file. CSV later if needed.
- Retire/purge blocked while alignments use the record (`--cascade`, `--force`).
- Alignment = faculty teaching a course in a term. Program mapping deferred.
- **Stack: vLLM + LiteLLM + Chroma + FastAPI. No Ollama.**
- **Serving model: Qwen2.5-7B-Instruct-AWQ, awq_marlin, max_model_len 4096, gpu_memory_utilization 0.80.**
- Embedding model stays BGE until P9a benchmark (Qwen3-Embedding-0.6B vs BGE-M3).

## Not yet verified
- Real BGE embedder end to end; `minal-admin` on a real on-disk store (P3.1).
- Retrieval quality on real questions (needs data, then P7b).
- VRAM headroom at 4096 context (P4a).

## Next actions
1. Run `scripts/p3_5_cleanup.sh`, fix the listed references, confirm 145 tests pass.
2. Fill in `docs/features/query.md`.
3. P3.1 smoke test with the real embedder, then load one department.
4. P4a: run the three scripts on the GPU machine and paste the `check_vllm.sh` output here.

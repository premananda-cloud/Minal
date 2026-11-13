# STATUS.md

**Project:** Minal
**Last updated:** 2026-11-13
**Current patch:** P4b (gateway) in progress; P3.1 and P3.5 still open

---

| # | Patch | State | Evidence |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | Done | `uv sync` and `uv run pytest` work |
| P1 | Database | Done | Memory and Chroma contract tests pass |
| P2 | Retrieval | Done | `tests/retrieval`: 24 passed |
| P3 | Admin CLI | Done (automated) | Full suite: 145 passed |
| P3.1 | Smoke test, real data | In progress | Not yet run |
| P3.5 | Docs and repo reset | In progress | README, TECH_STACK, PLAN written; cleanup pending |
| P4a | vLLM serving | Done | Gate passed 2026-11-13: see evidence below |
| P4b | LiteLLM gateway | Scripts written; tested against a fake vLLM only | Run on the GPU machine to close |
| P5a-P10 | See `PLAN.md` | Not started | |

## Decisions
- ChromaDB only; one collection per kind; history kept as `<key>#v<N>`.
- Retrieval gets a read-only handle; admin holds the writer and is local-only.
- Import format: one JSON file. CSV later if needed.
- Retire/purge blocked while alignments use the record (`--cascade`, `--force`).
- Alignment = faculty teaching a course in a term. Program mapping deferred.
- **Stack: vLLM + LiteLLM + Chroma + FastAPI. No Ollama.**
- **Serving model: Qwen2.5-7B-Instruct-AWQ, awq_marlin, max_model_len 4096, gpu_memory_utilization 0.80.**
- Gateway auth: single master key for now (virtual keys need a database; revisit in P8).
- Embedding model stays BGE until P9a benchmark (Qwen3-Embedding-0.6B vs BGE-M3).

## P4a evidence (2026-11-13)
- Model: Qwen/Qwen2.5-7B-Instruct-AWQ, quantization awq_marlin, vLLM 0.33.0, GPU RTX 4070 SUPER (12282 MiB)
- max_model_len 4096, gpu_memory_utilization 0.80, enforce_eager true, VLLM_USE_FLASHINFER_SAMPLER=0
- curl returned text (3 back-to-back requests): yes; served name `minal-llm`
- nvidia-smi peak during inference: 11218 MiB; headroom 1064 MiB
- Measured with vLLM alone. The BGE embedder was not on the GPU, so headroom with it loaded is unknown.
- OOM observed: none
- Startup fix needed on WSL/conda: FlashInfer sampler needs nvcc, so it is switched off.

## Notes for later patches
- vLLM applies the model's own sampling defaults (temperature 0.7, top_p 0.8, top_k 20,
  repetition_penalty 1.05). P5a should set temperature explicitly (low, for grounded answers).
- The model identifies itself as Qwen. The P5b system prompt must set the Minal ambassador identity.
- Peak VRAM is set mostly by `gpu_memory_utilization` plus overhead (vLLM pre-allocates KV cache),
  not by `max_model_len`. Raising context to 6144 is not the headroom risk; adding the embedder is.

## Not yet verified
- Real BGE embedder end to end; `minal-admin` on a real on-disk store (P3.1).
- Retrieval quality on real questions (needs data, then P7b).
- VRAM headroom with the embedder on the GPU (run a `minal-admin search` while vLLM is up, then `nvidia-smi`).
- P4b gate on the real stack (`scripts/check_litellm.sh` with real vLLM behind it).

## Next actions
1. Run `scripts/p3_5_cleanup.sh`, fix the listed references, confirm 145 tests pass.
2. Fill in `docs/features/query.md`.
3. P3.1 smoke test with the real embedder, then load one department.
4. P4b: `setup_litellm_env.sh`, `serve_vllm.sh`, `serve_litellm.sh`, `check_litellm.sh`; paste the output.

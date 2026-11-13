# STATUS.md

**Project:** Minal
**Last updated:** 2026-11-13
**Current patch:** P3.1 (load real data) is now the blocker for the P5b manual check; P3.5 still open

---

| # | Patch | State | Evidence |
| :-- | :--- | :--- | :--- |
| P0 | Foundation | Done | `uv sync` and `uv run pytest` work |
| P1 | Database | Done | Memory and Chroma contract tests pass |
| P2 | Retrieval | Done | `tests/retrieval`: 24 passed |
| P3 | Admin CLI | Done (automated) | Full suite: 145 passed |
| P3.1 | Smoke test, real data | Script written, not yet run | `bash scripts/smoke_admin.sh` (throwaway stores under /tmp, real embedder on CPU) |
| P3.5 | Docs and repo reset | In progress | README, TECH_STACK, PLAN written; cleanup pending |
| P4a | vLLM serving | Done | Gate passed 2026-11-13: see evidence below |
| P4b | LiteLLM gateway | Done | `check_litellm.sh`: P4b GATE: PASS on the real stack, 2026-11-13 |
| P5a | LLM client and fake LLM | Done | Full suite 184 passed, 3 skipped; integration test 3 passed on the real stack, 2026-11-13 |
| P5b | Prompts and answer chain | Done (automated); manual check pending | Full suite 231 passed, 3 skipped on 2026-11-13. Manual: `scripts/ask.py` with 10 real questions once data is loaded |
| P5c-P10 | See `PLAN.md` | Not started | |

## Decisions
- ChromaDB only; one collection per kind; history kept as `<key>#v<N>`.
- Retrieval gets a read-only handle; admin holds the writer and is local-only.
- Import format: one JSON file. CSV later if needed.
- Retire/purge blocked while alignments use the record (`--cascade`, `--force`).
- Alignment = faculty teaching a course in a term. Program mapping deferred.
- **Stack: vLLM + LiteLLM + Chroma + FastAPI. No Ollama.**
- **Serving model: Qwen2.5-7B-Instruct-AWQ, awq_marlin, max_model_len 4096, gpu_memory_utilization 0.80.**
- LLM client uses httpx (already a dependency), not the openai SDK or litellm; errors are stable codes (`llm_*`).
- Answer chain decisions (query.md section 6): English only; uncited answers kept and flagged; small talk bypasses retrieval; `min_score` tuned later in P7b.
- Default store is `data/chroma` (CLI default); `scripts/ask.py` uses the same default and refuses to create a store.
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

## Cleanup added for P3.5
- `pyproject.toml`: remove the `gateway` dependency group (litellm now lives in conda env `minal-litellm`) and `opencv-contrib-python`; `pytest` is listed twice (runtime deps and dev).

## Cleanup added for P3.5 (continued)
- Fill in `AnswerConfig.office_contact` with the institute's real contact when known.

## Next actions
1. Run `scripts/p3_5_cleanup.sh`, fix the references it lists, confirm `uv run pytest` still passes (P3.5).
2. P3.1: `bash scripts/smoke_admin.sh`; paste the output. The first run downloads the BGE model.
3. Delete the empty store my earlier `ask.py` run created: `rm data/chroma.sqlite3` (check `ls data` first; the real store is `data/chroma`).
4. P5b manual check: `minal-admin import samples/sample_department.json --apply --data-dir data/sample`, then `python scripts/ask.py --data-dir data/sample --file scripts/questions.txt --log run1.jsonl --show-context` (vLLM and gateway running).
5. Then P5c (follow-up rewriting), or tune with the answers from step 4.

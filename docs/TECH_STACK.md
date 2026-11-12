# TECH_STACK.md

**Project:** Minal
**Purpose:** the stack we build on, and why. Replaces the older Ollama-based design.

| Layer | Choice | Why |
| :--- | :--- | :--- |
| Runtime | Python 3.12 + `uv` | Reproducible installs via `uv.lock` |
| Data store | ChromaDB (embedded, `PersistentClient`) | Single local store for vectors and records; no extra service |
| Embeddings | BGE, recorded per collection | A model mismatch is refused until `reindex` |
| Model serving | vLLM, quantized 7-8B instruct model | Fits 12 GB VRAM; OpenAI-compatible endpoint |
| Gateway | LiteLLM | One stable endpoint and virtual keys; the model can be swapped without app changes |
| API | FastAPI + pydantic-settings | Thin layer over the answer service |
| Ingestion | Docling | PDF/handbook to Markdown for chunking |
| Tracing and eval | Langfuse + a small eval set | See what happened; compare scores after each change |
| Tests | pytest with fakes | No downloads or running services in unit tests |

## Environments
- **App environment** (`uv`): db, retrieval, admin, llm client, API, Docling.
- **Serving environment** (separate): vLLM. It conflicts with Docling/torch in a
  single lockfile, so it lives in its own environment, launched from `scripts/`
  with config in `configs/`.

## Rules
1. The app calls LiteLLM, never vLLM directly.
2. AI-facing code gets a `DatabaseReader` only.
3. The admin surface is local-only and never exposed on the public API.
4. The model is chosen in P4 and recorded here; nothing else depends on which one.

## Removed
- Ollama and Llama 3.1 8B via Ollama: replaced by vLLM + LiteLLM.
- `requirements.txt`, `_legacy/`, `opencv-contrib-python`: removed in P3.5.

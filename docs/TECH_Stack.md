# TECH_STACK.md

**Project:** Minal
**Status:** Draft
**Related documents:** 01_Architecture.md, 02_Design_Decisions.md, 06_Backend.md

---

## 1. Purpose

This document defines the technology stack for Minal, records the rationale behind each choice, and establishes versioning and packaging conventions. It is the authoritative reference for what we build on and why. Any deviation from this stack should be recorded in `02_Design_Decisions.md`.

---

## 2. Stack Summary

| Layer | Component | Role |
| :--- | :--- | :--- |
| Language | Python 3.12+ | Primary implementation language |
| Package management | uv | Dependency resolution, virtualenv, lockfile |
| LLM inference | vLLM | Serves open-weight models behind an OpenAI-compatible API |
| LLM gateway | LiteLLM | Unified routing, spend tracking, fallbacks |
| Orchestration | LangChain | Retrieval pipelines and prompt composition |
| Document parsing | Docling | Layout-aware extraction to structured Markdown/JSON |
| Embeddings | sentence-transformers (BGE family) | Text-to-vector encoding |
| Vector store | ChromaDB | Persistent local vector database |
| Observability | Langfuse | Request tracing, token accounting, evaluation |

---

## 3. Layer-by-Layer Detail

### 3.1 Language and Runtime

- **Python 3.12+** is the target runtime. All components in the stack have first-class Python support, and the project already targets modern Python via `pyproject.toml`.
- A single virtual environment managed by `uv` is used across development and deployment to keep parity.

### 3.2 Package Management: uv

- **uv** is the sole dependency manager. `pyproject.toml` declares dependencies; `uv.lock` pins the resolved graph.
- All installs and script executions go through `uv` (`uv sync`, `uv run`). Do not use bare `pip install` in project workflows; it bypasses the lockfile.
- Rationale: reproducible builds, fast resolution, and a single lockfile for both local and CI environments.

### 3.3 LLM Inference: vLLM

- **Role:** serves the open-weight model over an OpenAI-compatible HTTP API.
- **Endpoint convention:** `http://<host>:8000/v1`.
- **Configuration:** model selection, `--max-model-len`, tensor parallelism, and GPU memory utilization are defined per deployment target.
- **Rationale:** PagedAttention-based KV cache management gives strong throughput under concurrent requests, and the OpenAI-compatible surface removes coupling between the application and the inference engine.
- **Reference:** `docs.vllm.ai` (Quickstart, API Reference, CLI Reference).

### 3.4 LLM Gateway: LiteLLM

- **Role:** single entry point between the application and all model providers.
- **Endpoint convention:** `http://<host>:4000/v1`.
- **Responsibilities:** virtual keys, per-key spend tracking, model routing, fallback chains, rate limits.
- **Rule:** application code calls LiteLLM, never vLLM directly. This preserves the ability to swap models, add cloud fallbacks, or change serving backends without touching application code.
- **Reference:** `docs.litellm.ai` (Gateway Quickstart, Virtual Keys).

### 3.5 Orchestration: LangChain

- **Role:** composes the retrieval pipeline, prompt templates, and model invocation into a single chain.
- **Usage pattern:** retriever → prompt template → LLM → output parser, expressed with LCEL runnables.
- **Rule:** retrieval and prompt composition live in LangChain; transport-level concerns (auth, retries, routing) belong to LiteLLM.
- **Reference:** `python.langchain.com` (Retrievers, Vector Store Integrations, LCEL).

### 3.6 Document Parsing: Docling

- **Role:** converts raw source documents (PDF, DOCX, PPTX, HTML) into structured Markdown or JSON with layout, tables, and reading order preserved.
- **Output contract:** Markdown is the canonical intermediate format passed to the chunker.
- **Rationale:** naive text extraction destroys table and header structure, which degrades retrieval quality. Layout-aware parsing is a prerequisite for reliable chunking.
- **Reference:** `docling-project.github.io` (Quickstart, Supported Formats, DocumentConverter API).

### 3.7 Embeddings: sentence-transformers (BGE)

- **Role:** encodes chunks and queries into dense vectors.
- **Default model:** `BAAI/bge-small-en-v1.5` for development. Larger BGE variants may be substituted for production accuracy.
- **Constraint:** the same embedding model must be used at ingestion and query time. Changing the model requires re-indexing the vector store.
- **Reference:** Hugging Face model cards; `sbert.net` for the runtime library.

### 3.8 Vector Store: ChromaDB

- **Role:** persists chunk embeddings and metadata, and performs similarity search with metadata filtering.
- **Mode:** `PersistentClient` for local development; client-server mode (`HttpClient` against a Chroma server) for shared or deployed environments.
- **Storage location:** configurable path, excluded from version control.
- **Reference:** `docs.trychroma.com` (Getting Started, Where Filters, Client-Server).

### 3.9 Observability: Langfuse

- **Role:** captures traces for every request, including retrieved chunks, prompts, token usage, and latency.
- **Deployment:** Langfuse Cloud (free tier) for development; self-hosted option reserved for later stages.
- **Instrumentation:** LangChain callback handler attached at chain invocation.
- **Reference:** `langfuse.com/docs` (Observability Overview, Tracing Get Started, Token and Cost Tracking).

---

## 4. Deployment Topology

The application is organized into two flows.

**Ingestion flow (offline, run on document change):**

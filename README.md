# Minal: NIELIT Imphal Ambassador Assistant

A local, offline AI assistant that acts as a college ambassador. It answers
questions from prospective students, parents and visitors about faculty,
courses, departments and notices, using only the institute's own data and
citing the passages it used. It runs on one machine with no cloud API
dependency at inference time.

> **Status:** under active development. See [`docs/STATUS.md`](docs/STATUS.md)
> for the current patch and [`docs/PLAN.md`](docs/PLAN.md) for the roadmap.

## How it works

```
question -> API -> answer service -> retrieval -> DatabaseReader -> ChromaDB
                        |
                        +-> LiteLLM gateway -> vLLM (local model) -> answer + citations

admin CLI -> Dispatcher -> Database (writer) -> embedder -> ChromaDB   (local only)
```

- **Read/write split.** The AI side only ever receives a read-only
  `DatabaseReader`. All writes go through the local admin CLI.
- **Grounded answers.** The model sees only retrieved records and cites them.
  With no relevant records it says it does not know.
- **One-way layers.** `api` and `admin` call `services`; `services` calls
  `retrieval`, `llm` and `db`. Nothing imports upward.

## Tech stack

| Concern | Choice |
| :--- | :--- |
| Language / packaging | Python 3.12, `uv`, `pyproject.toml` |
| Vector store | ChromaDB (embedded), one collection per record kind |
| Embeddings | BGE (loaded lazily) |
| Model serving | vLLM, quantized 7-8B instruct model sized for 12 GB VRAM |
| Model gateway | LiteLLM (the app calls LiteLLM, never vLLM directly) |
| API | FastAPI + pydantic-settings |
| Document ingestion | Docling (planned) |
| Observability | Langfuse (planned) |
| Tests | pytest, with fakes (in-memory backend, fake embedder, fake LLM) |

Details and rationale: [`docs/TECH_STACK.md`](docs/TECH_STACK.md).
There is no Ollama dependency.

## Project layout

```
src/minal/
  db/            Chroma-backed store, Dispatcher, reader/writer ports
  retrieval/     question -> numbered passages + context string
  admin/         minal-admin CLI (import, export, add, retire, ...)
  llm/           LiteLLM client, prompts          (planned)
  services/      answer chain                      (planned)
  api/           FastAPI layer                     (planned)
  auth/          roles and visibility              (planned)
  ingestion/     Docling document ingestion        (planned)
  observability/ Langfuse tracing                  (planned)
tests/           db, retrieval, admin (more as patches land)
docs/            PLAN.md, STATUS.md, TECH_STACK.md, features/*.md
configs/         LiteLLM and vLLM config          (planned)
scripts/         launch scripts                   (planned)
```

## Quick start

```bash
uv sync
uv run pytest                 # unit tests; no model or service needed
uv run minal-admin --help     # local data admin CLI
```

Model serving (vLLM + LiteLLM) is added in patch P4; until then the data
layer, retrieval and admin CLI are usable and tested on their own.

## Working on the project

Work is split into small patches (see `docs/PLAN.md`). Each patch has a
short feature doc in `docs/features/` written first, a test gate that must
pass, and an update to `docs/STATUS.md` before the next patch starts.

## License

See [`LICENSE`](LICENSE).

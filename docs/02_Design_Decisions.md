# Design Decisions

Each decision below is recorded with its reasoning so the choice can be
revisited deliberately later, rather than re-litigated from scratch.

---

## D1. Model: Hermes 3 8B, via Ollama

**Decision:** Approved. Supersedes the original Llama 3.1 8B Instruct
choice below (2026-08-03) — kept as-is, since Hermes 3 is a fine-tune
of that exact base model, not a different lineage.

**Reasoning:**

- **Fast response** — public-facing interaction needs to feel
  instantaneous; large delays make the assistant appear unintelligent.
- **GPU compatibility** — target hardware is an RTX 4070 (12 GB VRAM,
  laptop variant in the current build). The 8B quantized model occupies
  roughly the same VRAM footprint as Llama 3.1 8B (~4.7 GB), leaving
  headroom for the context window, KV cache, OS overhead, and future
  tool usage.
- **Instruction following** — the model follows conversational
  instructions reliably and resists prompt injection better than older
  models of similar size.
- **Tool-calling** — Hermes 3 is a Nous Research fine-tune of Llama 3.1
  8B specifically trained for structured output and function/tool
  calling. That's a better starting point for Phase 6 (tool calling,
  campus map search, etc.) than the vanilla instruct model, at no cost
  in size or speed.
- **Already available locally** — no `ollama pull` needed; it was
  already on the machine (`ollama list`).

Original reasoning for the Llama 3.1 8B Instruct family (still valid,
since Hermes 3 inherits the same base):

- Fast response, GPU compatibility, and reliable instruction following
  were the original selection criteria — see above, all still hold.

---

## D1a. Config: centralized `app/config.py` + `.env`

**Decision:** All environment-specific values (model name, Ollama host,
API key if any, app port) live in `.env` and are loaded through
`app/config.py` via `pydantic-settings`. No other module reads
environment variables directly.

**Reasoning:**

- Swapping models (as just happened with D1) should be a one-line `.env`
  edit, not a code change in `main.py` or `ollama_client.py`.
- `pydantic-settings` validates types (e.g. `app_port` is an `int`) and
  fails fast with a clear error instead of a confusing runtime bug.
- `ollama_api_key` is currently unused (local Ollama needs no auth) but
  is there for when Ollama sits behind a proxy, or the backend later
  talks to a hosted API instead.
- `.env` is gitignored; `.env.example` is the tracked template so the
  required keys are documented without leaking any real secrets.

---

## D2. Knowledge architecture: full-context injection, not RAG

**Decision:** Do **not** use Retrieval-Augmented Generation initially.
Instead, inject the relevant slice of the college dataset directly into
the prompt.

**Reasoning:**

Estimated total knowledge is small — roughly 100 faculty records and
~15,000 words across faculty, departments, labs, and courses. This is
well below Llama 3.1's context limit, so retrieval infrastructure would
add complexity without a corresponding benefit yet.

Advantages of skipping RAG for now:

- Zero retrieval latency
- Simpler implementation
- No vector database
- No embedding pipeline
- Easier debugging

**Upgrade trigger** — move to RAG only when one of these becomes true:

- Knowledge exceeds the context window
- Multiple colleges are supported from one deployment
- Source documents become very large
- PDFs need to become searchable

---

## D3. Development platform: Windows

**Decision:** Develop directly on Windows, not WSL/Linux, for now.

**Reasoning:**

- Ollama runs locally with direct GPU access on Windows
- Easier debugging during active development
- Lower networking complexity
- Faster development cycle

WSL may be used later for Docker-based or containerized deployment
testing, but isn't part of the day-to-day dev loop.

---

## D4. Data storage: flat JSON files, not a database (for now)

**Decision:** Store faculty/courses/labs/notices as JSON files under
`app/asset/`, accessed only through `app/db/repository.py`.

**Reasoning:**

- At ~100 records total, a database adds operational overhead
  (migrations, connection handling) without a real benefit.
- Routing all reads through one `db/` module means the eventual move to
  SQLite/Postgres is a single-seam change — nothing else in the app
  needs to know where the data physically lives.

**Upgrade trigger** — move to a real database when:

- Data needs concurrent writes (e.g. a staff editor UI, Phase 5)
- Record counts grow enough that substring search in
  `context_builder._search_data()` becomes noisy or slow
- Multi-user editing or audit history is needed

---

## D5. Search: plain substring matching, not embeddings

**Decision:** Match faculty/course/lab/notice records to a query with
plain substring matching in `context_builder._search_data()`.

**Reasoning:** Fine for ~100 rows total; embeddings would be premature
optimization at this scale. This is intentionally the single function
that would need to change if matches get noisy or the dataset grows —
see D2's upgrade trigger, which applies here too.

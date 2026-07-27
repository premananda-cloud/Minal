# NIELIT Imphal Ambassador Assistant — Architecture & Setup

## 1. What this is

A kiosk/server-based assistant for NIELIT Imphal. Visitors ask about
faculty, courses, labs, and notices; the app looks up relevant local
data and asks a locally-hosted LLM (via Ollama) to turn it into a
short, friendly answer. No cloud API calls, no internet dependency
at inference time — everything runs on one Windows PC.

## 2. Hardware & runtime

| Component | Spec |
|---|---|
| GPU | RTX 4070 Laptop (12 GB VRAM) |
| RAM | 32 GB system |
| Model runner | Ollama v0.32.1 (auto-detects GPU) |
| Model | `llama3.1:8b` (~4.7 GB VRAM, ~7 GB headroom) |
| API framework | FastAPI (Python), run via `uv` |

Model choice rationale: `llama3.1:8b` is proven for instruction
following and conversational quality, and the data size here (~100
records) doesn't need anything bigger. Headroom matters because
Windows + kiosk UI overhead eats into VRAM too.

## 3. High-level flow

```
Kiosk UI (browser/touchscreen)
        │  POST /ask { query }
        ▼
   FastAPI  (main.py)
        │  build_context(query)
        ▼
   skill/ layer
        │  ├─ run_all_skills()   → live facts (date/time, later: web search)
        │  ├─ search db/         → matching faculty/courses/labs/notices
        │  └─ load system prompt → identity, rules, tone
        ▼
   assembled prompt
        │  POST http://localhost:11434/api/generate
        ▼
   Ollama (llama3.1:8b)
        │  natural-language answer
        ▼
   FastAPI wraps in AskResponse
        ▼
   Kiosk UI displays answer
```

The two-hop design (client → FastAPI → Ollama) is intentional, not a
workaround:
- Ollama has no concept of your JSON data — something has to search
  it and build a context-stuffed prompt. That's FastAPI's job.
- The kiosk UI only ever talks to one clean endpoint (`/ask`). If you
  swap models, add a second model, or change how search works, the
  UI never needs to know.
- Logging, rate-limiting, caching, or a future admin panel all have
  a natural home in this layer.

## 4. Folder structure

```
rt/
  requirements.txt
  README.md
  ARCHITECTURE.md
  app/
    main.py                    # thin HTTP layer — no business logic
    schemas/
      ask.py                   # AskRequest, AskResponse (Pydantic, API boundary)
    models/
      entities.py              # Faculty, Course, Notice, LabInfo (domain entities)
    db/
      repository.py            # only file allowed to read asset/*.json
    skill/
      datetime_util.py         # current date/time as a "live fact"
      registry.py              # SKILLS list — the upgradable point
      context_builder.py       # orchestrates: skills + db search + system prompt → one prompt string
      ollama_client.py         # thin wrapper around Ollama's HTTP API
    asset/
      faculty.json
      courses.json
      notices.json
      labs.json
      prompts/
        system_prompt.txt      # assistant identity, rules, tone
```

### Why these boundaries

| Folder | Responsibility | Rule |
|---|---|---|
| `asset/` | Dumb storage | No logic. JSON in, JSON out. |
| `db/` | Data access | The *only* code that opens files in `asset/`. Everything else calls its functions (`get_faculty()`, `get_courses()`, etc.). This is the one seam to change if you ever move to SQLite/Postgres. |
| `models/` | Domain shape | Describes what's *inside* the JSON (`Faculty`, `Course`, `Notice`, `LabInfo`), independent of how a user asks for it. |
| `schemas/` | API shape | Describes what crosses the HTTP boundary (`AskRequest`, `AskResponse`). Different concern from `models/` — a response doesn't have to mirror a domain entity 1:1. |
| `skill/` | Orchestration | Anything that gathers or computes context before the LLM call: current time, keyword search over `db/`, (later) web search, prompt assembly, the Ollama call itself. |
| `main.py` | Protocol | Receive request → `build_context()` → `call_ollama()` → return response. Nothing else. If you're about to write an `if` about faculty/courses here, it belongs in `skill/` or `db/` instead. |

## 5. Request lifecycle (detailed)

1. **Kiosk UI** sends `POST /ask` with `{"query": "..."}`.
2. **`main.py`** validates it against `AskRequest`, calls
   `build_context(query)`.
3. **`context_builder.py`**:
   - loads `asset/prompts/system_prompt.txt` (identity + rules + tone)
   - calls `run_all_skills()` from `registry.py` → currently just
     `get_datetime_context()`, so the model knows what "today" or
     "this Friday" means
   - keyword-searches `db/repository.py` for faculty/courses/labs
     matching the query, plus all currently-active notices
   - stitches system prompt + live facts + matched data + the
     visitor's question into one prompt string
4. **`ollama_client.py`** POSTs that prompt to
   `http://localhost:11434/api/generate` with model `llama3.1:8b`.
5. **`main.py`** wraps the reply in `AskResponse` and returns it.

## 6. The system prompt (`asset/prompts/system_prompt.txt`)

Defines:
- **Identity** — the assistant is named "Yaifo" (placeholder, change
  freely), representing NIELIT Imphal.
- **Grounding rule** — only answer from the data provided in the
  prompt; never invent a faculty name, date, or notice.
- **Graceful unknowns** — if the answer isn't in the data, say so and
  point to the notice board or admin office instead of guessing.
- **Time awareness** — use the "live facts" date/time to resolve
  relative questions ("is there an exam this Friday?").
- **Tone** — short, conversational, friendly, kiosk-appropriate (no
  markdown, no essay-length answers).

Kept as a plain text file (not a Python string) so tone/rules can be
tuned without touching code.

## 7. The `skill/` upgrade path

`registry.py` holds a `SKILLS` list of zero-argument functions, each
returning a string fact or `""`. `run_all_skills()` runs all of them
and joins the results into the prompt's "Live facts" section.

Today: just `get_datetime_context()`.

Planned, not yet built (deliberately deferred — real time-sink risk):
- `web_search.py` — a skill that fires only when `db/` can't answer
  (e.g. an official exam date), hits a search API, and returns a
  short verified snippet. Add the file, register it in `SKILLS`, and
  nothing else in the app changes.

## 8. Data model

| File | Fields |
|---|---|
| `faculty.json` | `name, designation, department, email, room, specialization[]` |
| `courses.json` | `code, title, department, duration, eligibility, description` |
| `notices.json` | `title, date, body, expires_on` (filtered to active-only by default) |
| `labs.json` | `name, department, description, equipment[]` |

Search today is plain substring matching in
`context_builder._search_data()` — fine for ~100 rows total. If data
grows or matches get noisy, swap in embeddings there; it's the only
function that needs to change.

## 9. Setup

### Prerequisites
- Windows PC with the RTX 4070 laptop GPU, drivers installed
- [Ollama](https://ollama.com) installed and running
  (`ollama serve`, or it auto-starts as a background service)
- Python via `uv` (or plain `pip` + venv if you prefer)

### 9.1 Pull the model
```powershell
ollama pull llama3.1:8b
```
Confirm it's using the GPU:
```powershell
ollama ps
```

### 9.2 Install dependencies
From the `rt/` project root:
```powershell
uv sync
```
or, without `uv`:
```powershell
pip install -r requirements.txt
```

### 9.3 Add your real data
Replace the placeholder rows in:
- `app/asset/faculty.json`
- `app/asset/courses.json`
- `app/asset/notices.json`
- `app/asset/labs.json`

Each file is a plain JSON array of objects matching the fields in
section 8. Keep it under ~100 entries per file for latency.

### 9.4 Run the server
From the `rt/` directory (so `app` resolves as a package):
```powershell
uv run uvicorn app.main:app --reload
```
Server starts at `http://localhost:8000`.

### 9.5 Test it
```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"query\": \"who teaches computer science\"}"
```

Other endpoints:
- `GET /health` — liveness check
- `POST /refresh` — reload `asset/*.json` from disk without
  restarting the server (use this after editing data files)

### 9.6 Edit data without downtime
Edit any file in `app/asset/`, then:
```powershell
curl -X POST http://localhost:8000/refresh
```

## 10. Known constraints / things to revisit later

- **No auth** — fine for a single-kiosk LAN deployment; add before
  exposing this beyond one machine.
- **No conversation memory** — each `/ask` is stateless. `session_id`
  exists in `AskRequest` as a placeholder for future multi-turn
  support but isn't used yet.
- **No streaming** — `ollama_client.py` calls Ollama with
  `stream=False` for simplicity. Switch to `stream=True` +
  server-sent events later if answers feel slow on the kiosk screen.
- **Frontend** — not built yet. Planned: touchscreen kiosk UI, maybe
  a slideshow of the AI lab, maybe voice output. All of that talks to
  the same `/ask` endpoint — no backend changes needed.

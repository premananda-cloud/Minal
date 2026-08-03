# Backend

## 1. Folder structure

```
rt/
  requirements.txt
  README.md
  docs/
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

## 2. Why these boundaries

| Folder | Responsibility | Rule |
|---|---|---|
| `asset/` | Dumb storage | No logic. JSON in, JSON out. |
| `db/` | Data access | The *only* code that opens files in `asset/`. Everything else calls its functions (`get_faculty()`, `get_courses()`, etc.). This is the one seam to change if you ever move to SQLite/Postgres. |
| `models/` | Domain shape | Describes what's *inside* the JSON (`Faculty`, `Course`, `Notice`, `LabInfo`), independent of how a user asks for it. |
| `schemas/` | API shape | Describes what crosses the HTTP boundary (`AskRequest`, `AskResponse`). A response doesn't have to mirror a domain entity 1:1 — different concern from `models/`. |
| `skill/` | Orchestration | Anything that gathers or computes context before the LLM call: current time, keyword search over `db/`, (later) web search, prompt assembly, the Ollama call itself. |
| `main.py` | Protocol | Receive request → `build_context()` → `call_ollama()` → return response. Nothing else. If you're about to write an `if` about faculty/courses here, it belongs in `skill/` or `db/` instead. |

## 3. Request lifecycle (detailed)

1. **Kiosk UI** sends `POST /ask` with `{"query": "..."}`.
2. **`main.py`** validates it against `AskRequest`, calls `build_context(query)`.
3. **`context_builder.py`**:
   - loads `asset/prompts/system_prompt.txt` (identity + rules + tone)
   - calls `run_all_skills()` from `registry.py` → currently just
     `get_datetime_context()`, so the model knows what "today" or "this
     Friday" means
   - keyword-searches `db/repository.py` for faculty/courses/labs matching
     the query, plus all currently-active notices
   - stitches system prompt + live facts + matched data + the visitor's
     question into one prompt string
4. **`ollama_client.py`** POSTs that prompt to
   `http://localhost:11434/api/generate` with model `llama3.1:8b`.
5. **`main.py`** wraps the reply in `AskResponse` and returns it.

## 4. The `skill/` upgrade path

`registry.py` holds a `SKILLS` list of zero-argument functions, each
returning a string fact or `""`. `run_all_skills()` runs all of them and
joins the results into the prompt's "Live facts" section.

Today: just `get_datetime_context()`.

Planned, not yet built (deliberately deferred — real time-sink risk):

- `web_search.py` — a skill that fires only when `db/` can't answer (e.g.
  an official exam date), hits a search API, and returns a short verified
  snippet. Add the file, register it in `SKILLS`, and nothing else in the
  app changes.

## 5. Data model

See `04_Data_Schema.md` for full field-level detail. Summary:

| File | Fields |
|---|---|
| `faculty.json` | `name, designation, department, email, room, specialization[]` |
| `courses.json` | `code, title, department, duration, eligibility, description` |
| `notices.json` | `title, date, body, expires_on` (filtered to active-only by default) |
| `labs.json` | `name, department, description, equipment[]` |

Search today is plain substring matching in
`context_builder._search_data()` — fine for ~100 rows total (see
`02_Design_Decisions.md`, D5, for the upgrade trigger).

## 6. Setup

### Prerequisites

- Windows PC with the RTX 4070 GPU, drivers installed
- [Ollama](https://ollama.com) installed and running (`ollama serve`, or
  it auto-starts as a background service)
- Python via `uv` (or plain `pip` + venv)

### 6.1 Pull the model

```powershell
ollama pull llama3.1:8b
```

Confirm it's using the GPU:

```powershell
ollama ps
```

### 6.2 Install dependencies

From the `rt/` project root:

```powershell
uv sync
```

or, without `uv`:

```powershell
pip install -r requirements.txt
```

### 6.3 Add real data

Replace the placeholder rows in:

- `app/asset/faculty.json`
- `app/asset/courses.json`
- `app/asset/notices.json`
- `app/asset/labs.json`

Each file is a plain JSON array of objects matching the fields in
`04_Data_Schema.md`. Keep it under ~100 entries per file for latency.

### 6.4 Run the server

From the `rt/` directory (so `app` resolves as a package):

```powershell
uv run uvicorn app.main:app --reload
```

Server starts at `http://localhost:8000`. Endpoint details:
`05_API.md`.

### 6.5 Edit data without downtime

Edit any file in `app/asset/`, then:

```powershell
curl -X POST http://localhost:8000/refresh
```

# TODO

## Phase 2 — Knowledge base
- [ ] Collect real faculty data (replace placeholders in `faculty.json`)
- [ ] Collect real course data (`courses.json`)
- [ ] Collect real lab/infrastructure data (`labs.json`)
- [ ] Set up a process for keeping `notices.json` current

## Phase 3 — Backend
- [ ] Implement `db/repository.py` (faculty/courses/labs/notices getters)
- [ ] Implement `skill/context_builder.py` (system prompt + live facts + search → prompt string)
- [ ] Implement `skill/datetime_util.py` + register in `skill/registry.py`
- [ ] Implement `skill/ollama_client.py`
- [ ] Implement `main.py` (`/ask`, `/health`, `/refresh`)
- [ ] Add basic logging

## Known constraints to revisit
- [ ] **No auth** — add before exposing beyond one LAN/kiosk
- [ ] **No conversation memory** — `session_id` exists in `AskRequest` but is unused; design multi-turn support if needed
- [ ] **No streaming** — switch `ollama_client.py` to `stream=True` + SSE if kiosk answers feel slow
- [ ] **Search quality** — substring matching in `context_builder._search_data()` will need to become fuzzier/embeddings-based if data grows past ~100 rows or matches get noisy (see `docs/02_Design_Decisions.md`, D5)

## Phase 4 — Frontend
- [ ] Build kiosk/touchscreen chat UI (talks only to `/ask`)
- [ ] Decide on kiosk idle-state content (e.g. AI Lab slideshow)

## Phase 5 — Administration
- [ ] Staff-facing editor for `asset/*.json`
- [ ] Validation before writes (avoid malformed JSON breaking `/refresh`)

## Phase 6 — Advanced features (not started, exploratory)
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] Vision
- [ ] Campus map / room navigation
- [ ] Tool/function calling
- [ ] `web_search.py` skill (fires only when local data can't answer)
- [ ] Move to a real database if concurrent writes or audit history become necessary
- [ ] Move to RAG if knowledge outgrows context window or multiple colleges are supported (see `docs/02_Design_Decisions.md`, D2)

# Changelog

All notable progress on this project, newest first.

## 2026-07-24

- Ran `llama3.1:8b` locally via Ollama, server up at
  `http://localhost:11434`.
- Finalized Phase 1 architecture: folder layout (`asset/`, `db/`,
  `models/`, `schemas/`, `skill/`, `main.py`), two-hop request flow
  (kiosk → FastAPI → Ollama), and the decision to inject full context
  instead of using RAG for now.
- Defined JSON schema for `courses.json`, `faculty.json`, `labs.json`,
  and `notices.json`.
- Wrote initial system prompt rules (grounding, graceful unknowns, time
  awareness, tone).

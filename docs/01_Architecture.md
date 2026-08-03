# Architecture Overview

## 1. What this is

A kiosk/server-based assistant for NIELIT Imphal. Visitors ask about
faculty, courses, labs, and notices; the app looks up relevant local data
and asks a locally-hosted LLM (via Ollama) to turn it into a short,
friendly answer. No cloud API calls, no internet dependency at inference
time — everything runs on one Windows PC.

## 2. Hardware & runtime

| Component | Spec |
|---|---|
| GPU | RTX 4070 Laptop (12 GB VRAM) |
| RAM | 32 GB system |
| Model runner | Ollama v0.32.1 (auto-detects GPU) |
| Model | `llama3.1:8b` (~4.7 GB VRAM, ~7 GB headroom) |
| API framework | FastAPI (Python), run via `uv` |

See `02_Design_Decisions.md` for why this model and this hardware profile
were chosen.

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

- Ollama has no concept of the JSON data — something has to search it and
  build a context-stuffed prompt. That's FastAPI's job.
- The kiosk UI only ever talks to one clean endpoint (`/ask`). Swapping
  models, adding a second model, or changing how search works never
  requires a UI change.
- Logging, rate-limiting, caching, or a future admin panel all have a
  natural home in this layer.

Module-level folder structure and responsibilities are covered in
`06_Backend.md`; the request lifecycle step-by-step is also detailed there.

## 4. Known constraints (current state)

- **No auth** — acceptable for a single-kiosk LAN deployment; add before
  exposing this beyond one machine.
- **No conversation memory** — each `/ask` is stateless. `session_id`
  exists in `AskRequest` as a placeholder for future multi-turn support
  but isn't used yet.
- **No streaming** — `ollama_client.py` calls Ollama with `stream=False`
  for simplicity. Revisit if answers feel slow on the kiosk screen.
- **Frontend** — not built yet (Phase 4). Planned: touchscreen kiosk UI,
  possibly a slideshow of the AI lab, possibly voice output. All of it
  will talk to the same `/ask` endpoint — no backend changes needed.

See `TODO.md` for the actionable version of this list.

# API Reference

FastAPI app (`app/main.py`), served locally at `http://localhost:8000`.
`main.py` is intentionally a thin protocol layer — see `06_Backend.md`
for where the actual logic lives.

CORS is enabled for all origins (`allow_origins=["*"]`), since the
kiosk client (`Minal-client.html`) is typically opened as a local file
or served from a different port than the API. Fine for a single-machine
kiosk; tighten this before exposing the API beyond localhost/LAN.

---

## `POST /ask`

Ask the assistant a question. Supports multi-turn conversations via
`session_id`, and the model can call internal tools (faculty/course/lab
lookups, active notices) before answering — see `06_Backend.md` for how
the tool-calling loop works.

**Request body** (`AskRequest`, `app/schemas/ask.py`):

```json
{
  "query": "who teaches computer science",
  "session_id": null
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `query` | `string` | Yes | The visitor's question, natural language |
| `session_id` | `string` \| `null` | No | Omit or send `null` on the first turn. The server generates one and returns it — send that same value back on every subsequent turn in the conversation to keep history. |

**Response body** (`AskResponse`, `app/schemas/ask.py`):

```json
{
  "answer": "Dr. Sanasam is the HoD for Computer Science, based in room CS-101.",
  "sources": ["search_faculty:computer science"],
  "model_used": "hermes3:8b",
  "session_id": "1b6f6f2e-4b3a-4e9d-9c2a-2d6a7f0c9e11"
}
```

| Field | Type | Notes |
|---|---|---|
| `answer` | `string` | The assistant's reply. |
| `sources` | `list[string]` \| `null` | Which internal tools were used to answer, as `"tool_name:query"` (e.g. `"search_faculty:machine learning"`). `null` if the model answered without calling any tool. Informational — not meant to be shown verbatim to visitors. |
| `model_used` | `string` | The Ollama model that generated the answer, from `OLLAMA_MODEL` in `.env`. |
| `session_id` | `string` | Always present in the response, even if you sent `null` in the request. **Store this and send it back** on the next `/ask` call to continue the same conversation. |

**Example — first turn (no session yet):**

```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"query\": \"who teaches computer science\"}"
```

**Example — following turn (reusing the returned session_id):**

```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"query\": \"where is their office\", \"session_id\": \"1b6f6f2e-4b3a-4e9d-9c2a-2d6a7f0c9e11\"}"
```

---

## `GET /health`

Liveness check. Returns `200 OK` if the server is up. Use this for kiosk
watchdog scripts or uptime monitoring.

```json
{ "status": "ok", "model": "hermes3:8b" }
```

---

## `POST /session/{session_id}/reset`

Clears conversation history for a given session (e.g. when a visitor
starts a fresh chat on the kiosk). Does not delete anything from the
underlying data — only forgets the turn-by-turn history for that
`session_id`.

```powershell
curl -X POST http://localhost:8000/session/1b6f6f2e-4b3a-4e9d-9c2a-2d6a7f0c9e11/reset
```

```json
{ "status": "reset", "session_id": "1b6f6f2e-4b3a-4e9d-9c2a-2d6a7f0c9e11" }
```

Safe to call even if the `session_id` is unknown to the server (e.g.
already expired or never used) — it's a no-op in that case, not an error.

---

## `POST /refresh`

Reloads `app/asset/*.json` from disk without restarting the server. Call
this after editing any data file:

```powershell
curl -X POST http://localhost:8000/refresh
```

---

## Session history: what frontend devs should know

- History lives **in server memory only**, keyed by `session_id`. It is
  lost on server restart and does not persist to disk.
- Only the last few turns are kept per session (`MAX_TURNS` in
  `session_store.py`) — don't rely on a session remembering an entire
  long conversation indefinitely.
- This only works correctly with a **single** uvicorn worker process. If
  the API is ever run with multiple workers, each would have its own
  in-memory session store and history would appear to randomly vanish.

---

## Not yet implemented

- Authentication (see `TODO.md` — needed before exposing beyond one LAN)
- Streaming responses (`ollama_client.py` currently calls Ollama with
  `stream=False`)
- Persistent session history across server restarts (currently in-memory
  only — see `session_store.py`)

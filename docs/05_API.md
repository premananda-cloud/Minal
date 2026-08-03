# API Reference

FastAPI app (`app/main.py`), served locally at `http://localhost:8000`.
`main.py` is intentionally a thin protocol layer — see `06_Backend.md`
for where the actual logic lives.

---

## `POST /ask`

Ask the assistant a question.

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
| `session_id` | `string` \| `null` | No | Placeholder for future multi-turn support; not used yet |

**Response body** (`AskResponse`):

```json
{
  "answer": "Dr. Sanasam is the HoD for Computer Science, based in room CS-101."
}
```

**Example:**

```powershell
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"query\": \"who teaches computer science\"}"
```

---

## `GET /health`

Liveness check. Returns `200 OK` if the server is up. Use this for kiosk
watchdog scripts or uptime monitoring.

---

## `POST /refresh`

Reloads `app/asset/*.json` from disk without restarting the server. Call
this after editing any data file:

```powershell
curl -X POST http://localhost:8000/refresh
```

---

## Not yet implemented

- Authentication (see `TODO.md` — needed before exposing beyond one LAN)
- Streaming responses (`ollama_client.py` currently calls Ollama with
  `stream=False`)
- Multi-turn conversation using `session_id`

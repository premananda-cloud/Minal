"""
main.py — thin HTTP layer only.

Protocol per request:
  1. Receive AskRequest from kiosk UI (query + optional session_id).
  2. If no session_id, generate one (new conversation).
  3. Look up that session's history from session_store.
  4. Ask skill/ to build the chat messages (system + history + current query).
  5. Call Ollama's chat endpoint with those messages.
  6. Save this turn (query, answer) back into session_store.
  7. Wrap the reply in AskResponse (including session_id) and return it.

No business logic here. If you're tempted to add an `if` about
faculty/courses/history-trimming in this file, it belongs in skill/ instead.
"""

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import AskRequest, AskResponse
from app.skill.context_builder import build_messages
from app.skill.ollama_client import call_ollama_chat, DEFAULT_MODEL
from app.skill import session_store
from app.db import repository as db

app = FastAPI(title="NIELIT Imphal Ambassador Assistant")

# Allow the kiosk frontend (served from a different origin/file://) to call this API.
# Tighten allow_origins to your actual kiosk URL before deploying beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.refresh()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    session_id = request.session_id or str(uuid.uuid4())
    history = session_store.get_history(session_id)

    messages = build_messages(request.query, history)
    try:
        answer = call_ollama_chat(messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {e}")

    session_store.append_turn(session_id, request.query, answer)

    return AskResponse(answer=answer, model_used=DEFAULT_MODEL, session_id=session_id)


@app.post("/session/{session_id}/reset")
def reset_session(session_id: str):
    """Kiosk should call this when a visitor walks away / a new visitor starts."""
    session_store.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}


@app.post("/refresh")
def refresh_data():
    """Call this after editing asset/*.json without restarting the server."""
    db.refresh()
    return {"status": "refreshed"}


@app.get("/health")
def health():
    return {"status": "ok"}

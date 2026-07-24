"""
main.py — thin HTTP layer only.

Protocol per request:
  1. Receive AskRequest from kiosk UI.
  2. Ask skill/ to build the full context (datetime + matched data + system prompt).
  3. Call Ollama with that context.
  4. Wrap the reply in AskResponse and return it.

No business logic here. If you're tempted to add a `if` about
faculty/courses/notices in this file, it belongs in skill/ or db/ instead.
"""

from fastapi import FastAPI, HTTPException

from app.schemas import AskRequest, AskResponse
from app.skill.context_builder import build_context
from app.skill.ollama_client import call_ollama, DEFAULT_MODEL
from app.db import repository as db

app = FastAPI(title="NIELIT Imphal Ambassador Assistant")


@app.on_event("startup")
def on_startup():
    db.refresh()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    prompt = build_context(request.query)
    try:
        answer = call_ollama(prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama call failed: {e}")

    return AskResponse(answer=answer, model_used=DEFAULT_MODEL)


@app.post("/refresh")
def refresh_data():
    """Call this after editing asset/*.json without restarting the server."""
    db.refresh()
    return {"status": "refreshed"}


@app.get("/health")
def health():
    return {"status": "ok"}

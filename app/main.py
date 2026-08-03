"""
Thin HTTP layer. No business logic lives here — see skill/context_builder.py,
skill/ollama_client.py, skill/tools.py, and skill/session_store.py for the
actual work.
"""

import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.schemas.ask import AskRequest, AskResponse
from app.skill.context_builder import build_messages
from app.skill.ollama_client import chat_with_tools
from app.skill.tools import TOOL_SCHEMAS, TOOL_DISPATCH
from app.skill import session_store

app = FastAPI(title="NIELIT Imphal Ambassador Assistant")

# Minal-client.html is opened as a local file (or served from a different
# origin/port than uvicorn), so the browser treats every /ask, /reset, etc.
# call as cross-origin. Without this, the browser blocks the requests before
# they even reach FastAPI — you'd see it as a CORS error in devtools, not as
# a 4xx/5xx from the server. Kiosk is single-machine/trusted, so allow_origins
# "*" is fine here; tighten this if the API is ever exposed beyond localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.ollama_model}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    session_id = request.session_id or str(uuid.uuid4())

    history = session_store.get_history(session_id)
    messages = build_messages(request.query, history=history)

    answer, sources = chat_with_tools(
        messages,
        tools=TOOL_SCHEMAS,
        dispatch=TOOL_DISPATCH,
    )

    session_store.append_turn(session_id, request.query, answer)

    return AskResponse(
        answer=answer,
        sources=sources or None,
        model_used=settings.ollama_model,
        session_id=session_id,
    )


@app.post("/session/{session_id}/reset")
def reset(session_id: str) -> dict:
    session_store.reset_session(session_id)
    return {"status": "reset", "session_id": session_id}


@app.post("/refresh")
def refresh() -> dict:
    # db/repository.py should expose a reload_all() that re-reads asset/*.json
    from app.db.repository import reload_all

    reload_all()
    return {"status": "reloaded"}


if __name__ == "__main__":
    import uvicorn

    # `uv run uvicorn app.main:app --reload` also works and is fine for
    # dev, but running this file directly respects APP_HOST/APP_PORT
    # from .env without you having to remember extra flags.
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=True)

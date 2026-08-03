"""
Thin HTTP layer. No business logic lives here — see skill/context_builder.py
and skill/ollama_client.py for the actual work.
"""

from fastapi import FastAPI

from app.config import settings
from app.schemas.ask import AskRequest, AskResponse
from app.skill.context_builder import build_context
from app.skill.ollama_client import generate

app = FastAPI(title="NIELIT Imphal Ambassador Assistant")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": settings.ollama_model}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    prompt = build_context(request.query)
    answer = generate(prompt)
    return AskResponse(answer=answer)


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

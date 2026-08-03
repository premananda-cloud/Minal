"""
Thin wrapper around Ollama's HTTP API.

All connection details (host, model, timeout, key) come from
app/config.py — nothing here is hardcoded, so switching models or
pointing at a different Ollama instance is a .env edit, not a code edit.
"""

import httpx

from app.config import settings


def generate(prompt: str) -> str:
    """Send a fully-assembled prompt to Ollama and return the reply text."""
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    response = httpx.post(
        f"{settings.ollama_host}/api/generate",
        json={
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
        },
        headers=headers,
        timeout=settings.ollama_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()["response"]

"""
Centralized application configuration.

Everything that might change between machines/deployments (model name,
ports, credentials) lives in `.env`, not in code. Import `settings`
anywhere you need one of these values:

    from app.config import settings
    settings.ollama_model

Never edit main.py (or anything else) to change the model, port, etc. —
edit `.env` instead. See `.env.example` for the full list of keys.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# pydantic-settings resolves a relative env_file path against the process's
# current working directory, not against this file's location. That means
# `uv run uvicorn app.main:app` behaves differently depending on whether you
# launch it from the repo root, from app/, or from an IDE with its own CWD —
# and silently falls back to defaults if .env isn't found there, with no
# error. Pinning this to a path next to config.py makes it work the same
# regardless of where the process is launched from.
ENV_PATH = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    # --- Ollama ---
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "hermes3:8b"
    ollama_api_key: Optional[str] = None  # local Ollama needs no key; kept for a future remote/proxied Ollama or a hosted API
    ollama_timeout_seconds: float = 60.0

    # --- App server ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- Misc ---
    log_level: str = "info"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",       # unknown keys in .env won't crash the app
    )

    @field_validator("ollama_host")
    @classmethod
    def _normalize_ollama_host(cls, v: str) -> str:
        """
        Ollama's own docs have you set OLLAMA_HOST as a bare host:port
        (e.g. "0.0.0.0:11434") when configuring the Ollama *server* itself.
        It's an easy, reasonable mistake to copy that same format into this
        app's .env — but here OLLAMA_HOST needs to be a full URL, since it's
        passed straight to httpx. A bare host:port fails deep in httpx with
        a confusing "missing protocol" error instead of a clear message here.

        So: strip whitespace/trailing slash, and if there's no scheme,
        assume http:// (Ollama has no built-in TLS, so http is the
        correct default, not a guess).
        """
        v = v.strip().rstrip("/")
        if not v:
            raise ValueError(
                "OLLAMA_HOST is empty. Set it in .env, e.g. "
                "OLLAMA_HOST=http://localhost:11434"
            )
        if "://" not in v:
            v = f"http://{v}"
        return v


@lru_cache
def get_settings() -> Settings:
    """.env is only read once per process; every import after the first is free."""
    return Settings()


settings = get_settings()

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
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",       # unknown keys in .env won't crash the app
    )


@lru_cache
def get_settings() -> Settings:
    """.env is only read once per process; every import after the first is free."""
    return Settings()


settings = get_settings()

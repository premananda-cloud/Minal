"""
Thin wrapper around the local Ollama server. Nothing else in the
app should know Ollama's request/response shape — only this file.
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.1:8b"


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={"model": model, "prompt": prompt, "stream": stream},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()

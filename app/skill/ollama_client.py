"""
Thin wrapper around the local Ollama server. Nothing else in the
app should know Ollama's request/response shape — only this file.
"""

import requests
from typing import List, Dict

OLLAMA_BASE = "http://localhost:11434"
GENERATE_URL = f"{OLLAMA_BASE}/api/generate"
CHAT_URL = f"{OLLAMA_BASE}/api/chat"
DEFAULT_MODEL = "llama3.1:8b"


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False) -> str:
    """Single-shot prompt, no message history. Kept for simple/one-off calls."""
    response = requests.post(
        GENERATE_URL,
        json={"model": model, "prompt": prompt, "stream": stream},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def call_ollama_chat(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    """
    Multi-turn chat. `messages` is a list of {"role": "system"|"user"|"assistant", "content": str},
    oldest first. Ollama's /api/chat understands roles natively, so conversation
    history doesn't need to be flattened into one giant prompt string.
    """
    response = requests.post(
        CHAT_URL,
        json={"model": model, "messages": messages, "stream": False},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "").strip()

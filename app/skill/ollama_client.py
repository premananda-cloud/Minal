"""
Thin wrapper around the local Ollama server. Nothing else in the
app should know Ollama's request/response shape — only this file.
"""

import json
import requests
from typing import List, Dict, Any, Callable

OLLAMA_BASE = "http://localhost:11434"
GENERATE_URL = f"{OLLAMA_BASE}/api/generate"
CHAT_URL = f"{OLLAMA_BASE}/api/chat"
DEFAULT_MODEL = "llama3.1:8b"

MAX_TOOL_ROUNDS = 5  # hard cap so a confused model can't loop forever


def call_ollama(prompt: str, model: str = DEFAULT_MODEL, stream: bool = False) -> str:
    """Single-shot prompt, no message history, no tools. Kept for simple/one-off calls."""
    response = requests.post(
        GENERATE_URL,
        json={"model": model, "prompt": prompt, "stream": stream},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("response", "").strip()


def _chat_once(messages: List[Dict[str, Any]], tools: List[Dict] = None, model: str = DEFAULT_MODEL) -> Dict:
    """One call to /api/chat. Returns the raw `message` object from Ollama's response."""
    payload = {"model": model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools

    response = requests.post(CHAT_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {})


def call_ollama_chat(messages: List[Dict[str, str]], model: str = DEFAULT_MODEL) -> str:
    """Multi-turn chat, no tools. Kept for cases that don't need data lookups."""
    message = _chat_once(messages, tools=None, model=model)
    return (message.get("content") or "").strip()


def call_ollama_chat_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict],
    dispatch: Dict[str, Callable[[dict], str]],
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Multi-turn chat where the model can call tools to pull data it needs.

    Loop:
      1. Send messages + tool schemas to Ollama.
      2. If the model's reply requests tool calls, run each one locally
         via `dispatch`, append the results as role="tool" messages,
         and go back to step 1.
      3. If the model replies with plain content (no tool calls), that's
         the final answer — return it.

    `messages` is mutated in place (tool calls/results get appended),
    matching how Ollama expects the running conversation to be threaded.
    """
    for _ in range(MAX_TOOL_ROUNDS):
        message = _chat_once(messages, tools=tools, model=model)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return (message.get("content") or "").strip()

        # Record the assistant's tool-call request, then run each tool.
        messages.append(message)

        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name")
            raw_args = fn.get("arguments", {})
            # Ollama usually gives arguments as a dict already; handle a
            # stringified-JSON fallback just in case.
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args) if raw_args else {}
                except json.JSONDecodeError:
                    args = {}
            else:
                args = raw_args or {}

            if name in dispatch:
                try:
                    result = dispatch[name](args)
                except Exception as e:
                    result = f"Tool error: {e}"
            else:
                result = f"Unknown tool: {name}"

            messages.append({"role": "tool", "content": result})

    # Model kept calling tools past the round cap — ask it to wrap up plainly.
    message = _chat_once(messages, tools=None, model=model)
    return (message.get("content") or "I wasn't able to find that — please check with the admin office.").strip()

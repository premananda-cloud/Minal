"""
Thin wrapper around Ollama's /api/chat, including the tool-calling loop.

All connection details (host, model, timeout, key) come from
app/config.py — nothing here is hardcoded, so switching models or
pointing at a different Ollama instance is a .env edit, not a code edit.

Tool calling: Ollama's /api/chat mirrors OpenAI-style function calling.
If `tools` is passed and the model wants to use one, the response's
`message` contains a `tool_calls` list instead of (or alongside) plain
content. We then:
  1. append that assistant message (with its tool_calls) to the
     conversation, exactly as returned,
  2. run each requested tool via `dispatch`,
  3. append one {"role": "tool", "name": ..., "content": ...} message
     per call with the JSON-serializable result,
  4. send the whole thing back to the model for another round.

This repeats until the model replies with no tool_calls (a final
answer), or `max_rounds` is hit, at which point we ask once more
without tools so it's forced to answer with whatever it already has.
"""

import json
from typing import Callable, Dict, List, Optional, Tuple

import httpx

from app.config import settings


def _headers() -> dict:
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"
    return headers


def _post_chat(messages: List[Dict], tools: Optional[List[Dict]]) -> Dict:
    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    response = httpx.post(
        f"{settings.ollama_host}/api/chat",
        json=payload,
        headers=_headers(),
        timeout=settings.ollama_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def chat_with_tools(
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    dispatch: Optional[Dict[str, Callable[[dict], str]]] = None,
    max_rounds: int = 5,
) -> Tuple[str, List[str]]:
    """
    Runs the full tool-calling conversation and returns (answer, sources).

    `messages` is mutated in place (tool turns get appended) — pass a
    list you don't need untouched afterwards.

    `sources` is a simple log of "tool_name:query" strings for every
    tool call made, oldest first — good enough to populate
    AskResponse.sources without main.py needing to know tool internals.
    """
    sources: List[str] = []

    for _ in range(max_rounds):
        data = _post_chat(messages, tools)
        message = data["message"]
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message.get("content", ""), sources

        messages.append(message)

        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

            if dispatch and name in dispatch:
                result = dispatch[name](args)
            else:
                result = f"Error: unknown tool '{name}'"

            query = args.get("query", "") if isinstance(args, dict) else ""
            sources.append(f"{name}:{query}" if query else name)

            messages.append({"role": "tool", "name": name, "content": result})

    # Exhausted max_rounds without a final answer — force one, no tools,
    # so a model stuck in a call-loop still returns something to the visitor.
    data = _post_chat(messages, tools=None)
    return data["message"].get("content", ""), sources

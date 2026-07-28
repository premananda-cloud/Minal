"""
Builds what gets sent to Ollama.

Two different strategies are used for the two kinds of data:

  - Live facts (current date/time) and active notices are small,
    general-purpose, and useful on almost every turn — so they're
    still PUSHED straight into the system message.

  - Faculty / courses / labs are NOT pushed anymore. Previously this
    file guessed what was relevant with a keyword search against the
    raw query text, which silently failed whenever the visitor's
    wording didn't overlap with a name/department/title — it looked
    like the model "couldn't access" the data. Instead, those are now
    exposed as TOOLS (see tools.py) that the model calls itself, with
    whatever search term it thinks is right, and can retry or chain
    across multiple calls in one turn.

main.py should only ever call build_messages() — it shouldn't know
about db/, asset/, or tools.py directly.
"""

from pathlib import Path
from typing import List, Dict, Tuple
from app.skill.registry import run_all_skills
from app.db import repository as db

PROMPT_DIR = Path(__file__).resolve().parent.parent / "asset" / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system_prompt.txt"


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_PATH.exists():
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return "You are a helpful assistant."


def _active_notices_summary() -> str:
    notices = db.get_notices(active_only=True)
    if not notices:
        return "No active notices right now."
    lines = [f"- [{n.date}] {n.title}: {n.body}" for n in notices]
    return "\n".join(lines)


def build_messages(
    query: str, history: List[Tuple[str, str]] = None
) -> List[Dict[str, str]]:
    """
    Returns a messages list for Ollama's /api/chat:
      [ {role: system, content: identity+rules+live facts+active notices},
        ...prior turns from history (user/assistant, oldest first)...,
        {role: user, content: query} ]

    Faculty/course/lab data is deliberately NOT included here — the
    model pulls that itself via tools (see tools.py + main.py, which
    passes TOOL_SCHEMAS/TOOL_DISPATCH into the Ollama call).

    `history` is a list of (role, content) tuples from session_store,
    e.g. [("user", "who teaches ML?"), ("assistant", "Dr. X does.")].
    """
    system_prompt = _load_system_prompt()
    skill_facts = run_all_skills()
    notices = _active_notices_summary()

    system_content = (
        f"{system_prompt}\n\n"
        f"--- Live facts ---\n{skill_facts}\n\n"
        f"--- Active notices ---\n{notices}\n\n"
        f"You have tools available to look up faculty, courses, and labs. "
        f"Call them whenever a visitor asks about something specific — "
        f"never guess or invent a name, code, or detail."
    )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

    for role, content in (history or []):
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": query})
    return messages

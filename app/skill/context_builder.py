"""
Builds what gets sent to Ollama:
  1. runs all registered skills (datetime, later maybe web search)
  2. searches db/ for records relevant to the user's CURRENT query
  3. loads the system prompt template
  4. stitches it into either a single prompt string (build_context)
     or a role-tagged message list for /api/chat (build_messages)

main.py should only ever call these — it shouldn't know about
db/, asset/, or session_store directly.

Note on multi-turn: the system message is rebuilt fresh on every
call using only the LATEST query, so the data grounding (live facts +
matched faculty/course/notice rows) always reflects what's relevant
right now. Prior turns are threaded in as plain user/assistant
messages so the model keeps conversational context ("his email?"
resolving to whoever "he" was) without stale data grounding.
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


def _search_data(query: str) -> str:
    """Naive keyword search across faculty/courses/notices/labs.
    Good enough for ~100 entries; upgrade to embeddings later if needed."""
    sections = []

    faculty = db.get_faculty(query)
    if faculty:
        lines = [f"- {f.name}, {f.designation}, {f.department}" for f in faculty]
        sections.append("Faculty:\n" + "\n".join(lines))

    courses = db.get_courses(query)
    if courses:
        lines = [f"- {c.code}: {c.title} ({c.department})" for c in courses]
        sections.append("Courses:\n" + "\n".join(lines))

    labs = db.get_labs(query)
    if labs:
        lines = [f"- {l.name} ({l.department})" for l in labs]
        sections.append("Labs:\n" + "\n".join(lines))

    # Notices aren't keyword-filtered — just show active ones, model decides relevance
    notices = db.get_notices(active_only=True)
    if notices:
        lines = [f"- [{n.date}] {n.title}: {n.body}" for n in notices]
        sections.append("Active notices:\n" + "\n".join(lines))

    return "\n\n".join(sections) if sections else "No matching records found."


def build_context(query: str) -> str:
    system_prompt = _load_system_prompt()
    skill_facts = run_all_skills()
    matched_data = _search_data(query)

    return (
        f"{system_prompt}\n\n"
        f"--- Live facts ---\n{skill_facts}\n\n"
        f"--- Relevant data ---\n{matched_data}\n\n"
        f"--- Visitor question ---\n{query}"
    )


def build_messages(
    query: str, history: List[Tuple[str, str]] = None
) -> List[Dict[str, str]]:
    """
    Returns a messages list for Ollama's /api/chat:
      [ {role: system, content: prompt+facts+data},
        ...prior turns from history (user/assistant, oldest first)...,
        {role: user, content: query} ]

    `history` is a list of (role, content) tuples from session_store,
    e.g. [("user", "who teaches ML?"), ("assistant", "Dr. X does.")].
    """
    system_prompt = _load_system_prompt()
    skill_facts = run_all_skills()
    matched_data = _search_data(query)

    system_content = (
        f"{system_prompt}\n\n"
        f"--- Live facts ---\n{skill_facts}\n\n"
        f"--- Relevant data ---\n{matched_data}"
    )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

    for role, content in (history or []):
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": query})
    return messages

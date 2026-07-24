"""
Builds the full context block sent to Ollama:
  1. runs all registered skills (datetime, later maybe web search)
  2. searches db/ for records relevant to the user's query
  3. loads the system prompt template
  4. stitches it all together into one prompt string

main.py should only ever call build_context(query) — it shouldn't
know about db/ or asset/ directly.
"""

from pathlib import Path
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

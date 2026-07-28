"""
Tool definitions for the LLM to PULL data on demand, instead of us
guessing what's relevant from the raw query text and pushing it in.

This is the fix for "the model can't access the JSON": before, only
_search_data() in context_builder.py decided what data the model saw,
using a naive substring match against the query. If the visitor's
wording didn't overlap with a name/department/title, the model got
nothing — it looked like the data wasn't there at all.

With tools, the model itself decides when it needs a lookup and what
to search for (which can differ from the visitor's exact wording —
e.g. it can retry "CS" after "computer science" returns nothing), and
can chain lookups (find the faculty member, then reason about their
department) across multiple tool calls in one turn.

Each tool's `parameters` schema is JSON Schema, per Ollama/OpenAI-style
function calling. TOOL_DISPATCH maps a tool name to the actual Python
function that runs the lookup and returns a JSON-serializable result.
"""

import json
from app.db import repository as db

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_faculty",
            "description": (
                "Search faculty by name or department keyword. Use this whenever "
                "a visitor asks about a specific teacher, HoD, or department staff. "
                "Call with an empty query to list all faculty."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Name or department keyword to search for. Empty string lists everyone.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_courses",
            "description": (
                "Search courses by title, course code, or department keyword. Use this "
                "whenever a visitor asks about a course, its duration, or eligibility."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Title, code, or department keyword to search for. Empty string lists all courses.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_labs",
            "description": "Search labs by name or department keyword.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Lab name or department keyword. Empty string lists all labs.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_notices",
            "description": (
                "Get currently active notices (admissions, exam dates, events). "
                "Call this whenever a visitor asks about dates, notices, or anything "
                "time-sensitive — expired notices are already filtered out for you."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _search_faculty(query: str = "") -> str:
    results = db.get_faculty(query or None)
    if not results:
        return "No matching faculty found."
    return json.dumps([r.model_dump() for r in results])


def _search_courses(query: str = "") -> str:
    results = db.get_courses(query or None)
    if not results:
        return "No matching courses found."
    return json.dumps([r.model_dump() for r in results])


def _search_labs(query: str = "") -> str:
    results = db.get_labs(query or None)
    if not results:
        return "No matching labs found."
    return json.dumps([r.model_dump() for r in results])


def _get_active_notices() -> str:
    results = db.get_notices(active_only=True)
    if not results:
        return "No active notices right now."
    return json.dumps([r.model_dump() for r in results])


TOOL_DISPATCH = {
    "search_faculty": lambda args: _search_faculty(args.get("query", "")),
    "search_courses": lambda args: _search_courses(args.get("query", "")),
    "search_labs": lambda args: _search_labs(args.get("query", "")),
    "get_active_notices": lambda args: _get_active_notices(),
}

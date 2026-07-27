"""
In-memory conversation history, keyed by session_id.

Deliberately simple: a dict in process memory, capped per session.
Good enough for a single kiosk process. Constraints to know about:
  - History is lost on server restart.
  - Does NOT work if you ever run multiple uvicorn workers/processes
    (each process would have its own dict). Fine for one kiosk PC.
  - No persistence, no expiry — sessions just accumulate until restart.
    Add a TTL/eviction pass here first if that becomes a problem.

If this needs to survive restarts or scale to multiple processes later,
swap the dict for Redis here — nothing outside this file should need
to change (same get_history/append_turn/reset_session function shapes).
"""

from collections import deque
from typing import Deque, Dict, List, Tuple

MAX_TURNS = 6  # how many past (query, answer) pairs to keep per session

# session_id -> deque of (role, content) messages, oldest first
_sessions: Dict[str, Deque[Tuple[str, str]]] = {}


def get_history(session_id: str) -> List[Tuple[str, str]]:
    """Returns list of (role, content) tuples, oldest first. Empty if unknown session."""
    if session_id not in _sessions:
        return []
    return list(_sessions[session_id])


def append_turn(session_id: str, user_query: str, assistant_answer: str) -> None:
    if session_id not in _sessions:
        _sessions[session_id] = deque(maxlen=MAX_TURNS * 2)  # *2: user + assistant per turn
    _sessions[session_id].append(("user", user_query))
    _sessions[session_id].append(("assistant", assistant_answer))


def reset_session(session_id: str) -> None:
    _sessions.pop(session_id, None)

"""
Request/response shapes that cross the HTTP boundary.
These validate what the kiosk UI sends and receives — nothing more.
"""

from pydantic import BaseModel
from typing import Optional


class AskRequest(BaseModel):
    query: str
    session_id: Optional[str] = None  # for future multi-turn kiosk sessions


class AskResponse(BaseModel):
    answer: str
    sources: Optional[list[str]] = None  # e.g. ["faculty:Dr. X", "notice:CCC Exam"]
    model_used: str
    session_id: str  # echoed back so the client can persist it across turns

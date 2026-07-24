"""
Domain entities — describe what's INSIDE asset/*.json.
These are independent of how a user asks for them (see schemas/ for that).
"""

from pydantic import BaseModel
from typing import Optional, List


class Faculty(BaseModel):
    name: str
    designation: str
    department: str
    email: Optional[str] = None
    room: Optional[str] = None
    specialization: Optional[List[str]] = None


class Course(BaseModel):
    code: str
    title: str
    department: str
    duration: Optional[str] = None
    eligibility: Optional[str] = None
    description: Optional[str] = None


class Notice(BaseModel):
    title: str
    date: str  # ISO format YYYY-MM-DD
    body: str
    expires_on: Optional[str] = None  # ISO date; if past, notice is inactive


class LabInfo(BaseModel):
    name: str
    department: str
    description: Optional[str] = None
    equipment: Optional[List[str]] = None

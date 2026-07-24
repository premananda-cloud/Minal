"""
db/ is the ONLY layer allowed to open files in asset/.
Everything else (skill/, main.py) calls these functions instead of
touching JSON directly. This is your one seam if you ever swap
JSON for SQLite/Postgres later — only this file changes.
"""

import json
from pathlib import Path
from datetime import date
from typing import List, Optional

from app.models import Faculty, Course, Notice, LabInfo

ASSET_DIR = Path(__file__).resolve().parent.parent / "asset"

# ---- simple in-memory cache, refreshed on demand ----
_cache = {
    "faculty": None,
    "courses": None,
    "notices": None,
    "labs": None,
}


def _load_json(filename: str) -> list:
    path = ASSET_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def refresh() -> None:
    """Force-reload all data from disk. Call this if asset/*.json changed."""
    _cache["faculty"] = [Faculty(**f) for f in _load_json("faculty.json")]
    _cache["courses"] = [Course(**c) for c in _load_json("courses.json")]
    _cache["notices"] = [Notice(**n) for n in _load_json("notices.json")]
    _cache["labs"] = [LabInfo(**l) for l in _load_json("labs.json")]


def _ensure_loaded() -> None:
    if _cache["faculty"] is None:
        refresh()


def get_faculty(name: Optional[str] = None) -> List[Faculty]:
    _ensure_loaded()
    data = _cache["faculty"]
    if name:
        name_lower = name.lower()
        return [f for f in data if name_lower in f.name.lower()]
    return data


def get_courses(query: Optional[str] = None) -> List[Course]:
    _ensure_loaded()
    data = _cache["courses"]
    if query:
        q = query.lower()
        return [
            c for c in data
            if q in c.title.lower() or q in c.code.lower() or q in c.department.lower()
        ]
    return data


def get_notices(active_only: bool = True) -> List[Notice]:
    _ensure_loaded()
    data = _cache["notices"]
    if not active_only:
        return data
    today = date.today().isoformat()
    return [n for n in data if not n.expires_on or n.expires_on >= today]


def get_labs(query: Optional[str] = None) -> List[LabInfo]:
    _ensure_loaded()
    data = _cache["labs"]
    if query:
        q = query.lower()
        return [l for l in data if q in l.name.lower() or q in l.department.lower()]
    return data

"""
Minimal skill: current date/time awareness.

The model has no clock. Without this, "is there an exam this Friday?"
is unanswerable. This runs on every prompt and gets embedded into
the context sent to Ollama.
"""

from datetime import datetime


def get_datetime_context() -> str:
    now = datetime.now()
    return (
        f"Current date: {now.strftime('%A, %d %B %Y')}. "
        f"Current time: {now.strftime('%H:%M')}."
    )

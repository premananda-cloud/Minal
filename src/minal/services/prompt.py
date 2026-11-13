"""Build the chat messages for one question. Pure function, easy to test."""
from __future__ import annotations

import re

from minal.llm.models import ChatMessage
from minal.llm.prompts import system_prompt
from minal.retrieval.models import RetrievalResult

_TAG = re.compile(r"<\s*(/?)\s*records\s*>", re.IGNORECASE)


def _neutralize(text: str) -> str:
    """Records and questions are untrusted; stop them closing or faking the <records> block."""
    return _TAG.sub(lambda m: f"({m.group(1)}records tag removed)", text)


def build_messages(
    question: str, result: RetrievalResult, *, office_contact: str | None = None
) -> list[ChatMessage]:
    user = (
        f"Today's date: {result.as_of.isoformat()}\n\n"
        f"<records>\n{_neutralize(result.context)}\n</records>\n\n"
        f"Question: {_neutralize(question)}"
    )
    return [
        ChatMessage(role="system", content=system_prompt(office_contact)),
        ChatMessage(role="user", content=user),
    ]


def build_small_talk_messages(question: str, *, office_contact: str | None = None
                              ) -> list[ChatMessage]:
    return [
        ChatMessage(role="system", content=system_prompt(office_contact, small_talk=True)),
        ChatMessage(role="user", content=_neutralize(question)),
    ]

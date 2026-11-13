"""Answer-chain contract."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from minal.db import Kind
from minal.llm.models import Usage
from minal.retrieval.models import Passage


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


# answered   - the model cited at least one real record
# declined   - the model said it does not have the information (no citation expected)
# uncited    - the model answered without citing any real record (logged for evaluation)
# no_records - retrieval found nothing; the fixed reply was returned and the LLM was not called
# chat       - small talk; answered without records
AnswerStatus = Literal["answered", "declined", "uncited", "no_records", "chat"]


class AnswerConfig(_M):
    model_config = ConfigDict(extra="forbid", frozen=True)

    top_k: int = Field(default=5, ge=1, le=20)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    office_contact: str | None = None   # e.g. "the NIELIT Imphal office (phone/email)"

    def no_records_text(self) -> str:
        who = self.office_contact or "the institute office"
        return f"I don't have that information. Please contact {who} for help."


class CitedRecord(_M):
    ref: int
    kind: Kind
    key: str


class Answer(_M):
    question: str
    text: str                              # shown to the visitor, [n] markers kept in
    status: AnswerStatus
    citations: list[CitedRecord] = Field(default_factory=list)   # in order of first use
    removed_citations: int = 0             # markers pointing at records that do not exist
    passages: list[Passage] = Field(default_factory=list)        # everything retrieval gave
    as_of: date | None = None
    usage: Usage = Field(default_factory=Usage)

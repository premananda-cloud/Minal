"""Schema for college data. Chroma is schemaless, so this module IS the schema.

Three kinds of record:
  course     - a course in the catalogue
  faculty    - a faculty member
  alignment  - a faculty member assigned to a course in a term

Every record has optional valid_from / valid_to dates so the AI can be asked
what was true as of a given day.
"""
from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = 1


class Kind(StrEnum):
    COURSE = "course"
    FACULTY = "faculty"
    ALIGNMENT = "alignment"


# '#' and '|' are used internally to build history ids and alignment keys.
Ident = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[^#|]+$")
]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ClassVar[Kind]
    # Fields that may be used as exact-match filters in list/search.
    FILTERABLE: ClassVar[frozenset[str]] = frozenset()

    valid_from: date | None = None
    valid_to: date | None = None

    @model_validator(mode="after")
    def _check_validity_window(self):
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not be before valid_from")
        return self

    @property
    def key(self) -> str:
        raise NotImplementedError

    def to_text(self) -> str:
        """Natural-language rendering of the record. This is what gets embedded."""
        raise NotImplementedError

    def filter_fields(self) -> dict[str, str | int | float | bool]:
        out: dict[str, str | int | float | bool] = {}
        for name in self.FILTERABLE:
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        return out


class Course(Record):
    kind: ClassVar[Kind] = Kind.COURSE
    FILTERABLE: ClassVar[frozenset[str]] = frozenset(
        {"department", "level", "academic_year", "credits"}
    )

    code: Ident
    title: Text
    department: Text
    credits: float = Field(ge=0)
    description: str = ""
    level: str | None = None
    prerequisites: list[Ident] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    academic_year: str | None = None

    @field_validator("code")
    @classmethod
    def _upper_code(cls, v: str) -> str:
        return v.upper()

    @field_validator("prerequisites")
    @classmethod
    def _upper_prereqs(cls, v: list[str]) -> list[str]:
        return [p.upper() for p in v]

    @property
    def key(self) -> str:
        return self.code

    def to_text(self) -> str:
        parts = [
            f"Course {self.code}: {self.title}.",
            f"Department: {self.department}.",
            f"Credits: {self.credits:g}.",
        ]
        if self.level:
            parts.append(f"Level: {self.level}.")
        if self.academic_year:
            parts.append(f"Academic year: {self.academic_year}.")
        if self.description:
            parts.append(self.description)
        if self.prerequisites:
            parts.append("Prerequisites: " + ", ".join(self.prerequisites) + ".")
        if self.outcomes:
            parts.append("Learning outcomes: " + "; ".join(self.outcomes) + ".")
        return " ".join(parts)


class Faculty(Record):
    kind: ClassVar[Kind] = Kind.FACULTY
    FILTERABLE: ClassVar[frozenset[str]] = frozenset({"department", "designation"})

    id: Ident
    name: Text
    department: Text
    designation: str | None = None
    email: str | None = None
    expertise: list[str] = Field(default_factory=list)
    bio: str = ""

    @property
    def key(self) -> str:
        return self.id

    def to_text(self) -> str:
        role = self.designation or "faculty member"
        parts = [f"{self.name} ({self.id}), {role} in the {self.department} department."]
        if self.expertise:
            parts.append("Expertise: " + ", ".join(self.expertise) + ".")
        if self.bio:
            parts.append(self.bio)
        return " ".join(parts)


class Alignment(Record):
    """A faculty member assigned to a course for a term."""

    kind: ClassVar[Kind] = Kind.ALIGNMENT
    FILTERABLE: ClassVar[frozenset[str]] = frozenset(
        {"course_code", "faculty_id", "term", "role"}
    )

    course_code: Ident
    faculty_id: Ident
    term: Ident
    role: Text = "instructor"
    section: str | None = None
    # Filled in by the writer from the referenced records; do not set by hand.
    course_title: str | None = None
    faculty_name: str | None = None

    @field_validator("course_code")
    @classmethod
    def _upper_code(cls, v: str) -> str:
        return v.upper()

    @property
    def key(self) -> str:
        return f"{self.course_code}|{self.faculty_id}|{self.term}"

    def to_text(self) -> str:
        who = self.faculty_name or self.faculty_id
        what = f"{self.course_title} ({self.course_code})" if self.course_title else self.course_code
        text = f"{who} is {self.role} for {what} in {self.term}."
        if self.section:
            text += f" Section {self.section}."
        return text


KINDS: dict[Kind, type[Record]] = {
    Kind.COURSE: Course,
    Kind.FACULTY: Faculty,
    Kind.ALIGNMENT: Alignment,
}


def record_class(kind: Kind) -> type[Record]:
    return KINDS[kind]

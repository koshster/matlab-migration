"""Pydantic data schemas for course, roster, and assignment administration.

Defines input validation models for course setup, staff assignments, CSV roster
importing, and polymorphic assignment problem slot configurations.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.auth import _EmailBody


class CourseCreateRequest(BaseModel):
    """Payload for creating a new academic course section."""

    code: str = Field(
        min_length=1,
        max_length=64,
        description="Course subject code (e.g. MAE-030A)",
    )
    term: str = Field(
        min_length=1,
        max_length=64,
        description="Academic term (e.g. Fall 2026)",
    )
    section: str = Field(
        default="001",
        max_length=32,
        description="Section code (e.g. 001)",
    )
    title: str = Field(
        default="",
        max_length=255,
        description="Full descriptive course title",
    )


class CourseUpdateRequest(BaseModel):
    """Payload for updating course metadata or archive status."""

    title: str | None = Field(default=None, max_length=255)
    isArchived: bool | None = Field(default=None)


class CourseInstructorCreateRequest(_EmailBody):
    """Payload for inviting an instructor or TA to a course staff roster."""

    role: str = Field(
        default="ta",
        description="Staff permission role: owner, instructor, ta, reader",
    )


class CourseInstructorRoleUpdate(BaseModel):
    """Payload for updating a staff member's permission role."""

    role: str = Field(description="New permission role: owner, instructor, ta, reader")


class RosterEntryCreate(BaseModel):
    """Individual student row from CSV roster batch import."""

    pid: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    firstName: str | None = Field(default=None, max_length=128)
    lastName: str | None = Field(default=None, max_length=128)


class RosterImportRequest(BaseModel):
    """Batch roster CSV import payload."""

    entries: list[RosterEntryCreate] = Field(default_factory=list)


class ProblemSlotSpec(BaseModel):
    """Specification of an individual problem slot within an assignment."""

    orderIndex: int = Field(ge=1, description="1-indexed problem slot position")
    problemType: str = Field(
        default="truss",
        max_length=64,
        description="Domain identifier (e.g. truss, beam, rigid_body)",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Domain difficulty knobs (e.g. num_nodes, max_force)",
    )
    points: float = Field(
        default=1.0,
        ge=0.0,
        description="Points weight for grading",
    )


class AssignmentCreateRequest(BaseModel):
    """Payload for creating a new homework assignment shell."""

    title: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=128)
    instructions: str = Field(default="", max_length=2048)
    tolerance: float = Field(default=0.01, ge=0.0001, le=0.5)
    feedbackMode: str = Field(default="per_field")
    maxAttempts: int | None = Field(default=None, ge=1)
    penaltyPerAttempt: float = Field(default=0.0, ge=0.0)
    scoringStrategy: str = Field(default="pass_fail")
    allowLate: bool = Field(default=False)
    latePenaltyRate: float = Field(default=0.0, ge=0.0)
    audience: str = Field(default="all")
    targetEntryIds: list[str] = Field(default_factory=list)
    problems: list[ProblemSlotSpec] = Field(default_factory=list)


class AssignmentUpdateRequest(BaseModel):
    """Payload for modifying an existing homework assignment."""

    title: str | None = Field(default=None, max_length=255)
    slug: str | None = Field(default=None, max_length=128)
    instructions: str | None = Field(default=None, max_length=2048)
    tolerance: float | None = Field(default=None, ge=0.0001, le=0.5)
    feedbackMode: str | None = Field(default=None)
    maxAttempts: int | None = Field(default=None)
    penaltyPerAttempt: float | None = Field(default=None, ge=0.0)
    scoringStrategy: str | None = Field(default=None)
    allowLate: bool | None = Field(default=None)
    latePenaltyRate: float | None = Field(default=None, ge=0.0)
    audience: str | None = Field(default=None)
    targetEntryIds: list[str] | None = Field(default=None)
    problems: list[ProblemSlotSpec] | None = Field(default=None)


class PublishAssignmentRequest(BaseModel):
    """Payload for publishing or unpublishing an assignment."""

    isPublished: bool

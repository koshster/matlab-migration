"""Pydantic data schemas for course, roster, and assignment administration.

Defines input validation models for course setup, staff assignments, CSV roster
importing, and polymorphic assignment problem slot configurations.
"""

from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.schemas.auth import _EmailBody
from app.services.access import as_utc


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


def _assert_date_order(
    opens_at: datetime | None,
    due_at: datetime | None,
    hard_deadline_at: datetime | None,
) -> None:
    """Reject a schedule that cannot happen: open <= due <= hard deadline.

    Normalizes first: on a PATCH these are compared against values already
    stored, and a store that drops the offset (SQLite, as every test uses)
    hands back naive datetimes that cannot be compared to an aware request.
    """
    opens_at = as_utc(opens_at)
    due_at = as_utc(due_at)
    hard_deadline_at = as_utc(hard_deadline_at)
    if opens_at and due_at and opens_at > due_at:
        raise ValueError("opensAt must not be after dueAt")
    if due_at and hard_deadline_at and due_at > hard_deadline_at:
        raise ValueError("dueAt must not be after hardDeadlineAt")
    if opens_at and hard_deadline_at and opens_at > hard_deadline_at:
        raise ValueError("opensAt must not be after hardDeadlineAt")


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
    # AwareDatetime, not datetime: a grading deadline that is ambiguous by the
    # client's UTC offset is a support ticket. Make callers send an offset.
    opensAt: AwareDatetime | None = Field(default=None)
    dueAt: AwareDatetime | None = Field(default=None)
    hardDeadlineAt: AwareDatetime | None = Field(default=None)
    revealSolutionsAfterClose: bool = Field(default=False)
    audience: str = Field(default="all")
    targetEntryIds: list[str] = Field(default_factory=list)
    problems: list[ProblemSlotSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def _dates_in_order(self) -> "AssignmentCreateRequest":
        _assert_date_order(self.opensAt, self.dueAt, self.hardDeadlineAt)
        return self


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
    # These three are cleared by sending an explicit null, so the router reads
    # model_fields_set rather than testing for None.
    opensAt: AwareDatetime | None = Field(default=None)
    dueAt: AwareDatetime | None = Field(default=None)
    hardDeadlineAt: AwareDatetime | None = Field(default=None)
    revealSolutionsAfterClose: bool | None = Field(default=None)
    audience: str | None = Field(default=None)
    targetEntryIds: list[str] | None = Field(default=None)
    problems: list[ProblemSlotSpec] | None = Field(default=None)


class PublishAssignmentRequest(BaseModel):
    """Payload for publishing or unpublishing an assignment."""

    isPublished: bool

"""Assignment, problem slot, target audience, session, and submission SQLAlchemy models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.courses import Course, RosterEntry
    from app.db.models.users import Student


class Assignment(Base):
    """Homework assignment containing 1..N polymorphic problem slots."""

    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str] = mapped_column(String(2048), default="", nullable=False)
    tolerance: Mapped[float] = mapped_column(Float, default=0.01, nullable=False)
    feedback_mode: Mapped[str] = mapped_column(String(32), default="per_field", nullable=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    penalty_per_attempt: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scoring_strategy: Mapped[str] = mapped_column(String(32), default="pass_fail", nullable=False)
    allow_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_penalty_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    audience: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hard_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reveal_solutions_after_close: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    course: Mapped["Course"] = relationship(back_populates="assignments")
    problems: Mapped[list["AssignmentProblem"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentProblem.order_index",
    )
    student_assignments: Mapped[list["StudentAssignment"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )
    targets: Mapped[list["AssignmentTarget"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class AssignmentTarget(Base):
    """Junction table associating assignments to specific roster entries for selected audience."""

    __tablename__ = "assignment_targets"
    __table_args__ = (
        UniqueConstraint("assignment_id", "roster_entry_id", name="uq_assignment_roster_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    roster_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roster_entries.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    assignment: Mapped["Assignment"] = relationship(back_populates="targets")
    roster_entry: Mapped["RosterEntry"] = relationship(back_populates="targets")


class AssignmentProblem(Base):
    """Problem slot within an assignment (polymorphic problem_type + difficulty params)."""

    __tablename__ = "assignment_problems"
    __table_args__ = (
        UniqueConstraint("assignment_id", "order_index", name="uq_assignment_order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_type: Mapped[str] = mapped_column(String(64), default="truss", nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Relationships
    assignment: Mapped["Assignment"] = relationship(back_populates="problems")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="assignment_problem", cascade="all, delete-orphan"
    )


class StudentAssignment(Base):
    """Student assignment session with unique, immutable per-assignment random seed."""

    __tablename__ = "student_assignments"
    __table_args__ = (
        UniqueConstraint("student_id", "assignment_id", name="uq_student_assignment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    draft_answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Distinct from submitted_at on purpose: an assignment that closed on its
    # deadline is final, but the student never pressed Submit. Conflating the
    # two would report a submission that did not happen.
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="student_assignments")
    assignment: Mapped["Assignment"] = relationship(back_populates="student_assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="student_assignment", cascade="all, delete-orphan"
    )


class Submission(Base):
    """Audit log of individual problem attempt submissions."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignment_problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignment_problems.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    field_verdicts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    student_assignment: Mapped["StudentAssignment"] = relationship(back_populates="submissions")
    assignment_problem: Mapped["AssignmentProblem"] = relationship(back_populates="submissions")

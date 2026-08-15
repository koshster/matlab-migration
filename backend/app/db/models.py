from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Student(Base):
    """Student account."""

    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pid: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    student_assignments: Mapped[list["StudentAssignment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class Instructor(Base):
    """Instructor or TA account for admin access."""

    __tablename__ = "instructors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    courses: Mapped[list["Course"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )


class Course(Base):
    """Academic course section."""

    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("instructors.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    term: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    instructor: Mapped["Instructor"] = relationship(back_populates="courses")
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["Assignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class CourseEnrollment(Base):
    """Junction table tracking student enrollment status per course section."""

    __tablename__ = "course_enrollments"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_course_student_enrollment"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dropped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    course: Mapped["Course"] = relationship(back_populates="enrollments")
    student: Mapped["Student"] = relationship(back_populates="enrollments")


class Assignment(Base):
    """Homework assignment containing N problems."""

    __tablename__ = "assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    tolerance: Mapped[float] = mapped_column(Float, default=0.01, nullable=False)
    feedback_mode: Mapped[str] = mapped_column(
        String(32), default="per_field", nullable=False
    )
    max_attempts: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    penalty_per_attempt: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    scoring_strategy: Mapped[str] = mapped_column(
        String(32), default="pass_fail", nullable=False
    )
    allow_late: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    late_penalty_rate: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    hard_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped["Course"] = relationship(back_populates="assignments")
    problems: Mapped[list["AssignmentProblem"]] = relationship(
        back_populates="assignment",
        cascade="all, delete-orphan",
        order_by="AssignmentProblem.order_index",
    )
    student_assignments: Mapped[list["StudentAssignment"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class AssignmentProblem(Base):
    """Problem slot within an assignment (polymorphic problem_type + params)."""

    __tablename__ = "assignment_problems"
    __table_args__ = (
        UniqueConstraint("assignment_id", "order_index", name="uq_assignment_order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
    )
    problem_type: Mapped[str] = mapped_column(
        String(64), default="truss", nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

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

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    student: Mapped["Student"] = relationship(back_populates="student_assignments")
    assignment: Mapped["Assignment"] = relationship(back_populates="student_assignments")
    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="student_assignment", cascade="all, delete-orphan"
    )


class Submission(Base):
    """Audit log of individual problem attempt submissions."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
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
    field_verdicts: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    student_assignment: Mapped["StudentAssignment"] = relationship(
        back_populates="submissions"
    )
    assignment_problem: Mapped["AssignmentProblem"] = relationship(
        back_populates="submissions"
    )

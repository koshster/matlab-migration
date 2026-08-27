"""User account SQLAlchemy models for students and instructors."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.assignments import StudentAssignment
    from app.db.models.courses import Course, CourseEnrollment, CourseInstructor, RosterEntry


class Student(Base):
    """Student user account identified by their institutional PID."""

    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pid: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        comment="University Student ID (e.g. A10000001)",
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    student_assignments: Mapped[list["StudentAssignment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    roster_entries: Mapped[list["RosterEntry"]] = relationship(back_populates="student")


class Instructor(Base):
    """Instructor or Teaching Assistant account for course management."""

    __tablename__ = "instructors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    courses: Mapped[list["Course"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )
    staff_roles: Mapped[list["CourseInstructor"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )

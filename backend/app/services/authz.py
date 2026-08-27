"""Authorization helpers for instructor-facing routes.

`require_course_role` and `assert_course_role` are the single choke point
for course-scoped access. Resolves membership through `courses.instructor_id`
(owner) and `course_instructors` junction table (owner, instructor, ta, reader).
"""

import uuid
from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_instructor_id
from app.db.models import Course, CourseInstructor, Instructor
from app.db.session import get_db

CourseRole = Literal["owner", "instructor", "ta", "reader"]

# Ordered least- to most-privileged; `_at_least` compares by index.
ROLE_HIERARCHY: tuple[CourseRole, ...] = ("reader", "ta", "instructor", "owner")
_ROLE_ORDER = ROLE_HIERARCHY


def _at_least(actual: CourseRole, minimum: CourseRole) -> bool:
    """Check if actual role meets or exceeds minimum required role."""
    return _ROLE_ORDER.index(actual) >= _ROLE_ORDER.index(minimum)


async def require_instructor(
    instructor_id: uuid.UUID = Depends(get_current_instructor_id),
    db: AsyncSession = Depends(get_db),
) -> Instructor:
    """Resolve the signed-in instructor, rejecting tokens for deleted accounts."""
    row = await db.execute(select(Instructor).where(Instructor.id == instructor_id))
    instructor = row.scalar_one_or_none()
    if instructor is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return instructor


async def _load_role(
    db: AsyncSession, course_id: uuid.UUID, instructor_id: uuid.UUID
) -> CourseRole | None:
    """Return the instructor's role on a course, or None if they have no access."""
    row = await db.execute(select(Course).where(Course.id == course_id))
    course = row.scalar_one_or_none()
    if course is None:
        return None
    if course.instructor_id == instructor_id:
        return "owner"

    staff_row = await db.execute(
        select(CourseInstructor).where(
            CourseInstructor.course_id == course_id,
            CourseInstructor.instructor_id == instructor_id,
        )
    )
    staff = staff_row.scalar_one_or_none()
    if staff is not None and staff.role in _ROLE_ORDER:
        return staff.role

    return None


async def get_effective_course_role(
    db: AsyncSession, course_id: uuid.UUID, instructor: Instructor
) -> CourseRole | None:
    """Public helper returning effective role of an instructor on a course."""
    return await _load_role(db, course_id, instructor.id)


async def assert_course_role(
    db: AsyncSession,
    course_id: uuid.UUID,
    instructor: Instructor,
    minimum: CourseRole = "ta",
) -> CourseRole:
    """Raise unless `instructor` holds at least `minimum` on `course_id`.

    Returns 404 rather than 403 when they have no access at all, so an
    instructor cannot enumerate other instructors' course ids.
    """
    role = await _load_role(db, course_id, instructor.id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not _at_least(role, minimum):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient course role"
        )
    return role

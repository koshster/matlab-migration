"""Authorization helpers for instructor-facing routes.

`require_course_role` is deliberately the single choke point for course-scoped
access. Today it resolves membership through `courses.instructor_id` (one owner
per course). Phase B adds a `course_instructors(course_id, instructor_id, role)`
junction so TAs and co-instructors can be granted access; when it lands, only
`_load_role` below should need to change — callers and route signatures stay
as they are.
"""

import uuid
from typing import Literal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_instructor_id
from app.db.models import Course, Instructor
from app.db.session import get_db

CourseRole = Literal["owner", "instructor", "ta", "reader"]

# Ordered least- to most-privileged; `_at_least` compares by index.
_ROLE_ORDER: tuple[CourseRole, ...] = ("reader", "ta", "instructor", "owner")


def _at_least(actual: CourseRole, minimum: CourseRole) -> bool:
    return _ROLE_ORDER.index(actual) >= _ROLE_ORDER.index(minimum)


async def require_instructor(
    instructor_id: uuid.UUID = Depends(get_current_instructor_id),
    db: AsyncSession = Depends(get_db),
) -> Instructor:
    """Resolve the signed-in instructor, rejecting tokens for deleted accounts."""
    row = await db.execute(select(Instructor).where(Instructor.id == instructor_id))
    instructor = row.scalar_one_or_none()
    if instructor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return instructor


async def _load_role(
    db: AsyncSession, course_id: uuid.UUID, instructor_id: uuid.UUID
) -> CourseRole | None:
    """Return the instructor's role on a course, or None if they have no access.

    Phase B: replace this body with a `course_instructors` lookup.
    """
    row = await db.execute(select(Course).where(Course.id == course_id))
    course = row.scalar_one_or_none()
    if course is None:
        return None
    if course.instructor_id == instructor_id:
        return "owner"
    return None


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

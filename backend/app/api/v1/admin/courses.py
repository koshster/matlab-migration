"""Course management and teaching staff administration endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.admin.helpers import _course_summary
from app.db.models import Course, CourseInstructor, Instructor
from app.db.session import get_db
from app.schemas.admin import (
    CourseCreateRequest,
    CourseInstructorCreateRequest,
    CourseInstructorRoleUpdate,
    CourseUpdateRequest,
)
from app.services.authz import (
    ROLE_HIERARCHY,
    assert_course_role,
    get_effective_course_role,
    require_instructor,
)

router = APIRouter(tags=["admin-courses"])


@router.get("/courses", summary="List courses accessible to the logged-in instructor")
async def list_courses(
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve all courses where the instructor is the creator or a staff member."""
    direct_courses_rows = await db.execute(
        select(Course)
        .where(Course.instructor_id == instructor.id)
        .options(
            selectinload(Course.roster_entries),
            selectinload(Course.assignments),
        )
    )
    direct_courses = list(direct_courses_rows.scalars().all())

    staff_courses_rows = await db.execute(
        select(Course)
        .join(CourseInstructor, CourseInstructor.course_id == Course.id)
        .where(CourseInstructor.instructor_id == instructor.id)
        .options(
            selectinload(Course.roster_entries),
            selectinload(Course.assignments),
        )
    )
    staff_courses = list(staff_courses_rows.scalars().all())

    seen_ids: set[uuid.UUID] = set()
    courses_combined: list[Course] = []
    for c in direct_courses + staff_courses:
        if c.id not in seen_ids:
            seen_ids.add(c.id)
            courses_combined.append(c)

    courses_combined.sort(key=lambda c: (c.created_at, c.code), reverse=True)

    result: list[dict[str, Any]] = []
    for c in courses_combined:
        role = await get_effective_course_role(db, c.id, instructor) or "reader"
        active_count = sum(1 for r in c.roster_entries if r.status == "active")
        invited_count = sum(1 for r in c.roster_entries if r.status == "invited")
        assign_count = len(c.assignments)
        result.append(
            _course_summary(
                c,
                viewer_role=role,
                student_count=active_count,
                pending_invite_count=invited_count,
                assignment_count=assign_count,
            )
        )

    return result


@router.post("/courses", status_code=status.HTTP_201_CREATED, summary="Create a new course")
async def create_course(
    body: CourseCreateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a course section and assign the creator as course owner."""
    code = body.code.strip()
    term = body.term.strip()
    section = body.section.strip()

    # Check for duplicate course section
    existing_course = (
        await db.execute(
            select(Course).where(
                Course.instructor_id == instructor.id,
                Course.code == code,
                Course.term == term,
                Course.section == section,
            )
        )
    ).scalar_one_or_none()
    if existing_course is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Course section already exists",
        )

    course = Course(
        instructor_id=instructor.id,
        code=code,
        term=term,
        section=section,
        title=body.title.strip(),
    )
    db.add(course)
    await db.flush()

    # Automatically add creator as owner in course_instructors
    membership = CourseInstructor(
        course_id=course.id,
        instructor_id=instructor.id,
        role="owner",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(course)

    return _course_summary(
        course,
        viewer_role="owner",
        student_count=0,
        pending_invite_count=0,
        assignment_count=0,
    )


@router.get("/courses/{course_id}", summary="Get course metadata")
async def get_course(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve details and enrollment statistics for a specific course."""
    role = await assert_course_role(db, course_id, instructor, minimum="reader")
    course_row = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.roster_entries),
            selectinload(Course.assignments),
        )
    )
    course = course_row.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    active_count = sum(1 for r in course.roster_entries if r.status == "active")
    invited_count = sum(1 for r in course.roster_entries if r.status == "invited")
    assign_count = len(course.assignments)
    return _course_summary(
        course,
        viewer_role=role,
        student_count=active_count,
        pending_invite_count=invited_count,
        assignment_count=assign_count,
    )


@router.patch("/courses/{course_id}", summary="Update course settings")
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update title and archive status of a course."""
    role = await assert_course_role(db, course_id, instructor, minimum="instructor")
    course_row = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(
            selectinload(Course.roster_entries),
            selectinload(Course.assignments),
        )
    )
    course = course_row.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if body.title is not None:
        course.title = body.title.strip()
    if body.isArchived is not None:
        course.is_archived = body.isArchived

    db.add(course)
    await db.commit()
    await db.refresh(course)

    active_count = sum(1 for r in course.roster_entries if r.status == "active")
    invited_count = sum(1 for r in course.roster_entries if r.status == "invited")
    assign_count = len(course.assignments)
    return _course_summary(
        course,
        viewer_role=role,
        student_count=active_count,
        pending_invite_count=invited_count,
        assignment_count=assign_count,
    )


@router.get("/courses/{course_id}/staff", summary="List course teaching staff")
async def list_course_staff(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve all instructors, TAs, and readers assigned to a course."""
    await assert_course_role(db, course_id, instructor, minimum="reader")
    rows = (
        await db.execute(
            select(CourseInstructor)
            .where(CourseInstructor.course_id == course_id)
            .options(selectinload(CourseInstructor.instructor))
        )
    ).scalars().all()

    return [
        {
            "id": str(r.id),
            "instructorId": str(r.instructor_id),
            "email": r.instructor.email,
            "name": r.instructor.name,
            "role": r.role,
            "createdAt": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]


@router.post(
    "/courses/{course_id}/staff",
    status_code=status.HTTP_200_OK,
    summary="Add staff member",
)
async def add_course_staff(
    course_id: uuid.UUID,
    body: CourseInstructorCreateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Invite an instructor or TA to a course section."""
    await assert_course_role(db, course_id, instructor, minimum="instructor")

    target_user = (
        await db.execute(select(Instructor).where(Instructor.email == body.email))
    ).scalar_one_or_none()
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor with that email does not exist",
        )

    existing = (
        await db.execute(
            select(CourseInstructor).where(
                CourseInstructor.course_id == course_id,
                CourseInstructor.instructor_id == target_user.id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Instructor is already on the staff roster for this course",
        )

    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {list(ROLE_HIERARCHY)}",
        )

    membership = CourseInstructor(
        course_id=course_id,
        instructor_id=target_user.id,
        role=body.role,
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    return {
        "id": str(membership.id),
        "instructorId": str(target_user.id),
        "email": target_user.email,
        "name": target_user.name,
        "role": membership.role,
        "createdAt": membership.created_at.isoformat() if membership.created_at else "",
    }


@router.patch(
    "/courses/{course_id}/staff/{staff_instructor_id}",
    summary="Update staff member role",
)
async def update_course_staff_role(
    course_id: uuid.UUID,
    staff_instructor_id: uuid.UUID,
    body: CourseInstructorRoleUpdate,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update a staff member's permission role."""
    await assert_course_role(db, course_id, instructor, minimum="owner")

    membership = (
        await db.execute(
            select(CourseInstructor)
            .where(
                CourseInstructor.course_id == course_id,
                CourseInstructor.instructor_id == staff_instructor_id,
            )
            .options(selectinload(CourseInstructor.instructor))
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found in course",
        )

    if body.role not in ROLE_HIERARCHY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {list(ROLE_HIERARCHY)}",
        )

    membership.role = body.role
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    return {
        "id": str(membership.id),
        "instructorId": str(membership.instructor_id),
        "email": membership.instructor.email,
        "name": membership.instructor.name,
        "role": membership.role,
        "createdAt": membership.created_at.isoformat() if membership.created_at else "",
    }


@router.delete(
    "/courses/{course_id}/staff/{staff_instructor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove staff member",
)
async def remove_course_staff(
    course_id: uuid.UUID,
    staff_instructor_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an instructor or TA from the course staff."""
    await assert_course_role(db, course_id, instructor, minimum="owner")

    membership = (
        await db.execute(
            select(CourseInstructor).where(
                CourseInstructor.course_id == course_id,
                CourseInstructor.instructor_id == staff_instructor_id,
            )
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found")

    await db.delete(membership)
    await db.commit()

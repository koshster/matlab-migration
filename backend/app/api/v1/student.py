"""Student-facing routes for course invitations, enrolled courses, and assignments.

Handles invitation accept/decline flows, active course listings, and dashboard
assignment visibility gated by course enrollment and assignment targeting.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_student_id
from app.db.models import (
    Assignment,
    Course,
    CourseEnrollment,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import get_db

router = APIRouter(prefix="/student", tags=["student"])


# ---------------------------------------------------------------------------
# Helper Formatter
# ---------------------------------------------------------------------------


def _student_course_summary(
    course: Course, assignment_count: int, enrolled_at: datetime
) -> dict[str, Any]:
    return {
        "id": str(course.id),
        "code": course.code,
        "term": course.term,
        "section": course.section,
        "title": course.title,
        "instructorName": course.instructor.name if course.instructor else "",
        "assignmentCount": assignment_count,
        "enrolledAt": enrolled_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.get("/invitations", summary="List pending course invitations for student")
async def list_student_invitations(
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all pending course invitations awaiting student acceptance."""
    student_row = await db.execute(select(Student).where(Student.id == student_id))
    student = student_row.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")

    norm_pid = student.pid.strip().upper()
    invitation_entries = (
        await db.execute(
            select(RosterEntry)
            .where(
                (
                    (RosterEntry.student_id == student_id)
                    | (func.upper(RosterEntry.pid) == norm_pid)
                ),
                RosterEntry.status == "invited",
            )
            .options(
                selectinload(RosterEntry.course).selectinload(Course.instructor),
                selectinload(RosterEntry.course).selectinload(Course.assignments),
            )
            .order_by(RosterEntry.invited_at.desc())
        )
    ).scalars().all()

    invitations: list[dict[str, Any]] = []
    for entry in invitation_entries:
        course = entry.course
        pub_count = sum(1 for a in course.assignments if a.is_published or a.is_active)
        invitations.append(
            {
                "id": str(entry.id),
                "course": {
                    "id": str(course.id),
                    "code": course.code,
                    "term": course.term,
                    "title": course.title,
                },
                "instructorName": course.instructor.name if course.instructor else "",
                "invitedAt": entry.invited_at.isoformat(),
                "assignmentCount": pub_count,
            }
        )
    return invitations


@router.post("/invitations/{entry_id}/accept", summary="Accept course invitation")
async def accept_invitation(
    entry_id: uuid.UUID,
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Accept an invitation to join a course and reveal its assignments."""
    student_row = await db.execute(select(Student).where(Student.id == student_id))
    student = student_row.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")

    norm_pid = student.pid.strip().upper()
    entry_row = await db.execute(
        select(RosterEntry)
        .where(
            RosterEntry.id == entry_id,
            (
                (RosterEntry.student_id == student_id)
                | (func.upper(RosterEntry.pid) == norm_pid)
            ),
        )
        .options(
            selectinload(RosterEntry.course).selectinload(Course.instructor),
            selectinload(RosterEntry.course).selectinload(Course.assignments),
        )
    )
    entry = entry_row.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    now = datetime.now(UTC)
    entry.status = "active"
    entry.student_id = student_id
    entry.accepted_at = now
    db.add(entry)

    # Sync with CourseEnrollment for backward compatibility
    enrollment_row = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == entry.course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    enrollment = enrollment_row.scalar_one_or_none()
    if enrollment is None:
        enrollment = CourseEnrollment(
            course_id=entry.course_id,
            student_id=student_id,
            status="active",
            enrolled_at=now,
        )
        db.add(enrollment)
    else:
        enrollment.status = "active"
        db.add(enrollment)

    await db.commit()
    await db.refresh(entry)

    course = entry.course
    pub_count = sum(1 for a in course.assignments if a.is_published or a.is_active)
    return _student_course_summary(course, pub_count, entry.accepted_at or now)


@router.post("/invitations/{entry_id}/decline", summary="Decline course invitation")
async def decline_invitation(
    entry_id: uuid.UUID,
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Decline a pending course invitation."""
    student_row = await db.execute(select(Student).where(Student.id == student_id))
    student = student_row.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")

    norm_pid = student.pid.strip().upper()
    entry_row = await db.execute(
        select(RosterEntry).where(
            RosterEntry.id == entry_id,
            (
                (RosterEntry.student_id == student_id)
                | (func.upper(RosterEntry.pid) == norm_pid)
            ),
        )
    )
    entry = entry_row.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    entry.status = "declined"
    db.add(entry)
    await db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Enrolled Courses
# ---------------------------------------------------------------------------


@router.get("/courses", summary="List student's active enrolled courses")
async def list_student_courses(
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all courses where the student has an active roster entry."""
    active_entries = (
        await db.execute(
            select(RosterEntry)
            .where(
                RosterEntry.student_id == student_id,
                RosterEntry.status == "active",
            )
            .options(
                selectinload(RosterEntry.course).selectinload(Course.instructor),
                selectinload(RosterEntry.course).selectinload(Course.assignments),
            )
            .order_by(RosterEntry.accepted_at.desc())
        )
    ).scalars().all()

    result: list[dict[str, Any]] = []
    seen_courses: set[uuid.UUID] = set()
    for entry in active_entries:
        if entry.course_id in seen_courses:
            continue
        seen_courses.add(entry.course_id)
        course = entry.course
        pub_count = sum(1 for a in course.assignments if a.is_published or a.is_active)
        result.append(
            _student_course_summary(
                course, pub_count, entry.accepted_at or entry.invited_at
            )
        )
    return result


# ---------------------------------------------------------------------------
# Student Assignments Dashboard
# ---------------------------------------------------------------------------


@router.get("/assignments", summary="List assignments available to student")
async def list_student_assignments(
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return all active and published assignments for the student's enrolled courses."""
    # Find active roster entries for the student
    active_entries = (
        await db.execute(
            select(RosterEntry).where(
                RosterEntry.student_id == student_id,
                RosterEntry.status == "active",
            )
        )
    ).scalars().all()

    active_course_ids = [e.course_id for e in active_entries]
    active_entry_ids = {e.id for e in active_entries}

    if not active_course_ids:
        # Fallback to course_enrollments if any legacy enrollments exist
        legacy_enrollments = (
            await db.execute(
                select(CourseEnrollment).where(
                    CourseEnrollment.student_id == student_id,
                    CourseEnrollment.status == "active",
                )
            )
        ).scalars().all()
        active_course_ids = [e.course_id for e in legacy_enrollments]

    if not active_course_ids:
        # Check if student has direct student_assignments sessions
        sa_course_rows = (
            await db.execute(
                select(Assignment.course_id)
                .join(StudentAssignment, StudentAssignment.assignment_id == Assignment.id)
                .where(StudentAssignment.student_id == student_id)
            )
        ).scalars().all()
        active_course_ids = list(set(sa_course_rows))

    if not active_course_ids:
        return []

    # Query published assignments in active courses
    assignment_rows = (
        await db.execute(
            select(Assignment)
            .where(
                Assignment.course_id.in_(active_course_ids),
                (Assignment.is_published.is_(True) | Assignment.is_active.is_(True)),
            )
            .options(
                selectinload(Assignment.course),
                selectinload(Assignment.problems),
                selectinload(Assignment.targets),
            )
            .order_by(Assignment.created_at.desc())
        )
    ).scalars().all()

    # Preload student assignments and submissions
    student_assigns = (
        await db.execute(
            select(StudentAssignment)
            .where(StudentAssignment.student_id == student_id)
            .options(selectinload(StudentAssignment.submissions))
        )
    ).scalars().all()
    sa_by_assign_id = {sa.assignment_id: sa for sa in student_assigns}

    items: list[dict[str, Any]] = []
    for assignment in assignment_rows:
        # Check audience targeting
        if assignment.audience == "selected":
            target_roster_ids = {t.roster_entry_id for t in assignment.targets}
            if not target_roster_ids.intersection(active_entry_ids):
                continue

        sa = sa_by_assign_id.get(assignment.id)
        if sa:
            locked = bool(sa.submitted_at)
            subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
            for sub in sa.submissions:
                subs_by_problem.setdefault(sub.assignment_problem_id, []).append(sub)

            problems_status = [
                (
                    "correct"
                    if any(s.is_passed for s in subs_by_problem.get(ap.id, []))
                    else "incorrect"
                    if subs_by_problem.get(ap.id)
                    else "no_attempt"
                )
                for ap in assignment.problems
            ]

            if locked:
                earned = sum(1 for s in problems_status if s == "correct")
                assign_status = "submitted"
                score: dict[str, Any] | None = {"earned": earned, "total": len(assignment.problems)}
            elif any(s != "no_attempt" for s in problems_status):
                assign_status = "in_progress"
                score = None
            else:
                assign_status = "not_started"
                score = None
        else:
            assign_status = "not_started"
            score = None

        course = assignment.course
        items.append(
            {
                "slug": assignment.slug,
                "title": assignment.title,
                "status": assign_status,
                "score": score,
                "dueAt": assignment.due_at.isoformat() if assignment.due_at else None,
                "problemCount": len(assignment.problems),
                "course": {
                    "id": str(course.id),
                    "code": course.code,
                    "term": course.term,
                    "title": course.title,
                },
            }
        )

    return items

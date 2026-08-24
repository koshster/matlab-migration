"""Instructor-facing admin routes.

Handles course management, CSV roster batch import, staff role assignment,
problem-type catalogue, assignment builder, assignment publishing, and problem previewing.
"""

import uuid
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.problems  # noqa: F401 — triggers generator registration
from app.api.v1.assignments import _build_answer_schema, _build_truss_geometry
from app.core.identity import looks_like_email, normalize_email, normalize_pid
from app.db.models import (
    Assignment,
    AssignmentProblem,
    AssignmentTarget,
    Course,
    CourseInstructor,
    Instructor,
    RosterEntry,
    Student,
)
from app.db.session import get_db
from app.problems.registry import problem_registry
from app.services.authz import CourseRole, assert_course_role, require_instructor

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------


class CourseCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    term: str = Field(min_length=1, max_length=64)
    section: str = Field(default="001", max_length=32)
    title: str = Field(default="", max_length=255)


class CourseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    isArchived: bool | None = None


class RosterImportEntry(BaseModel):
    pid: str | None = None
    email: str | None = None
    firstName: str | None = None
    lastName: str | None = None


class RosterImportRequest(BaseModel):
    entries: list[RosterImportEntry] = Field(min_length=1, max_length=1000)


class RosterEntryUpdateRequest(BaseModel):
    status: str = Field(pattern="^(invited|active|declined|dropped)$")


class CourseStaffAddRequest(BaseModel):
    email: str
    role: CourseRole = "ta"


class AdminProblemSlotSpec(BaseModel):
    orderIndex: int = Field(ge=1)
    problemType: str
    params: dict[str, Any] = Field(default_factory=dict)
    points: float = Field(default=1.0, ge=0.0)


class AssignmentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=128)
    instructions: str = ""
    dueAt: str | None = None
    opensAt: str | None = None
    tolerance: float = 0.01
    feedbackMode: str = "per_field"
    maxAttempts: int | None = None
    audience: str = "all"
    targetEntryIds: list[uuid.UUID] = Field(default_factory=list)
    problems: list[AdminProblemSlotSpec] = Field(default_factory=list)


class AssignmentUpdateRequest(BaseModel):
    title: str | None = None
    slug: str | None = None
    instructions: str | None = None
    dueAt: str | None = None
    opensAt: str | None = None
    tolerance: float | None = None
    feedbackMode: str | None = None
    maxAttempts: int | None = None
    audience: str | None = None
    targetEntryIds: list[uuid.UUID] | None = None
    problems: list[AdminProblemSlotSpec] | None = None


class PublishRequest(BaseModel):
    isPublished: bool


# ---------------------------------------------------------------------------
# Helper Formatters
# ---------------------------------------------------------------------------


def _course_summary(
    course: Course,
    viewer_role: CourseRole,
    student_count: int = 0,
    pending_invite_count: int = 0,
    assignment_count: int = 0,
) -> dict[str, Any]:
    return {
        "id": str(course.id),
        "code": course.code,
        "term": course.term,
        "section": course.section,
        "title": course.title,
        "isArchived": course.is_archived,
        "studentCount": student_count,
        "pendingInviteCount": pending_invite_count,
        "assignmentCount": assignment_count,
        "viewerRole": viewer_role,
    }


def _roster_entry_out(entry: RosterEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "status": entry.status,
        "pid": entry.pid,
        "email": entry.email,
        "firstName": entry.first_name,
        "lastName": entry.last_name,
        "hasAccount": entry.student_id is not None,
        "invitedAt": entry.invited_at.isoformat(),
        "acceptedAt": entry.accepted_at.isoformat() if entry.accepted_at else None,
    }


def _admin_assignment_summary(assignment: Assignment, targeted_count: int) -> dict[str, Any]:
    return {
        "id": str(assignment.id),
        "courseId": str(assignment.course_id),
        "slug": assignment.slug,
        "title": assignment.title,
        "isPublished": assignment.is_published,
        "audience": assignment.audience,
        "problemCount": len(assignment.problems),
        "targetedStudentCount": targeted_count,
        "dueAt": assignment.due_at.isoformat() if assignment.due_at else None,
        "opensAt": assignment.opens_at.isoformat() if assignment.opens_at else None,
    }


def _admin_assignment_detail(assignment: Assignment, targeted_count: int) -> dict[str, Any]:
    summary = _admin_assignment_summary(assignment, targeted_count)
    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    slots = [
        {
            "orderIndex": p.order_index + 1,
            "problemType": p.problem_type,
            "params": p.params,
            "points": p.points,
        }
        for p in problems_sorted
    ]
    target_ids = [str(t.roster_entry_id) for t in assignment.targets]
    return {
        **summary,
        "instructions": assignment.instructions,
        "tolerance": assignment.tolerance,
        "feedbackMode": assignment.feedback_mode,
        "maxAttempts": assignment.max_attempts,
        "problems": slots,
        "targetEntryIds": target_ids,
    }


# ---------------------------------------------------------------------------
# Problem Types Catalogue
# ---------------------------------------------------------------------------


@router.get("/problem-types", summary="Problem types and their configurable params")
async def list_problem_types(
    _instructor: Instructor = Depends(require_instructor),
) -> list[dict[str, Any]]:
    """Return all registered problem domains and their configurable difficulty knobs."""
    return [
        {
            "problemType": generator.problem_type,
            "displayName": generator.display_name,
            "paramsSchema": [
                {
                    "name": field.name,
                    "label": field.label,
                    "valueType": field.value_type,
                    "default": field.default,
                    "minimum": field.minimum,
                    "maximum": field.maximum,
                    "step": field.step,
                    "helpText": field.help_text,
                }
                for field in generator.params_schema
            ],
        }
        for generator in problem_registry.all()
    ]


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------


@router.get("/courses", summary="List courses accessible by instructor")
async def list_courses(
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all courses where the instructor is owner or staff member."""
    # Find all courses where instructor is owner or listed in course_instructors
    staff_rows = (
        await db.execute(
            select(CourseInstructor).where(CourseInstructor.instructor_id == instructor.id)
        )
    ).scalars().all()
    staff_map = {s.course_id: cast(CourseRole, s.role) for s in staff_rows}

    course_rows = (
        await db.execute(
            select(Course)
            .where(
                (Course.instructor_id == instructor.id)
                | (Course.id.in_(list(staff_map.keys())))
            )
            .options(
                selectinload(Course.roster_entries),
                selectinload(Course.assignments),
            )
            .order_by(Course.created_at.desc())
        )
    ).scalars().all()

    result: list[dict[str, Any]] = []
    for course in course_rows:
        viewer_role: CourseRole = (
            "owner" if course.instructor_id == instructor.id else staff_map.get(course.id, "reader")
        )
        active_count = sum(1 for r in course.roster_entries if r.status == "active")
        invited_count = sum(1 for r in course.roster_entries if r.status == "invited")
        assign_count = len(course.assignments)
        result.append(
            _course_summary(
                course,
                viewer_role=viewer_role,
                student_count=active_count,
                pending_invite_count=invited_count,
                assignment_count=assign_count,
            )
        )
    return result


@router.post("/courses", status_code=status.HTTP_201_CREATED, summary="Create a new course section")
async def create_course(
    body: CourseCreateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new course and associate the creating instructor as owner."""
    code = body.code.strip()
    term = body.term.strip()
    section = body.section.strip() or "001"
    title = body.title.strip()

    existing_row = await db.execute(
        select(Course).where(
            Course.instructor_id == instructor.id,
            func.lower(Course.code) == code.lower(),
            func.lower(Course.term) == term.lower(),
            func.lower(Course.section) == section.lower(),
        )
    )
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A course with that code, term and section already exists",
        )

    course = Course(
        instructor_id=instructor.id,
        code=code,
        term=term,
        section=section,
        title=title,
    )
    db.add(course)
    await db.flush()

    staff_entry = CourseInstructor(
        course_id=course.id,
        instructor_id=instructor.id,
        role="owner",
    )
    db.add(staff_entry)
    await db.commit()
    await db.refresh(course)

    return _course_summary(course, viewer_role="owner")


@router.get("/courses/{course_id}", summary="Get course details")
async def get_course(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve course summary with active student, invited, and assignment counts."""
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


# ---------------------------------------------------------------------------
# Roster Management
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/roster", summary="List course roster entries")
async def list_roster(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve full roster of enrolled and invited students for a course."""
    await assert_course_role(db, course_id, instructor, minimum="reader")
    entries = (
        await db.execute(
            select(RosterEntry)
            .where(RosterEntry.course_id == course_id)
            .order_by(RosterEntry.invited_at.asc())
        )
    ).scalars().all()

    return [_roster_entry_out(e) for e in entries]


@router.post("/courses/{course_id}/roster", summary="Batch import roster entries")
async def add_roster_entries(
    course_id: uuid.UUID,
    body: RosterImportRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Import roster rows, auto-linking existing student accounts and skipping duplicates."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    # Load existing roster entries to detect collisions
    existing_entries = (
        await db.execute(select(RosterEntry).where(RosterEntry.course_id == course_id))
    ).scalars().all()

    existing_pids = {e.pid for e in existing_entries if e.pid}
    existing_emails = {e.email for e in existing_entries if e.email}

    # Preload all student accounts for lookup
    all_students = (await db.execute(select(Student))).scalars().all()
    students_by_pid = {s.pid.upper(): s for s in all_students}

    added_count = 0
    already_present_count = 0
    linked_count = 0
    invalid_count = 0
    row_results: list[dict[str, Any]] = []

    for row_idx, item in enumerate(body.entries, start=1):
        raw_pid = item.pid.strip() if item.pid else None
        raw_email = item.email.strip() if item.email else None
        first_name = item.firstName.strip() if item.firstName else None
        last_name = item.lastName.strip() if item.lastName else None

        pid = normalize_pid(raw_pid) if raw_pid else None
        email = normalize_email(raw_email) if raw_email else None

        # Validate entry
        if not pid and not email:
            invalid_count += 1
            row_results.append({
                "row": row_idx,
                "outcome": "invalid",
                "pid": pid,
                "email": email,
                "message": "At least one of PID or email must be provided",
            })
            continue

        if email and not looks_like_email(email):
            invalid_count += 1
            row_results.append({
                "row": row_idx,
                "outcome": "invalid",
                "pid": pid,
                "email": email,
                "message": "Malformed email address",
            })
            continue

        # Check duplicate
        if (pid and pid in existing_pids) or (email and email in existing_emails):
            already_present_count += 1
            row_results.append({
                "row": row_idx,
                "outcome": "already_present",
                "pid": pid,
                "email": email,
                "message": None,
            })
            continue

        # Check if student account already exists
        matched_student = students_by_pid.get(pid) if pid else None
        if matched_student:
            student_id = matched_student.id
            outcome = "linked_existing_account"
            linked_count += 1
        else:
            student_id = None
            outcome = "added"
            added_count += 1

        new_entry = RosterEntry(
            course_id=course_id,
            student_id=student_id,
            pid=pid,
            email=email,
            first_name=first_name,
            last_name=last_name,
            status="invited",
        )
        db.add(new_entry)

        if pid:
            existing_pids.add(pid)
        if email:
            existing_emails.add(email)

        row_results.append({
            "row": row_idx,
            "outcome": outcome,
            "pid": pid,
            "email": email,
            "message": None,
        })

    await db.commit()

    return {
        "added": added_count,
        "alreadyPresent": already_present_count,
        "linked": linked_count,
        "invalid": invalid_count,
        "results": row_results,
    }


@router.patch("/courses/{course_id}/roster/{entry_id}", summary="Update student roster status")
async def update_roster_entry(
    course_id: uuid.UUID,
    entry_id: uuid.UUID,
    body: RosterEntryUpdateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update status of a roster entry (e.g. active, dropped, declined, invited)."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    entry_row = await db.execute(
        select(RosterEntry).where(
            RosterEntry.id == entry_id,
            RosterEntry.course_id == course_id,
        )
    )
    entry = entry_row.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster entry not found")

    entry.status = body.status
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return _roster_entry_out(entry)


# ---------------------------------------------------------------------------
# Staff Management
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/staff", summary="List course teaching staff")
async def list_course_staff(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve all staff members associated with a course section."""
    await assert_course_role(db, course_id, instructor, minimum="reader")

    staff_rows = (
        await db.execute(
            select(CourseInstructor)
            .where(CourseInstructor.course_id == course_id)
            .options(selectinload(CourseInstructor.instructor))
        )
    ).scalars().all()

    return [
        {
            "id": str(s.id),
            "instructorId": str(s.instructor_id),
            "name": s.instructor.name,
            "email": s.instructor.email,
            "role": s.role,
        }
        for s in staff_rows
    ]


@router.post("/courses/{course_id}/staff", summary="Add or update teaching staff member")
async def add_course_staff(
    course_id: uuid.UUID,
    body: CourseStaffAddRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add or update an instructor or TA role on a course section (requires owner role)."""
    await assert_course_role(db, course_id, instructor, minimum="owner")

    target_email = normalize_email(body.email)
    target_row = await db.execute(
        select(Instructor).where(func.lower(Instructor.email) == target_email)
    )
    target_instructor = target_row.scalar_one_or_none()
    if target_instructor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No instructor account found with that email",
        )

    staff_row = await db.execute(
        select(CourseInstructor).where(
            CourseInstructor.course_id == course_id,
            CourseInstructor.instructor_id == target_instructor.id,
        )
    )
    staff = staff_row.scalar_one_or_none()
    if staff is None:
        staff = CourseInstructor(
            course_id=course_id,
            instructor_id=target_instructor.id,
            role=body.role,
        )
        db.add(staff)
    else:
        staff.role = body.role
        db.add(staff)

    await db.commit()
    await db.refresh(staff)

    return {
        "id": str(staff.id),
        "instructorId": str(target_instructor.id),
        "name": target_instructor.name,
        "email": target_instructor.email,
        "role": staff.role,
    }


# ---------------------------------------------------------------------------
# Assignment Builder & Management
# ---------------------------------------------------------------------------


@router.get("/courses/{course_id}/assignments", summary="List course assignments for instructor")
async def list_course_assignments(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all assignments configured for a course section."""
    await assert_course_role(db, course_id, instructor, minimum="reader")

    assignments = (
        await db.execute(
            select(Assignment)
            .where(Assignment.course_id == course_id)
            .options(
                selectinload(Assignment.problems),
                selectinload(Assignment.targets),
            )
            .order_by(Assignment.created_at.desc())
        )
    ).scalars().all()

    # Get active roster count for default "all" audience
    active_roster_count = len(
        (
            await db.execute(
                select(RosterEntry).where(
                    RosterEntry.course_id == course_id,
                    RosterEntry.status == "active",
                )
            )
        ).scalars().all()
    )

    result: list[dict[str, Any]] = []
    for a in assignments:
        targeted_count = active_roster_count if a.audience == "all" else len(a.targets)
        result.append(_admin_assignment_summary(a, targeted_count))
    return result


@router.post(
    "/courses/{course_id}/assignments",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assignment",
)
async def create_assignment(
    course_id: uuid.UUID,
    body: AssignmentCreateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new problem set with polymorphic problem slots and difficulty settings."""
    await assert_course_role(db, course_id, instructor, minimum="instructor")

    slug = body.slug.strip()
    existing_row = await db.execute(select(Assignment).where(Assignment.slug == slug))
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An assignment with that slug already exists",
        )

    due_at = datetime.fromisoformat(body.dueAt) if body.dueAt else None
    opens_at = datetime.fromisoformat(body.opensAt) if body.opensAt else None

    assignment = Assignment(
        course_id=course_id,
        slug=slug,
        title=body.title.strip(),
        instructions=body.instructions.strip(),
        due_at=due_at,
        opens_at=opens_at,
        tolerance=body.tolerance,
        feedback_mode=body.feedbackMode,
        max_attempts=body.maxAttempts,
        audience=body.audience,
        is_published=False,
        is_active=False,
    )
    db.add(assignment)
    await db.flush()

    for idx, slot_spec in enumerate(body.problems):
        prob = AssignmentProblem(
            assignment_id=assignment.id,
            order_index=slot_spec.orderIndex - 1 if slot_spec.orderIndex > 0 else idx,
            problem_type=slot_spec.problemType,
            params=slot_spec.params,
            points=slot_spec.points,
        )
        db.add(prob)

    if body.audience == "selected":
        for target_id in body.targetEntryIds:
            db.add(AssignmentTarget(assignment_id=assignment.id, roster_entry_id=target_id))

    await db.commit()

    # Re-fetch with loaded relations
    loaded_assignment = (
        await db.execute(
            select(Assignment)
            .where(Assignment.id == assignment.id)
            .options(
                selectinload(Assignment.problems),
                selectinload(Assignment.targets),
            )
        )
    ).scalar_one()

    targeted_count = (
        len(loaded_assignment.targets) if loaded_assignment.audience == "selected" else 0
    )
    return _admin_assignment_detail(loaded_assignment, targeted_count)


@router.get("/assignments/{assignment_id}", summary="Get assignment configuration details")
async def get_admin_assignment(
    assignment_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full configuration and problem slot settings for an assignment."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")

    targeted_count = (
        len(assignment.targets)
        if assignment.audience == "selected"
        else len(
            (
                await db.execute(
                    select(RosterEntry).where(
                        RosterEntry.course_id == assignment.course_id,
                        RosterEntry.status == "active",
                    )
                )
            ).scalars().all()
        )
    )
    return _admin_assignment_detail(assignment, targeted_count)


@router.patch("/assignments/{assignment_id}", summary="Update assignment settings or problem slots")
async def update_assignment(
    assignment_id: uuid.UUID,
    body: AssignmentUpdateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update metadata, problem slots, or target student list of an assignment."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="instructor")

    if body.title is not None:
        assignment.title = body.title.strip()
    if body.slug is not None:
        assignment.slug = body.slug.strip()
    if body.instructions is not None:
        assignment.instructions = body.instructions.strip()
    if body.dueAt is not None:
        assignment.due_at = datetime.fromisoformat(body.dueAt) if body.dueAt else None
    if body.opensAt is not None:
        assignment.opens_at = datetime.fromisoformat(body.opensAt) if body.opensAt else None
    if body.tolerance is not None:
        assignment.tolerance = body.tolerance
    if body.feedbackMode is not None:
        assignment.feedback_mode = body.feedbackMode
    if body.maxAttempts is not None:
        assignment.max_attempts = body.maxAttempts
    if body.audience is not None:
        assignment.audience = body.audience

    if body.problems is not None:
        # Replace existing problem slots
        assignment.problems.clear()
        for idx, slot_spec in enumerate(body.problems):
            assignment.problems.append(
                AssignmentProblem(
                    assignment_id=assignment.id,
                    order_index=slot_spec.orderIndex - 1 if slot_spec.orderIndex > 0 else idx,
                    problem_type=slot_spec.problemType,
                    params=slot_spec.params,
                    points=slot_spec.points,
                )
            )

    if body.targetEntryIds is not None and assignment.audience == "selected":
        assignment.targets.clear()
        for target_id in body.targetEntryIds:
            assignment.targets.append(
                AssignmentTarget(assignment_id=assignment.id, roster_entry_id=target_id)
            )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    targeted_count = len(assignment.targets) if assignment.audience == "selected" else 0
    return _admin_assignment_detail(assignment, targeted_count)


@router.post("/assignments/{assignment_id}/publish", summary="Toggle assignment published state")
async def publish_assignment(
    assignment_id: uuid.UUID,
    body: PublishRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publish or unpublish an assignment. Publishing requires at least one problem."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="instructor")

    if body.isPublished and len(assignment.problems) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish an assignment with no problems",
        )

    assignment.is_published = body.isPublished
    assignment.is_active = body.isPublished
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    targeted_count = len(assignment.targets) if assignment.audience == "selected" else 0
    return _admin_assignment_detail(assignment, targeted_count)


@router.get(
    "/assignments/{assignment_id}/preview/{index}",
    summary="Preview a problem slot with simulated seed",
)
async def preview_assignment_problem(
    assignment_id: uuid.UUID,
    index: int,
    seed: int = Query(default=1),
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate problem display payload without saving answers or leaking solutions."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(selectinload(Assignment.problems))
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")

    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    slot = index - 1
    if slot < 0 or slot >= len(problems_sorted):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem index out of range"
        )

    ap = problems_sorted[slot]
    generator = problem_registry.get(ap.problem_type)
    params = {"problem_id": index, **(ap.params or {})}
    display = generator.generate(seed=seed, params=params)

    if ap.problem_type == "truss":
        geometry = _build_truss_geometry(display.visual_schema)
        answer_schema = _build_answer_schema(geometry["members"])
    else:
        geometry = {"schemaVersion": 1, "elements": [e.model_dump() for e in display.visual_schema]}
        answer_schema = {
            "groups": [
                {
                    "id": "reactions",
                    "label": "Reactions",
                    "fields": [
                        {
                            "key": f.field_id,
                            "label": f.label,
                            "unit": f.unit,
                            "type": "number",
                            "decimals": 2,
                        }
                        for f in display.answer_schema
                    ],
                }
            ]
        }

    return {
        "schemaVersion": 1,
        "index": index,
        "problemType": ap.problem_type,
        "prompt": {
            "title": display.title,
            "body": display.instructions,
            "notes": [],
        },
        "geometry": geometry,
        "answerSchema": answer_schema,
        "savedAnswers": {},
        "attemptCount": 0,
        "maxAttempts": assignment.max_attempts,
        "locked": False,
    }

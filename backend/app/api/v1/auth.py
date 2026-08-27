"""Authentication route controller for student and instructor portals.

Handles password hashing, session cookie issuance, student-to-roster
auto-linking, and session validation.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identity import normalize_pid
from app.core.security import (
    clear_instructor_cookie,
    clear_student_cookie,
    hash_password,
    set_instructor_cookie,
    set_student_cookie,
    verify_password,
)
from app.db.models import Instructor, RosterEntry, Student
from app.db.session import get_db
from app.schemas.auth import (
    InstructorLoginRequest,
    InstructorRegisterRequest,
    StudentLoginRequest,
    StudentRegisterRequest,
)
from app.services.authz import require_instructor

router = APIRouter(prefix="/auth", tags=["auth"])


def _student_out(student: Student) -> dict[str, Any]:
    """Format student response dictionary."""
    return {
        "id": str(student.id),
        "firstName": student.first_name,
        "lastName": student.last_name,
    }


def _instructor_out(instructor: Instructor) -> dict[str, Any]:
    """Format instructor response dictionary."""
    return {
        "id": str(instructor.id),
        "name": instructor.name,
        "email": instructor.email,
    }


async def _link_roster_entries(db: AsyncSession, student: Student) -> None:
    """Auto-link unlinked roster entries matching the student's normalized PID."""
    norm_pid = normalize_pid(student.pid)
    unlinked_rows = (
        (
            await db.execute(
                select(RosterEntry).where(
                    func.upper(RosterEntry.pid) == norm_pid,
                    RosterEntry.student_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for entry in unlinked_rows:
        entry.student_id = student.id
        db.add(entry)


# ---------------------------------------------------------------------------
# Student Authentication Routes
# ---------------------------------------------------------------------------


@router.post(
    "/student/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register new student account",
)
async def register_student(
    body: StudentRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register a new student, automatically linking matching roster entries."""
    norm_pid = normalize_pid(body.pid)
    existing_row = await db.execute(select(Student).where(func.upper(Student.pid) == norm_pid))
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PID already registered")

    student = Student(
        pid=body.pid,
        first_name=body.firstName,
        last_name=body.lastName,
        password_hash=hash_password(body.password),
    )
    db.add(student)
    await db.flush()

    await _link_roster_entries(db, student)
    await db.commit()
    await db.refresh(student)

    set_student_cookie(response, student.id)
    return {"student": _student_out(student)}


@router.post("/student/login", summary="Student login")
async def login_student(
    body: StudentLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Authenticate student via PID and password, auto-linking any new course roster entries."""
    norm_pid = normalize_pid(body.pid)
    student_row = await db.execute(select(Student).where(func.upper(Student.pid) == norm_pid))
    student = student_row.scalar_one_or_none()

    if (
        student is None
        or student.password_hash is None
        or not verify_password(body.password, student.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    await _link_roster_entries(db, student)
    await db.commit()

    set_student_cookie(response, student.id)
    return {"student": _student_out(student)}


@router.post("/student/logout", summary="Student logout")
async def logout_student(response: Response) -> dict[str, bool]:
    """Clear student session cookie server-side."""
    clear_student_cookie(response)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Instructor Authentication Routes
# ---------------------------------------------------------------------------


@router.post(
    "/instructor/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register instructor account",
)
async def register_instructor(
    body: InstructorRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Register a new instructor or TA account."""
    email = body.email
    existing_row = await db.execute(select(Instructor).where(func.lower(Instructor.email) == email))
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    instructor = Instructor(
        email=email,
        name=body.name,
        password_hash=hash_password(body.password),
    )
    db.add(instructor)
    await db.commit()
    await db.refresh(instructor)

    set_instructor_cookie(response, instructor.id)
    return {"instructor": _instructor_out(instructor)}


@router.post("/instructor/login", summary="Instructor login")
async def login_instructor(
    body: InstructorLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Authenticate instructor or TA via email and password."""
    email = body.email
    row = await db.execute(select(Instructor).where(func.lower(Instructor.email) == email))
    instructor = row.scalar_one_or_none()

    if instructor is None or not verify_password(body.password, instructor.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    set_instructor_cookie(response, instructor.id)
    return {"instructor": _instructor_out(instructor)}


@router.post("/instructor/logout", summary="Instructor logout")
async def logout_instructor(response: Response) -> dict[str, bool]:
    """Clear instructor session cookie server-side."""
    clear_instructor_cookie(response)
    return {"ok": True}


@router.get("/instructor/me", summary="Read current instructor profile")
async def read_instructor_me(
    instructor: Instructor = Depends(require_instructor),
) -> dict[str, Any]:
    """Rehydrate active instructor session from httpOnly cookie."""
    return {"instructor": _instructor_out(instructor)}

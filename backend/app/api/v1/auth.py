from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# NOTE: PIDs are stored as typed for now. Normalizing them here would stop
# existing accounts (e.g. seeded "demo001") from logging in; that switch belongs
# with Phase B's `pid_normalized` column and its backfill.
from app.core.identity import looks_like_email, normalize_email
from app.core.security import (
    clear_instructor_cookie,
    clear_student_cookie,
    hash_password,
    set_instructor_cookie,
    set_student_cookie,
    verify_password,
)
from app.db.models import Instructor, Student
from app.db.session import get_db
from app.services.authz import require_instructor

router = APIRouter(prefix="/auth", tags=["auth"])

# Long enough to matter, short enough not to push students toward reuse.
_MIN_PASSWORD_LENGTH = 8


class StudentRegisterRequest(BaseModel):
    pid: str = Field(min_length=1, max_length=32)
    firstName: str = Field(min_length=1, max_length=128)
    lastName: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)


class StudentLoginRequest(BaseModel):
    pid: str
    password: str


class _EmailBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        if not looks_like_email(value):
            raise ValueError("not a valid email address")
        return normalize_email(value)


class InstructorRegisterRequest(_EmailBody):
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=_MIN_PASSWORD_LENGTH)


class InstructorLoginRequest(_EmailBody):
    password: str


def _student_out(student: Student) -> dict[str, Any]:
    return {
        "id": str(student.id),
        "firstName": student.first_name,
        "lastName": student.last_name,
    }


def _instructor_out(instructor: Instructor) -> dict[str, Any]:
    return {
        "id": str(instructor.id),
        "name": instructor.name,
        "email": instructor.email,
    }


@router.post("/student/register", status_code=status.HTTP_201_CREATED)
async def register_student(
    body: StudentRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    existing_row = await db.execute(select(Student).where(Student.pid == body.pid))
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PID already registered")

    student = Student(
        pid=body.pid,
        first_name=body.firstName,
        last_name=body.lastName,
        password_hash=hash_password(body.password),
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)

    set_student_cookie(response, student.id)
    return {"student": _student_out(student)}


@router.post("/student/login")
async def login_student(
    body: StudentLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    student_row = await db.execute(select(Student).where(Student.pid == body.pid))
    student = student_row.scalar_one_or_none()

    # Inlined rather than assigned to a flag so the None check narrows `student`
    # for everything below it.
    if (
        student is None
        or student.password_hash is None
        or not verify_password(body.password, student.password_hash)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    set_student_cookie(response, student.id)
    return {"student": _student_out(student)}


@router.post("/student/logout")
async def logout_student(response: Response) -> dict[str, bool]:
    """Clear the session server-side; the client cannot delete an httpOnly cookie."""
    clear_student_cookie(response)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Instructor auth
#
# Deliberately a separate cookie and a separate guard from the student routes:
# an instructor cookie must never satisfy a student route or vice versa
# (ADR 0009). Path is /auth/instructor/* to match the already-built admin UI;
# the ADR's original /auth/admin/* naming was never implemented.
# ---------------------------------------------------------------------------

@router.post("/instructor/register", status_code=status.HTTP_201_CREATED)
async def register_instructor(
    body: InstructorRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    email = body.email
    existing_row = await db.execute(
        select(Instructor).where(func.lower(Instructor.email) == email)
    )
    if existing_row.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

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


@router.post("/instructor/login")
async def login_instructor(
    body: InstructorLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    email = body.email
    row = await db.execute(select(Instructor).where(func.lower(Instructor.email) == email))
    instructor = row.scalar_one_or_none()

    if instructor is None or not verify_password(body.password, instructor.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    set_instructor_cookie(response, instructor.id)
    return {"instructor": _instructor_out(instructor)}


@router.post("/instructor/logout")
async def logout_instructor(response: Response) -> dict[str, bool]:
    clear_instructor_cookie(response)
    return {"ok": True}


@router.get("/instructor/me")
async def read_instructor_me(
    instructor: Instructor = Depends(require_instructor),
) -> dict[str, Any]:
    """Lets the admin UI rehydrate from the httpOnly cookie instead of trusting
    its own sessionStorage copy, which can outlive the cookie."""
    return {"instructor": _instructor_out(instructor)}

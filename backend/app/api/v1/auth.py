import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_student_token, hash_password, verify_password
from app.db.models import Student
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class StudentRegisterRequest(BaseModel):
    pid: str
    firstName: str
    lastName: str
    password: str


class StudentLoginRequest(BaseModel):
    pid: str
    password: str


def _set_student_cookie(response: Response, student_id: uuid.UUID) -> None:
    response.set_cookie(
        key="student_session",
        value=create_student_token(student_id),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.jwt_expire_minutes * 60,
    )


def _student_out(student: Student) -> dict[str, Any]:
    return {
        "id": str(student.id),
        "firstName": student.first_name,
        "lastName": student.last_name,
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

    _set_student_cookie(response, student.id)
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

    _set_student_cookie(response, student.id)
    return {"student": _student_out(student)}

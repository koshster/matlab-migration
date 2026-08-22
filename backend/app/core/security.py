import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

_COOKIE_NAME = "student_session"


def create_student_token(student_id: uuid.UUID, student_assignment_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(student_id),
        "sa": str(student_assignment_id),
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_student_token(token: str) -> dict[str, str]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc


def get_current_student(
    student_session: str | None = Cookie(default=None, alias=_COOKIE_NAME),
) -> tuple[uuid.UUID, uuid.UUID]:
    if not student_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_student_token(student_session)
    return uuid.UUID(payload["sub"]), uuid.UUID(payload["sa"])

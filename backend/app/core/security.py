import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from fastapi import Cookie, HTTPException, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

TokenType = Literal["student", "instructor"]

STUDENT_COOKIE = "student_session"
INSTRUCTOR_COOKIE = "instructor_session"

# Single hashing context for the whole app. Previously auth.py and seed.py each
# built their own with different settings, which would silently diverge.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def create_token(subject_id: uuid.UUID, token_type: TokenType) -> str:
    """Mint a session token carrying an explicit audience.

    The `typ` claim is what actually separates students from instructors. With
    only `sub`/`exp`, the two were distinguishable by cookie name alone — so a
    student token replayed in an `instructor_session` cookie would have been
    accepted by admin routes (ADR 0009 forbids exactly this).
    """
    payload: dict[str, Any] = {
        "sub": str(subject_id),
        "typ": token_type,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return cast(str, jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm))


def create_student_token(student_id: uuid.UUID) -> str:
    return create_token(student_id, "student")


def create_instructor_token(instructor_id: uuid.UUID) -> str:
    return create_token(instructor_id, "instructor")


def _decode(token: str, expected_type: TokenType) -> uuid.UUID:
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm]),
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc

    # Tokens minted before `typ` existed are rejected rather than assumed to be
    # student tokens; the only cost is re-login.
    if payload.get("typ") != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    try:
        return uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc


# ---------------------------------------------------------------------------
# Cookies
# ---------------------------------------------------------------------------


def _set_session_cookie(response: Response, name: str, value: str) -> None:
    response.set_cookie(
        key=name,
        value=value,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def set_student_cookie(response: Response, student_id: uuid.UUID) -> None:
    _set_session_cookie(response, STUDENT_COOKIE, create_student_token(student_id))


def set_instructor_cookie(response: Response, instructor_id: uuid.UUID) -> None:
    _set_session_cookie(response, INSTRUCTOR_COOKIE, create_instructor_token(instructor_id))


def clear_student_cookie(response: Response) -> None:
    response.delete_cookie(STUDENT_COOKIE, path="/")


def clear_instructor_cookie(response: Response) -> None:
    response.delete_cookie(INSTRUCTOR_COOKIE, path="/")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def get_current_student_id(
    student_session: str | None = Cookie(default=None, alias=STUDENT_COOKIE),
) -> uuid.UUID:
    if not student_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode(student_session, "student")


def get_current_instructor_id(
    instructor_session: str | None = Cookie(default=None, alias=INSTRUCTOR_COOKIE),
) -> uuid.UUID:
    if not instructor_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode(instructor_session, "instructor")

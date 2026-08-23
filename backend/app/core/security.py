import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

from fastapi import Cookie, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_COOKIE_NAME = "student_session"

# Single hashing context for the whole app. Previously auth.py and seed.py each
# built their own with different settings, which would silently diverge.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_student_token(student_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(student_id),
        "exp": expire,
    }
    # python-jose ships no type stubs, so both calls return Any.
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return cast(str, token)


def decode_student_token(token: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        return cast(dict[str, str], payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc


def get_current_student_id(
    student_session: str | None = Cookie(default=None, alias=_COOKIE_NAME),
) -> uuid.UUID:
    if not student_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_student_token(student_session)
    return uuid.UUID(payload["sub"])

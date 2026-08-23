"""Student and instructor sessions must not be interchangeable.

Before the `typ` claim existed, a token carried only `sub`/`exp`, so the two
audiences were distinguishable by cookie name alone — replaying a student token
in an `instructor_session` cookie would have been accepted. ADR 0009 requires
that an instructor cookie never satisfy a student route and vice versa.
"""

import uuid

import pytest
from fastapi import HTTPException

from app.core.security import (
    INSTRUCTOR_COOKIE,
    STUDENT_COOKIE,
    create_instructor_token,
    create_student_token,
    create_token,
    get_current_instructor_id,
    get_current_student_id,
)


def test_student_token_is_rejected_by_the_instructor_guard() -> None:
    student_id = uuid.uuid4()
    token = create_student_token(student_id)

    # Same token, replayed in the other cookie.
    with pytest.raises(HTTPException) as exc:
        get_current_instructor_id(instructor_session=token)
    assert exc.value.status_code == 401


def test_instructor_token_is_rejected_by_the_student_guard() -> None:
    token = create_instructor_token(uuid.uuid4())

    with pytest.raises(HTTPException) as exc:
        get_current_student_id(student_session=token)
    assert exc.value.status_code == 401


def test_each_guard_accepts_its_own_audience() -> None:
    student_id = uuid.uuid4()
    instructor_id = uuid.uuid4()

    assert get_current_student_id(student_session=create_student_token(student_id)) == student_id
    assert (
        get_current_instructor_id(instructor_session=create_instructor_token(instructor_id))
        == instructor_id
    )


def test_missing_cookie_is_401() -> None:
    for guard in (get_current_student_id, get_current_instructor_id):
        for empty in (None, ""):
            with pytest.raises(HTTPException) as exc:
                guard(empty)  # type: ignore[operator]
            assert exc.value.status_code == 401


def test_garbage_token_is_401() -> None:
    with pytest.raises(HTTPException) as exc:
        get_current_student_id(student_session="not-a-jwt")
    assert exc.value.status_code == 401


def test_legacy_token_without_typ_is_rejected() -> None:
    """Tokens minted before the `typ` claim are refused rather than assumed to
    be student tokens; the only cost is re-login."""
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings

    legacy = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.now(UTC) + timedelta(minutes=60)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc:
        get_current_student_id(student_session=legacy)
    assert exc.value.status_code == 401


def test_expired_token_is_401() -> None:
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.core.config import settings

    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "typ": "student",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc:
        get_current_student_id(student_session=expired)
    assert exc.value.status_code == 401


def test_unknown_token_type_is_rejected() -> None:
    """A forged `typ` must not open either guard."""
    forged = create_token(uuid.uuid4(), "superuser")  # type: ignore[arg-type]
    for guard, kwarg in (
        (get_current_student_id, "student_session"),
        (get_current_instructor_id, "instructor_session"),
    ):
        with pytest.raises(HTTPException) as exc:
            guard(**{kwarg: forged})  # type: ignore[arg-type]
        assert exc.value.status_code == 401


def test_cookie_names_are_distinct() -> None:
    assert STUDENT_COOKIE != INSTRUCTOR_COOKIE

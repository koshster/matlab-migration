"""End-to-end instructor auth over HTTP, including cross-guard rejection."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import (
    INSTRUCTOR_COOKIE,
    STUDENT_COOKIE,
    create_student_token,
    hash_password,
)
from app.db.models import Instructor, Student
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_EMAIL = "marko@ucsd.edu"
INSTRUCTOR_PASSWORD = "statics2026!"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        session.add(
            Instructor(
                email=INSTRUCTOR_EMAIL,
                name="Prof. Marko",
                password_hash=hash_password(INSTRUCTOR_PASSWORD),
            )
        )
        session.add(
            Student(
                pid="A12345678",
                first_name="Ada",
                last_name="Lovelace",
                password_hash=hash_password("student-pw-1"),
            )
        )
        await session.commit()

        async def _override() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_db] = _override
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()

    await engine.dispose()


async def _login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": INSTRUCTOR_EMAIL, "password": INSTRUCTOR_PASSWORD},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_login_sets_an_httponly_instructor_cookie(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": INSTRUCTOR_EMAIL, "password": INSTRUCTOR_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["instructor"]["email"] == INSTRUCTOR_EMAIL
    # No password material in the response.
    assert "password" not in response.text.lower()

    cookie = response.headers.get("set-cookie", "")
    assert INSTRUCTOR_COOKIE in cookie
    assert "httponly" in cookie.lower()
    assert "samesite=lax" in cookie.lower()


@pytest.mark.asyncio
async def test_login_is_case_insensitive_on_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": "  MARKO@UCSD.EDU  ", "password": INSTRUCTOR_PASSWORD},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_wrong_password_is_401(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": INSTRUCTOR_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_unknown_email_is_401_not_404(client: AsyncClient) -> None:
    """Must not reveal whether an account exists."""
    response = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": "nobody@ucsd.edu", "password": INSTRUCTOR_PASSWORD},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_a_session(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/auth/instructor/me")).status_code == 401


@pytest.mark.asyncio
async def test_me_returns_the_signed_in_instructor(client: AsyncClient) -> None:
    await _login(client)
    response = await client.get("/api/v1/auth/instructor/me")
    assert response.status_code == 200
    assert response.json()["instructor"]["name"] == "Prof. Marko"


@pytest.mark.asyncio
async def test_logout_clears_the_session(client: AsyncClient) -> None:
    await _login(client)
    assert (await client.post("/api/v1/auth/instructor/logout")).status_code == 200
    assert (await client.get("/api/v1/auth/instructor/me")).status_code == 401


@pytest.mark.asyncio
async def test_student_cookie_cannot_reach_an_instructor_route(client: AsyncClient) -> None:
    """The core cross-guard property (ADR 0009)."""
    client.cookies.set(STUDENT_COOKIE, create_student_token(uuid.uuid4()))
    assert (await client.get("/api/v1/auth/instructor/me")).status_code == 401


@pytest.mark.asyncio
async def test_student_token_replayed_as_instructor_cookie_is_rejected(
    client: AsyncClient,
) -> None:
    client.cookies.set(INSTRUCTOR_COOKIE, create_student_token(uuid.uuid4()))
    assert (await client.get("/api/v1/auth/instructor/me")).status_code == 401


@pytest.mark.asyncio
async def test_instructor_cookie_cannot_reach_a_student_route(client: AsyncClient) -> None:
    await _login(client)
    # A real instructor session must not satisfy the student dashboard.
    assert (await client.get("/api/v1/student/assignments")).status_code == 401


@pytest.mark.asyncio
async def test_registration_rejects_duplicate_and_malformed_email(client: AsyncClient) -> None:
    duplicate = await client.post(
        "/api/v1/auth/instructor/register",
        json={"name": "Impostor", "email": INSTRUCTOR_EMAIL.upper(), "password": "another-pw-1"},
    )
    assert duplicate.status_code == 409

    malformed = await client.post(
        "/api/v1/auth/instructor/register",
        json={"name": "Nope", "email": "not-an-email", "password": "another-pw-1"},
    )
    assert malformed.status_code == 422


@pytest.mark.asyncio
async def test_registration_enforces_a_password_floor(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/register",
        json={"name": "Shorty", "email": "new@ucsd.edu", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_signs_the_new_instructor_in(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/instructor/register",
        json={"name": "New TA", "email": "New.TA@UCSD.edu", "password": "brand-new-pw-1"},
    )
    assert response.status_code == 201
    # Email is stored normalized so lookups and invites match reliably.
    assert response.json()["instructor"]["email"] == "new.ta@ucsd.edu"
    assert (await client.get("/api/v1/auth/instructor/me")).status_code == 200

"""Comprehensive tests for Authentication, Session Cookies, and Course Role Authorization Guards."""

import uuid
from collections.abc import AsyncIterator

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id
from app.db.models import Course, CourseInstructor, Instructor
from app.db.session import Base, get_db
from app.main import app
from app.services.authz import (
    _at_least,
    assert_course_role,
    get_effective_course_role,
    require_instructor,
)

INSTRUCTOR_ID = uuid.uuid4()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_student_auth_flows_and_cookie_management(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Register student
    reg_payload = {
        "pid": "A11223344",
        "firstName": "Ada",
        "lastName": "Lovelace",
        "password": "Password123!",
    }
    res_reg = await client.post("/api/v1/auth/student/register", json=reg_payload)
    assert res_reg.status_code == 201
    assert res_reg.json()["student"]["firstName"] == "Ada"
    assert "student_session" in res_reg.headers.get("set-cookie", "")

    # 2. Duplicate PID collision (409)
    res_dup = await client.post("/api/v1/auth/student/register", json=reg_payload)
    assert res_dup.status_code == 409

    # 3. Successful Login
    res_login = await client.post(
        "/api/v1/auth/student/login",
        json={"pid": "a11223344", "password": "Password123!"},  # case-insensitive PID
    )
    assert res_login.status_code == 200
    assert res_login.json()["student"]["lastName"] == "Lovelace"

    # 4. Failed Login (bad password & bad PID)
    res_bad_pw = await client.post(
        "/api/v1/auth/student/login",
        json={"pid": "A11223344", "password": "WrongPassword!"},
    )
    assert res_bad_pw.status_code == 401

    res_bad_pid = await client.post(
        "/api/v1/auth/student/login",
        json={"pid": "A99999999", "password": "Password123!"},
    )
    assert res_bad_pid.status_code == 401

    # 5. Logout
    res_logout = await client.post("/api/v1/auth/student/logout")
    assert res_logout.status_code == 200
    assert res_logout.json()["ok"] is True


@pytest.mark.asyncio
async def test_instructor_auth_flows_and_me(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Register instructor
    reg_payload = {
        "email": "prof.alan@ucsd.edu",
        "name": "Prof. Alan",
        "password": "SecurePassword123!",
    }
    res_reg = await client.post("/api/v1/auth/instructor/register", json=reg_payload)
    assert res_reg.status_code == 201
    inst_data = res_reg.json()["instructor"]
    assert inst_data["name"] == "Prof. Alan"
    inst_id = uuid.UUID(inst_data["id"])

    # 2. Duplicate email collision (409)
    res_dup = await client.post("/api/v1/auth/instructor/register", json=reg_payload)
    assert res_dup.status_code == 409

    # 3. Successful Login
    res_login = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": "PROF.ALAN@UCSD.EDU", "password": "SecurePassword123!"},
    )
    assert res_login.status_code == 200

    # 4. Failed Login
    res_bad = await client.post(
        "/api/v1/auth/instructor/login",
        json={"email": "prof.alan@ucsd.edu", "password": "WrongPassword!"},
    )
    assert res_bad.status_code == 401

    # 5. Instructor /me endpoint with dependency override
    app.dependency_overrides[get_current_instructor_id] = lambda: inst_id
    res_me = await client.get("/api/v1/auth/instructor/me")
    assert res_me.status_code == 200
    assert res_me.json()["instructor"]["email"] == "prof.alan@ucsd.edu"

    # 6. Logout
    res_logout = await client.post("/api/v1/auth/instructor/logout")
    assert res_logout.status_code == 200


@pytest.mark.asyncio
async def test_authz_role_hierarchy_and_course_guards(db_session: AsyncSession) -> None:
    # Hierarchy tests
    assert _at_least("owner", "reader") is True
    assert _at_least("ta", "instructor") is False
    assert _at_least("instructor", "ta") is True
    assert _at_least("reader", "reader") is True

    # Setup instructors
    owner = Instructor(email="owner@ucsd.edu", password_hash="x", name="Owner")
    ta = Instructor(email="ta@ucsd.edu", password_hash="x", name="TA")
    outsider = Instructor(email="out@ucsd.edu", password_hash="x", name="Outsider")
    db_session.add_all([owner, ta, outsider])
    await db_session.flush()

    # Setup course
    course = Course(instructor_id=owner.id, code="MAE 105", term="Fall 2026")
    db_session.add(course)
    await db_session.flush()

    staff = CourseInstructor(course_id=course.id, instructor_id=ta.id, role="ta")
    db_session.add(staff)
    await db_session.commit()

    # 1. Effective role checks
    assert await get_effective_course_role(db_session, course.id, owner) == "owner"
    assert await get_effective_course_role(db_session, course.id, ta) == "ta"
    assert await get_effective_course_role(db_session, course.id, outsider) is None

    # 2. assert_course_role successes
    assert await assert_course_role(db_session, course.id, owner, minimum="owner") == "owner"
    assert await assert_course_role(db_session, course.id, ta, minimum="ta") == "ta"
    assert await assert_course_role(db_session, course.id, ta, minimum="reader") == "ta"

    # 3. assert_course_role failures:
    # Outsider -> 404 (prevent course ID enumeration)
    with pytest.raises(HTTPException) as exc_404:
        await assert_course_role(db_session, course.id, outsider, minimum="reader")
    assert exc_404.value.status_code == 404

    # TA trying owner action -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_403:
        await assert_course_role(db_session, course.id, ta, minimum="owner")
    assert exc_403.value.status_code == 403

    # 4. require_instructor missing ID -> 401
    with pytest.raises(HTTPException) as exc_401:
        await require_instructor(instructor_id=uuid.uuid4(), db=db_session)
    assert exc_401.value.status_code == 401

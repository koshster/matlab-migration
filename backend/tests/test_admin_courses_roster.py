"""Tests for admin courses, roster management, staff, and security authorization."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id, get_current_student_id
from app.db.models import Course, CourseInstructor, Instructor, RosterEntry, Student
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()
OTHER_INSTRUCTOR_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(
            id=INSTRUCTOR_ID,
            email="marko@ucsd.edu",
            password_hash="hashed_pw",
            name="Prof. Marko",
        )
        other_instructor = Instructor(
            id=OTHER_INSTRUCTOR_ID,
            email="other@ucsd.edu",
            password_hash="hashed_pw",
            name="Prof. Other",
        )
        student = Student(
            id=STUDENT_ID,
            pid="A12345678",
            first_name="Ada",
            last_name="Lovelace",
        )
        session.add_all([instructor, other_instructor, student])
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def admin_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_instructor_id] = lambda: INSTRUCTOR_ID

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def student_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_student_id] = lambda: STUDENT_ID

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_and_list_courses(admin_client: AsyncClient) -> None:
    # 1. Create a course
    create_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026", "section": "001", "title": "Statics"},
    )
    assert create_resp.status_code == 201
    course_data = create_resp.json()
    assert course_data["code"] == "MAE-008"
    assert course_data["viewerRole"] == "owner"
    course_id = course_data["id"]

    # 2. Duplicate rejection
    dup_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026", "section": "001", "title": "Statics Duplicate"},
    )
    assert dup_resp.status_code == 409

    # 3. List courses
    list_resp = await admin_client.get("/api/v1/admin/courses")
    assert list_resp.status_code == 200
    courses = list_resp.json()
    assert len(courses) == 1
    assert courses[0]["id"] == course_id
    assert courses[0]["title"] == "Statics"


@pytest.mark.asyncio
async def test_roster_batch_import_and_outcomes(admin_client: AsyncClient) -> None:
    # Create course
    create_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-130", "term": "Fall 2026", "title": "Solids"},
    )
    course_id = create_resp.json()["id"]

    # Import roster:
    # 1: Ada Lovelace (existing student account PID A12345678 -> linked_existing_account)
    # 2: Charles Babbage (new student -> added)
    # 3: Missing PID and Email (invalid)
    # 4: Malformed Email (invalid)
    roster_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/roster",
        json={
            "entries": [
                {"pid": "a12345678", "firstName": "Ada", "lastName": "Lovelace"},
                {"pid": "A98765432", "email": "charles@ucsd.edu", "firstName": "Charles", "lastName": "Babbage"},
                {"firstName": "No", "lastName": "ID"},
                {"email": "not-an-email", "firstName": "Bad", "lastName": "Email"},
            ]
        },
    )
    assert roster_resp.status_code == 200
    data = roster_resp.json()
    assert data["added"] == 1
    assert data["linked"] == 1
    assert data["invalid"] == 2
    assert data["alreadyPresent"] == 0

    results = data["results"]
    assert results[0]["outcome"] == "linked_existing_account"
    assert results[1]["outcome"] == "added"
    assert results[2]["outcome"] == "invalid"
    assert results[3]["outcome"] == "invalid"

    # Re-importing Charles Babbage should now report already_present
    dup_import = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/roster",
        json={
            "entries": [
                {"pid": "A98765432", "email": "charles@ucsd.edu"},
            ]
        },
    )
    dup_data = dup_import.json()
    assert dup_data["alreadyPresent"] == 1
    assert dup_data["results"][0]["outcome"] == "already_present"


@pytest.mark.asyncio
async def test_update_roster_entry_status(admin_client: AsyncClient) -> None:
    create_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026"},
    )
    course_id = create_resp.json()["id"]

    await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/roster",
        json={"entries": [{"pid": "A11111111", "email": "s1@ucsd.edu"}]},
    )

    roster_list = (await admin_client.get(f"/api/v1/admin/courses/{course_id}/roster")).json()
    entry_id = roster_list[0]["id"]
    assert roster_list[0]["status"] == "invited"

    # Drop student
    patch_resp = await admin_client.patch(
        f"/api/v1/admin/courses/{course_id}/roster/{entry_id}",
        json={"status": "dropped"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "dropped"


@pytest.mark.asyncio
async def test_staff_management(admin_client: AsyncClient) -> None:
    create_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026"},
    )
    course_id = create_resp.json()["id"]

    # Add other instructor as TA
    staff_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/staff",
        json={"email": "other@ucsd.edu", "role": "ta"},
    )
    assert staff_resp.status_code == 200
    assert staff_resp.json()["role"] == "ta"

    # List staff
    list_resp = await admin_client.get(f"/api/v1/admin/courses/{course_id}/staff")
    assert list_resp.status_code == 200
    staff_list = list_resp.json()
    assert any(s["email"] == "other@ucsd.edu" and s["role"] == "ta" for s in staff_list)


@pytest.mark.asyncio
async def test_student_cannot_access_admin_endpoints(student_client: AsyncClient) -> None:
    # A student attempting to access any admin route must receive 401 Unauthorized
    resp1 = await student_client.get("/api/v1/admin/courses")
    assert resp1.status_code == 401

    resp2 = await student_client.post(
        "/api/v1/admin/courses",
        json={"code": "HACK-101", "term": "Fall 2026"},
    )
    assert resp2.status_code == 401

    resp3 = await student_client.get("/api/v1/admin/problem-types")
    assert resp3.status_code == 401

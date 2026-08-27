"""Comprehensive tests for Admin Courses, Teaching Staff, and Roster Import endpoints."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id
from app.db.models import Course, Instructor, Student
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()
TA_ID = uuid.uuid4()


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
            password_hash="hash1",
            name="Prof. Marko",
        )
        ta = Instructor(
            id=TA_ID,
            email="ta@ucsd.edu",
            password_hash="hash2",
            name="TA Alex",
        )
        session.add_all([instructor, ta])
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


@pytest.mark.asyncio
async def test_course_crud_and_staff_management(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Create course
    res_create = await admin_client.post(
        "/api/v1/admin/courses",
        json={
            "code": "MAE 170",
            "term": "Winter 2026",
            "section": "A00",
            "title": "Experimental Techniques",
        },
    )
    assert res_create.status_code == 201
    course_data = res_create.json()
    course_id = course_data["id"]
    assert course_data["code"] == "MAE 170"
    assert course_data["viewerRole"] == "owner"

    # 2. Duplicate course conflict (409)
    res_dup = await admin_client.post(
        "/api/v1/admin/courses",
        json={
            "code": "MAE 170",
            "term": "Winter 2026",
            "section": "A00",
            "title": "Experimental Techniques",
        },
    )
    assert res_dup.status_code == 409

    # 3. Get course details
    res_get = await admin_client.get(f"/api/v1/admin/courses/{course_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == course_id

    # 4. Update course title & archive
    res_patch = await admin_client.patch(
        f"/api/v1/admin/courses/{course_id}",
        json={"title": "Updated Title", "isArchived": True},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["title"] == "Updated Title"
    assert res_patch.json()["isArchived"] is True

    # 5. List courses
    res_list = await admin_client.get("/api/v1/admin/courses")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 6. Add staff member
    res_add_staff = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/staff",
        json={"email": "ta@ucsd.edu", "role": "ta"},
    )
    assert res_add_staff.status_code == 200
    staff_entry_id = res_add_staff.json()["id"]

    # 7. List staff
    res_staff = await admin_client.get(f"/api/v1/admin/courses/{course_id}/staff")
    assert res_staff.status_code == 200
    staff_list = res_staff.json()
    assert len(staff_list) == 2  # Owner + TA

    # 8. Update staff role
    res_update_staff = await admin_client.patch(
        f"/api/v1/admin/courses/{course_id}/staff/{TA_ID}",
        json={"role": "reader"},
    )
    assert res_update_staff.status_code == 200
    assert res_update_staff.json()["role"] == "reader"

    # 9. Delete staff member
    res_del_staff = await admin_client.delete(f"/api/v1/admin/courses/{course_id}/staff/{TA_ID}")
    assert res_del_staff.status_code == 204


@pytest.mark.asyncio
async def test_roster_import_and_crud(admin_client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Setup course and pre-existing student
    course = Course(instructor_id=INSTRUCTOR_ID, code="MAE 200", term="Spring 2026")
    db_session.add(course)
    await db_session.flush()

    student = Student(pid="A12345678", first_name="Existing", last_name="Student")
    db_session.add(student)
    await db_session.commit()

    # 2. Batch import roster
    import_payload = {
        "entries": [
            # Valid + links to existing student account
            {
                "pid": "A12345678",
                "email": "existing@ucsd.edu",
                "firstName": "Existing",
                "lastName": "Student",
            },
            # Valid new student
            {
                "pid": "A98765432",
                "email": "new.student@ucsd.edu",
                "firstName": "New",
                "lastName": "Student",
            },
            # Invalid email
            {"pid": "A11111111", "email": "not-an-email", "firstName": "Bad", "lastName": "Email"},
            # Missing PID & email
            {"pid": "", "email": "", "firstName": "No", "lastName": "Ident"},
        ]
    }
    res_import = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/roster",
        json=import_payload,
    )
    assert res_import.status_code == 200
    report = res_import.json()
    assert report["added"] == 1
    assert report["linked"] == 1
    assert report["invalid"] == 2

    # 3. List roster
    res_roster = await admin_client.get(f"/api/v1/admin/courses/{course.id}/roster")
    assert res_roster.status_code == 200
    roster_list = res_roster.json()
    assert len(roster_list) == 2

    entry_id = roster_list[0]["id"]

    # 4. Update roster entry status
    res_patch = await admin_client.patch(
        f"/api/v1/admin/courses/{course.id}/roster/{entry_id}",
        json={"status": "dropped"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "dropped"

    # 5. Delete roster entry
    res_del = await admin_client.delete(f"/api/v1/admin/courses/{course.id}/roster/{entry_id}")
    assert res_del.status_code == 204

    # Verify roster list count decreased
    res_roster_after = await admin_client.get(f"/api/v1/admin/courses/{course.id}/roster")
    assert len(res_roster_after.json()) == 1

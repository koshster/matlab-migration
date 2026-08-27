"""Comprehensive tests for Admin Assignment Builder and Preview endpoints."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id
from app.db.models import Course, CourseInstructor, Instructor, RosterEntry, Student
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()


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
            password_hash="hash",
            name="Prof. Marko",
        )
        session.add(instructor)
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
async def test_admin_assignment_crud_and_slugs(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Create a course
    course = Course(instructor_id=INSTRUCTOR_ID, code="MAE 101", term="Fall 2026")
    db_session.add(course)
    await db_session.flush()

    # Add course role for instructor
    role_obj = CourseInstructor(course_id=course.id, instructor_id=INSTRUCTOR_ID, role="instructor")
    db_session.add(role_obj)
    await db_session.commit()

    # 2. List course assignments (empty initially)
    list_resp = await admin_client.get(f"/api/v1/admin/courses/{course.id}/assignments")
    assert list_resp.status_code == 200
    assert list_resp.json() == []

    # 3. Create assignment with auto-generated slug
    create_payload = {
        "title": "Homework 1: Intro to Trusses",
        "instructions": "Solve all members",
        "tolerance": 0.02,
        "feedbackMode": "per_field",
        "maxAttempts": 3,
        "penaltyPerAttempt": 0.05,
        "scoringStrategy": "all_or_nothing",
        "allowLate": True,
        "latePenaltyRate": 0.1,
        "audience": "all",
        "problems": [
            {
                "orderIndex": 1,
                "problemType": "truss",
                "points": 1.0,
                "params": {"num_nodes": 3},
            },
            {
                "orderIndex": 2,
                "problemType": "beam",
                "points": 2.0,
                "params": {},
            },
        ],
    }
    create_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json=create_payload,
    )
    assert create_resp.status_code == 201
    assign_data = create_resp.json()
    assert assign_data["title"] == "Homework 1: Intro to Trusses"
    assert assign_data["slug"].startswith("homework-1-intro-to-trusses")
    assert len(assign_data["problems"]) == 2
    assignment_id = assign_data["id"]

    # 4. Slug collision test
    dup_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={**create_payload, "slug": assign_data["slug"]},
    )
    assert dup_resp.status_code == 409

    # 5. Get assignment detail
    get_resp = await admin_client.get(f"/api/v1/admin/assignments/{assignment_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == assignment_id

    # 6. Update assignment fields
    update_resp = await admin_client.patch(
        f"/api/v1/admin/assignments/{assignment_id}",
        json={
            "title": "HW 1 Updated",
            "tolerance": 0.05,
            "maxAttempts": 5,
            "allowLate": False,
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "rigid_body",
                    "points": 5.0,
                    "params": {},
                }
            ],
        },
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["title"] == "HW 1 Updated"
    assert updated_data["tolerance"] == 0.05
    assert updated_data["maxAttempts"] == 5
    assert updated_data["allowLate"] is False
    assert len(updated_data["problems"]) == 1
    assert updated_data["problems"][0]["problemType"] == "rigid_body"


@pytest.mark.asyncio
async def test_admin_assignment_targeting_and_publishing(
    admin_client: AsyncClient, db_session: AsyncSession
) -> None:
    course = Course(instructor_id=INSTRUCTOR_ID, code="MAE 102", term="Fall 2026")
    db_session.add(course)
    await db_session.flush()
    role_obj = CourseInstructor(course_id=course.id, instructor_id=INSTRUCTOR_ID, role="instructor")
    db_session.add(role_obj)

    student = Student(pid="A88888888", first_name="Ada", last_name="Lovelace")
    db_session.add(student)
    await db_session.flush()

    roster_entry = RosterEntry(
        course_id=course.id,
        student_id=student.id,
        email="ada@ucsd.edu",
        first_name="Ada",
        last_name="Lovelace",
        status="enrolled",
    )
    db_session.add(roster_entry)
    await db_session.commit()

    # Create assignment with selected targeting
    create_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={
            "title": "Targeted HW",
            "audience": "selected",
            "targetEntryIds": [str(roster_entry.id)],
            "problems": [],
        },
    )
    assert create_resp.status_code == 201
    assign_id = create_resp.json()["id"]

    # Invariant: cannot publish with 0 problems
    pub_fail = await admin_client.post(
        f"/api/v1/admin/assignments/{assign_id}/publish",
        json={"isPublished": True},
    )
    assert pub_fail.status_code == 400
    assert "0 problems" in pub_fail.json()["detail"]

    # Add a problem then publish
    await admin_client.patch(
        f"/api/v1/admin/assignments/{assign_id}",
        json={
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "truss",
                    "points": 1.0,
                    "params": {"num_nodes": 3},
                }
            ]
        },
    )

    pub_success = await admin_client.post(
        f"/api/v1/admin/assignments/{assign_id}/publish",
        json={"isPublished": True},
    )
    assert pub_success.status_code == 200
    assert pub_success.json()["isPublished"] is True

    # Unpublish
    unpub = await admin_client.patch(
        f"/api/v1/admin/assignments/{assign_id}/publish",
        json={"isPublished": False},
    )
    assert unpub.status_code == 200
    assert unpub.json()["isPublished"] is False


@pytest.mark.asyncio
async def test_admin_problem_preview(admin_client: AsyncClient, db_session: AsyncSession) -> None:
    course = Course(instructor_id=INSTRUCTOR_ID, code="MAE 103", term="Fall 2026")
    db_session.add(course)
    await db_session.flush()
    db_session.add(
        CourseInstructor(course_id=course.id, instructor_id=INSTRUCTOR_ID, role="instructor")
    )

    create_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course.id}/assignments",
        json={
            "title": "Preview Test Assignment",
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "truss",
                    "points": 1.0,
                    "params": {"num_nodes": 3},
                },
                {
                    "orderIndex": 2,
                    "problemType": "rigid_body",
                    "points": 1.0,
                    "params": {},
                },
            ],
        },
    )
    assert create_resp.status_code == 201
    assign_id = create_resp.json()["id"]

    # Preview Truss
    prev_truss = await admin_client.get(f"/api/v1/admin/assignments/{assign_id}/preview/1?seed=42")
    assert prev_truss.status_code == 200
    truss_data = prev_truss.json()
    assert truss_data["problemType"] == "truss"
    assert "geometry" in truss_data
    assert len(truss_data["geometry"]["members"]) > 0

    # Preview Rigid Body
    prev_rb = await admin_client.get(f"/api/v1/admin/assignments/{assign_id}/preview/2?seed=42")
    assert prev_rb.status_code == 200
    rb_data = prev_rb.json()
    assert rb_data["problemType"] == "rigid_body"
    assert "answerSchema" in rb_data

    # Out of bounds preview index
    prev_oob = await admin_client.get(f"/api/v1/admin/assignments/{assign_id}/preview/99")
    assert prev_oob.status_code == 404

    # Non-existent assignment preview
    prev_none = await admin_client.get(f"/api/v1/admin/assignments/{uuid.uuid4()}/preview/1")
    assert prev_none.status_code == 404

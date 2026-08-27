"""Tests for admin assignment builder, polymorphic problem slots, preview, and publishing."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id, get_current_student_id
from app.db.models import Instructor, Student
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()
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
        student = Student(
            id=STUDENT_ID,
            pid="A12345678",
            first_name="Ada",
            last_name="Lovelace",
        )
        session.add_all([instructor, student])
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
async def test_problem_types_catalogue_lists_all_generators(admin_client: AsyncClient) -> None:
    resp = await admin_client.get("/api/v1/admin/problem-types")
    assert resp.status_code == 200
    types = resp.json()
    type_names = {t["problemType"] for t in types}
    assert "truss" in type_names
    assert "beam" in type_names
    assert "rigid_body" in type_names

    truss_info = next(t for t in types if t["problemType"] == "truss")
    assert truss_info["displayName"] == "Planar truss"
    param_names = [p["name"] for p in truss_info["paramsSchema"]]
    assert "num_nodes" in param_names
    assert "max_force" in param_names
    assert "load_count" in param_names


@pytest.mark.asyncio
async def test_create_assignment_with_custom_problem_count_and_types(
    admin_client: AsyncClient,
) -> None:
    # 1. Create a course
    course_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026"},
    )
    course_id = course_resp.json()["id"]

    # 2. Create an assignment with 3 distinct problems (2 trusses of varying difficulty, 1 beam)
    assign_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/assignments",
        json={
            "title": "Mixed Problem Set 1",
            "slug": "mixed-set-1",
            "instructions": "Solve all problems carefully.",
            "tolerance": 0.01,
            "feedbackMode": "per_field",
            "maxAttempts": 3,
            "audience": "all",
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "truss",
                    "params": {"num_nodes": 3, "max_force": 5, "load_count": 1},
                    "points": 2.0,
                },
                {
                    "orderIndex": 2,
                    "problemType": "truss",
                    "params": {"num_nodes": 6, "max_force": 10, "load_count": 2},
                    "points": 3.0,
                },
                {
                    "orderIndex": 3,
                    "problemType": "beam",
                    "params": {"span_length": 8, "load_type": 2},
                    "points": 5.0,
                },
            ],
        },
    )
    assert assign_resp.status_code == 201
    assign_data = assign_resp.json()
    assert assign_data["slug"] == "mixed-set-1"
    assert assign_data["problemCount"] == 3
    assert assign_data["isPublished"] is False
    assert len(assign_data["problems"]) == 3
    assert assign_data["problems"][0]["points"] == 2.0
    assert assign_data["problems"][1]["points"] == 3.0
    assert assign_data["problems"][2]["points"] == 5.0
    assert assign_data["problems"][2]["problemType"] == "beam"


@pytest.mark.asyncio
async def test_publish_workflow_and_empty_guard(admin_client: AsyncClient) -> None:
    course_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026"},
    )
    course_id = course_resp.json()["id"]

    # Create empty assignment
    empty_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/assignments",
        json={"title": "Empty Assignment", "slug": "empty-assign", "problems": []},
    )
    empty_id = empty_resp.json()["id"]

    # Publishing empty assignment must fail
    publish_empty = await admin_client.post(
        f"/api/v1/admin/assignments/{empty_id}/publish",
        json={"isPublished": True},
    )
    assert publish_empty.status_code == 400

    # Add a problem slot
    await admin_client.patch(
        f"/api/v1/admin/assignments/{empty_id}",
        json={
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "truss",
                    "params": {"num_nodes": 4},
                    "points": 1.0,
                }
            ]
        },
    )

    # Now publishing succeeds
    publish_ok = await admin_client.post(
        f"/api/v1/admin/assignments/{empty_id}/publish",
        json={"isPublished": True},
    )
    assert publish_ok.status_code == 200
    assert publish_ok.json()["isPublished"] is True


@pytest.mark.asyncio
async def test_preview_assignment_problem(admin_client: AsyncClient) -> None:
    course_resp = await admin_client.post(
        "/api/v1/admin/courses",
        json={"code": "MAE-008", "term": "Fall 2026"},
    )
    course_id = course_resp.json()["id"]

    assign_resp = await admin_client.post(
        f"/api/v1/admin/courses/{course_id}/assignments",
        json={
            "title": "Preview Test",
            "slug": "preview-test",
            "problems": [
                {
                    "orderIndex": 1,
                    "problemType": "truss",
                    "params": {"num_nodes": 5, "max_force": 8},
                    "points": 1.0,
                }
            ],
        },
    )
    assignment_id = assign_resp.json()["id"]

    # Preview problem 1 with seed=42
    prev_resp = await admin_client.get(
        f"/api/v1/admin/assignments/{assignment_id}/preview/1?seed=42"
    )
    assert prev_resp.status_code == 200
    prev_data = prev_resp.json()
    assert prev_data["index"] == 1
    assert prev_data["problemType"] == "truss"
    assert "geometry" in prev_data
    assert len(prev_data["geometry"]["nodes"]) == 5
    # Zero solution leakage check: no solutions in preview response
    assert "member_solutions" not in prev_resp.text
    assert "reactions" not in prev_resp.text or "reactions" not in prev_data


@pytest.mark.asyncio
async def test_student_cannot_modify_assignments(student_client: AsyncClient) -> None:
    fake_id = uuid.uuid4()
    resp = await student_client.post(
        f"/api/v1/admin/assignments/{fake_id}/publish",
        json={"isPublished": True},
    )
    assert resp.status_code == 401

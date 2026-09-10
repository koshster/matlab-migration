"""Comprehensive tests for the student assignment flow:
- Assignment summary view
- Problem retrieval & draft saving
- Answer checking, scoring, feedback, max_attempts enforcement, and locking
- Assignment submission & results retrieval
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import _effective_seed, _generator_params, member_field_key
from app.core.security import get_current_student_id
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    Instructor,
    Student,
)
from app.db.session import Base, get_db
from app.main import app
from app.problems.registry import problem_registry

STUDENT_ID = uuid.uuid4()
SLUG = "flow-test-assignment"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(email="prof.test@ucsd.edu", password_hash="hash", name="Prof Test")
        session.add(instructor)
        await session.flush()

        course = Course(instructor_id=instructor.id, code="MAE-008", term="Fall 2026")
        session.add(course)
        await session.flush()

        assignment = Assignment(
            course_id=course.id,
            slug=SLUG,
            title="Truss HW Flow",
            tolerance=0.01,
            max_attempts=2,
        )
        session.add(assignment)
        await session.flush()

        for i in range(2):
            session.add(
                AssignmentProblem(
                    assignment_id=assignment.id,
                    problem_type="truss",
                    order_index=i,
                    params={"num_nodes": 3},
                )
            )

        student = Student(id=STUDENT_ID, pid="A11223344", first_name="Grace", last_name="Hopper")
        session.add(student)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_student_id] = lambda: STUDENT_ID

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_assignment_summary(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/assignments/{SLUG}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == SLUG
    assert data["title"] == "Truss HW Flow"
    assert data["problemCount"] == 2
    assert data["status"] == "not_started"
    assert data["locked"] is False
    assert len(data["problems"]) == 2
    assert data["problems"][0]["index"] == 1
    assert data["problems"][1]["index"] == 2


@pytest.mark.asyncio
async def test_get_problem_details_and_bounds(client: AsyncClient) -> None:
    # Valid 1-based index
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["index"] == 1
    assert data["problemType"] == "truss"
    assert "geometry" in data
    assert "answerSchema" in data
    assert data["attemptCount"] == 0
    assert data["maxAttempts"] == 2
    assert data["locked"] is False

    # Out of bounds indices
    resp_oob = await client.get(f"/api/v1/assignments/{SLUG}/problems/99")
    assert resp_oob.status_code == 404

    resp_zero = await client.get(f"/api/v1/assignments/{SLUG}/problems/0")
    assert resp_zero.status_code == 404


@pytest.mark.asyncio
async def test_save_draft_answers(client: AsyncClient) -> None:
    draft = {"S1": 15.5, "S2": -10.2}
    resp = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers",
        json={"answers": draft},
    )
    assert resp.status_code == 200
    assert "savedAt" in resp.json()

    # Re-fetch problem to verify draft answers are returned
    resp_get = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp_get.status_code == 200
    assert resp_get.json()["savedAnswers"] == draft


@pytest.mark.asyncio
async def test_check_answers_correct_and_incorrect(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. First attempt with incorrect answers
    resp_wrong = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": {"S1": 9999.0}},
    )
    assert resp_wrong.status_code == 200
    data_wrong = resp_wrong.json()
    assert data_wrong["correct"] is False
    assert data_wrong["attemptCount"] == 1
    assert data_wrong["problemStatus"] == "incorrect"

    # Verify assignment summary reflects in_progress status
    resp_summary = await client.get(f"/api/v1/assignments/{SLUG}")
    assert resp_summary.status_code == 200
    assert resp_summary.json()["status"] == "in_progress"

    # 2. Get ground truth solutions to submit a correct attempt
    from app.api.v1.assignments import _get_context, _resolve_slot

    _, sa, assignment = await _get_context(slug=SLUG, student_id=STUDENT_ID, db=db_session)
    slot, ap = _resolve_slot(assignment, 1)
    generator = problem_registry.get(ap.problem_type)
    seed = _effective_seed(sa, slot)
    params = _generator_params(ap, 1)

    display = generator.generate(seed=seed, params=params)
    from app.services.problem_display import build_truss_geometry

    geometry = build_truss_geometry(display.visual_schema)
    ground_truth = generator.solve(seed=seed, params=params)

    keys = list(ground_truth["member_solutions"].keys())
    members = geometry["members"]
    correct_answers = {
        member_field_key(m["id"]): ground_truth["member_solutions"][keys[i]]["signed_force"]
        for i, m in enumerate(members)
    }

    # 2nd attempt with correct answers (within max_attempts=2)
    resp_correct = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": correct_answers},
    )
    assert resp_correct.status_code == 200
    data_correct = resp_correct.json()
    assert data_correct["correct"] is True
    assert data_correct["attemptCount"] == 2
    assert data_correct["problemStatus"] == "correct"
    assert "All members correct" in data_correct["message"]


@pytest.mark.asyncio
async def test_check_answers_max_attempts_exceeded(client: AsyncClient) -> None:
    # Attempt 1 (wrong) -> OK
    res1 = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": {}},
    )
    assert res1.status_code == 200
    assert res1.json()["attemptCount"] == 1

    # Attempt 2 (wrong) -> OK (hit attempt limit 2)
    res2 = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": {}},
    )
    assert res2.status_code == 200
    assert res2.json()["attemptCount"] == 2
    assert "Check your signs" in res2.json()["message"]

    # Attempt 3 -> 403 Exceeded max attempts
    res3 = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": {}},
    )
    assert res3.status_code == 403
    assert "exceeded the maximum number of attempts" in res3.json()["detail"]


@pytest.mark.asyncio
async def test_submit_assignment_and_results(client: AsyncClient) -> None:
    # Query results before submitting -> 403
    res_before = await client.get(f"/api/v1/assignments/{SLUG}/result")
    assert res_before.status_code == 403
    assert "Not submitted yet" in res_before.json()["detail"]

    # Submit assignment
    res_submit = await client.post(f"/api/v1/assignments/{SLUG}/submit")
    assert res_submit.status_code == 200
    data_sub = res_submit.json()
    assert data_sub["submittedAt"] is not None
    assert "problems" in data_sub
    assert len(data_sub["problems"]) == 2
    assert data_sub["score"]["total"] == 2

    # Calling submit again should return the existing submission result
    res_resubmit = await client.post(f"/api/v1/assignments/{SLUG}/submit")
    assert res_resubmit.status_code == 200
    assert res_resubmit.json()["score"] == data_sub["score"]
    assert res_resubmit.json()["submittedAt"] is not None

    # Query results after submitting -> 200
    res_after = await client.get(f"/api/v1/assignments/{SLUG}/result")
    assert res_after.status_code == 200
    assert res_after.json()["score"] == data_sub["score"]
    assert res_after.json()["submittedAt"] is not None

    # Verify assignment summary reflects submitted status and score
    res_summary = await client.get(f"/api/v1/assignments/{SLUG}")
    assert res_summary.status_code == 200
    assert res_summary.json()["status"] == "submitted"
    assert res_summary.json()["locked"] is True
    assert res_summary.json()["score"] is not None

    # Attempting to check answer after submission -> 403 Assignment is locked
    res_locked = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check",
        json={"answers": {}},
    )
    assert res_locked.status_code == 403
    assert "Assignment is locked" in res_locked.json()["detail"]

    # Attempting to save draft after submission -> 403
    res_draft_locked = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers",
        json={"answers": {"S1": 10.0}},
    )
    assert res_draft_locked.status_code == 403

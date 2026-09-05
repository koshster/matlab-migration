"""The grader must reject a correct magnitude carried with the wrong sign.

Students enter one signed force per member: positive is tension, negative is
compression. Nothing else in the suite asserts that a compression member
answered as tension is marked wrong, even though that is the single most
common student error and the whole point of the sign convention.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import (
    _build_truss_geometry,
    _effective_seed,
    _generator_params,
    _get_context,
    _resolve_slot,
    member_field_key,
)
from app.core.security import get_current_student_id
from app.db.models import Assignment, AssignmentProblem, Course, Instructor, Student
from app.db.session import Base, get_db
from app.main import app
from app.problems.registry import problem_registry

STUDENT_ID = uuid.uuid4()
SLUG = "sign-convention-assignment"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(email="signs@ucsd.edu", password_hash="hash", name="Prof Signs")
        session.add(instructor)
        await session.flush()

        course = Course(instructor_id=instructor.id, code="MAE-008", term="Fall 2026")
        session.add(course)
        await session.flush()

        assignment = Assignment(course_id=course.id, slug=SLUG, title="Signs", tolerance=0.01)
        session.add(assignment)
        await session.flush()

        session.add(
            AssignmentProblem(
                assignment_id=assignment.id,
                problem_type="truss",
                order_index=0,
                params={"num_nodes": 4},
            )
        )
        session.add(Student(id=STUDENT_ID, pid="A99887766", first_name="Ada", last_name="Lovelace"))
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


async def _correct_answers(db_session: AsyncSession) -> dict[str, float]:
    _, sa, assignment = await _get_context(slug=SLUG, student_id=STUDENT_ID, db=db_session)
    slot, ap = _resolve_slot(assignment, 1)
    generator = problem_registry.get(ap.problem_type)
    seed = _effective_seed(sa, slot)
    params = _generator_params(ap, 1)
    geometry = _build_truss_geometry(generator.generate(seed=seed, params=params).visual_schema)
    truth = generator.solve(seed=seed, params=params)
    keys = list(truth["member_solutions"].keys())
    return {
        member_field_key(m["id"]): float(truth["member_solutions"][keys[i]]["signed_force"])
        for i, m in enumerate(geometry["members"])
    }


@pytest.mark.asyncio
async def test_correct_signed_answers_are_accepted(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    answers = await _correct_answers(db_session)
    resp = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers}
    )
    assert resp.status_code == 200
    assert resp.json()["correct"] is True


@pytest.mark.asyncio
async def test_negated_answers_are_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    """Right magnitude, wrong sign -> wrong. Every non-zero field must fail."""
    answers = await _correct_answers(db_session)
    negated = {key: -value for key, value in answers.items()}

    resp = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": negated}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["correct"] is False

    # A member carrying ~zero force is legitimately sign-agnostic; every other
    # member must be marked incorrect.
    for key, value in answers.items():
        if abs(value) > 0.05:
            assert body["perField"][key] is False, f"{key} accepted with a flipped sign"


@pytest.mark.asyncio
async def test_absolute_values_are_rejected(client: AsyncClient, db_session: AsyncSession) -> None:
    """Entering magnitudes only (a common shortcut) must not pass."""
    answers = await _correct_answers(db_session)
    if not any(value < -0.05 for value in answers.values()):
        pytest.skip("this generated truss has no compression member")

    magnitudes = {key: abs(value) for key, value in answers.items()}
    resp = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": magnitudes}
    )
    assert resp.status_code == 200
    assert resp.json()["correct"] is False

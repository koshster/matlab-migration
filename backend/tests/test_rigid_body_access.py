"""The generic (non-truss) problem path must obey the same gates as truss.

`rigid_body` is the first type served through the generator-declared schema
instead of the bespoke truss builders. That path is a second way into
`get_problem` and `check_answers`, so every guard the truss path has -- per
problem locking, deadline closure, and the reveal opt-in -- is asserted here
against a rigid_body assignment rather than assumed to carry over.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import _effective_seed, _generator_params, _get_context, _resolve_slot
from app.core.security import get_current_student_id
from app.db.models import Assignment, AssignmentProblem, Course, Instructor, Student
from app.db.session import Base, get_db
from app.main import app
from app.problems.registry import problem_registry

STUDENT_ID = uuid.uuid4()
SLUG = "rigid-body-assignment"

PAST = datetime(2020, 1, 1, tzinfo=UTC)
FUTURE = datetime(2099, 1, 1, tzinfo=UTC)


async def _seed(session: AsyncSession, **assignment_kw: object) -> None:
    instructor = Instructor(email="rb@ucsd.edu", password_hash="h", name="Prof RB")
    session.add(instructor)
    await session.flush()

    course = Course(instructor_id=instructor.id, code="MAE-008", term="Fall 2026")
    session.add(course)
    await session.flush()

    assignment = Assignment(
        course_id=course.id,
        slug=SLUG,
        title="Rigid Body",
        tolerance=0.01,
        **assignment_kw,
    )
    session.add(assignment)
    await session.flush()

    for i in range(2):
        session.add(
            AssignmentProblem(
                assignment_id=assignment.id,
                problem_type="rigid_body",
                order_index=i,
                params={},
            )
        )
    session.add(Student(id=STUDENT_ID, pid="A99998888", first_name="Rio", last_name="Marsh"))
    await session.commit()


def make_fixtures(**assignment_kw: object):  # noqa: ANN201 - pytest fixture factory
    @pytest.fixture
    async def _client() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            await _seed(session, **assignment_kw)

            async def _db() -> AsyncIterator[AsyncSession]:
                yield session

            app.dependency_overrides[get_db] = _db
            app.dependency_overrides[get_current_student_id] = lambda: STUDENT_ID
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                yield c, session
            app.dependency_overrides.clear()
        await engine.dispose()

    return _client


open_client = make_fixtures()
past_due_client = make_fixtures(due_at=PAST)
reveal_closed_client = make_fixtures(due_at=PAST, reveal_solutions_after_close=True)
reveal_open_client = make_fixtures(due_at=FUTURE, reveal_solutions_after_close=True)


async def correct_answers(db: AsyncSession, index: int) -> dict[str, float]:
    """Ground truth for a slot, keyed like the student's own answer fields."""
    _, sa, assignment = await _get_context(slug=SLUG, student_id=STUDENT_ID, db=db)
    slot, ap = _resolve_slot(assignment, index)
    generator = problem_registry.get(ap.problem_type)
    truth = generator.solve(seed=_effective_seed(sa, slot), params=_generator_params(ap, index))
    return {k: float(v) for k, v in truth["reactions"].items()}


# ---------------------------------------------------------------------------
# Generic schema shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rigid_body_is_gradeable_and_serves_a_generic_schema(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = open_client
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp.status_code == 200
    body = resp.json()

    assert body["problemType"] == "rigid_body"
    # Not the "displayable but unanswerable" shape the ungradeable types get.
    assert body["locked"] is False
    assert body["lockReason"] is None
    assert body["geometry"]["elements"]

    fields = [f for g in body["answerSchema"]["groups"] for f in g["fields"]]
    assert fields
    # `number` is the only value the contract's AnswerField enum allows; the
    # generators declare `numeric`, so the router must not pass it through.
    assert {f["type"] for f in fields} == {"number"}
    assert all(f["key"].startswith("reaction_") for f in fields)


# ---------------------------------------------------------------------------
# Per-problem locking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correct_rigid_body_problem_locks_without_revealing(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = open_client
    answers = await correct_answers(db, 1)

    resp = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers}
    )
    assert resp.status_code == 200
    assert resp.json()["correct"] is True
    assert "fields" in resp.json()["message"]

    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    assert problem["locked"] is True
    assert problem["lockReason"] == "correct"
    # Locked is not closed: still no solutions.
    assert problem["correctAnswers"] is None

    # A locked problem refuses further writes.
    again = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers}
    )
    assert again.status_code == 403


@pytest.mark.asyncio
async def test_empty_answers_are_never_vacuously_correct(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = open_client
    resp = await client.post(f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": {}})
    assert resp.status_code == 200
    assert resp.json()["correct"] is False


# ---------------------------------------------------------------------------
# Deadline closure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_closed_assignment_refuses_rigid_body_writes(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = past_due_client
    answers = await correct_answers(db, 1)

    check = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers}
    )
    assert check.status_code == 403

    save = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers", json={"answers": answers}
    )
    assert save.status_code == 403


# ---------------------------------------------------------------------------
# Reveal gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_solutions_while_open_even_when_opted_in(
    reveal_open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = reveal_open_client
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp.json()["correctAnswers"] is None


@pytest.mark.asyncio
async def test_closed_without_opt_in_reveals_nothing(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = past_due_client
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp.json()["correctAnswers"] is None


@pytest.mark.asyncio
async def test_solutions_revealed_only_when_closed_and_opted_in(
    reveal_closed_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = reveal_closed_client
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()

    revealed = problem["correctAnswers"]
    assert revealed is not None
    # Exactly the student's own fields -- nothing more, nothing fewer.
    assert set(revealed) == {
        f["key"] for g in problem["answerSchema"]["groups"] for f in g["fields"]
    }
    assert revealed == pytest.approx(await correct_answers(db, 1), abs=0.005)


@pytest.mark.asyncio
async def test_no_solver_internals_reach_the_wire(
    reveal_closed_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """solve() also returns `supports`; only the reaction values may escape."""
    client, _ = reveal_closed_client
    body = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).text
    for forbidden in ("fixed_pins", "member_solutions", "signed_force"):
        assert forbidden not in body, f"{forbidden} leaked to a student route"

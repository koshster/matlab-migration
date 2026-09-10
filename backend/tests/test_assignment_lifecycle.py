"""Per-problem locking, deadline closure, review access, and the reveal gate.

Covers the behaviour a student sees across an assignment's whole life: editing
while open, losing edit rights on a problem the moment it is correct, and
read-only review once the assignment closes -- by submit or by deadline.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import (
    _effective_seed,
    _generator_params,
    _get_context,
    _resolve_slot,
)
from app.core.security import get_current_student_id
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    Instructor,
    Student,
    StudentAssignment,
)
from app.db.session import Base, get_db
from app.main import app
from app.problems.registry import problem_registry
from app.services.problem_display import build_truss_geometry, member_field_key

STUDENT_ID = uuid.uuid4()
SLUG = "lifecycle-assignment"

PAST = datetime(2020, 1, 1, tzinfo=UTC)
FUTURE = datetime(2099, 1, 1, tzinfo=UTC)


def _make_session_factory() -> tuple[object, object]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def _seed(session: AsyncSession, **assignment_kw: object) -> None:
    instructor = Instructor(email="life@ucsd.edu", password_hash="h", name="Prof Life")
    session.add(instructor)
    await session.flush()

    course = Course(instructor_id=instructor.id, code="MAE-008", term="Fall 2026")
    session.add(course)
    await session.flush()

    assignment = Assignment(
        course_id=course.id,
        slug=SLUG,
        title="Lifecycle",
        tolerance=0.01,
        **assignment_kw,
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
    session.add(Student(id=STUDENT_ID, pid="A55554444", first_name="Kay", last_name="Chen"))
    await session.commit()


def make_fixtures(**assignment_kw: object):  # noqa: ANN201 - pytest fixture factory
    @pytest.fixture
    async def _client() -> AsyncIterator[tuple[AsyncClient, AsyncSession]]:
        engine, factory = _make_session_factory()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
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
late_ok_client = make_fixtures(due_at=PAST, hard_deadline_at=FUTURE, allow_late=True)
reveal_closed_client = make_fixtures(due_at=PAST, reveal_solutions_after_close=True)
reveal_open_client = make_fixtures(due_at=FUTURE, reveal_solutions_after_close=True)


async def correct_answers(db: AsyncSession, index: int) -> dict[str, float]:
    _, sa, assignment = await _get_context(slug=SLUG, student_id=STUDENT_ID, db=db)
    slot, ap = _resolve_slot(assignment, index)
    generator = problem_registry.get(ap.problem_type)
    seed = _effective_seed(sa, slot)
    params = _generator_params(ap, index)
    geometry = build_truss_geometry(generator.generate(seed=seed, params=params).visual_schema)
    truth = generator.solve(seed=seed, params=params)
    keys = list(truth["member_solutions"].keys())
    return {
        member_field_key(m["id"]): float(truth["member_solutions"][keys[i]]["signed_force"])
        for i, m in enumerate(geometry["members"])
    }


# ---------------------------------------------------------------------------
# Open assignment: a correct problem locks, its neighbours do not
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correct_problem_locks_and_keeps_the_passing_answers(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = open_client
    answers = await correct_answers(db, 1)

    resp = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers}
    )
    assert resp.status_code == 200
    assert resp.json()["correct"] is True

    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    assert problem["locked"] is True
    assert problem["lockReason"] == "correct"
    # The fields show the answer that actually earned the credit.
    assert problem["savedAnswers"] == pytest.approx(answers)
    # Solutions are not revealed just because the problem is locked.
    assert problem["correctAnswers"] is None


@pytest.mark.asyncio
async def test_a_correct_problem_rejects_further_writes(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = open_client
    answers = await correct_answers(db, 1)
    await client.post(f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers})

    recheck = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": {"S1": 1.0}}
    )
    assert recheck.status_code == 403
    assert "already correct" in recheck.json()["detail"]

    resave = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers", json={"answers": {"S1": 1.0}}
    )
    assert resave.status_code == 403


@pytest.mark.asyncio
async def test_other_problems_stay_editable(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """Locking is per problem, not per assignment."""
    client, db = open_client
    answers = await correct_answers(db, 1)
    await client.post(f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": answers})

    resp = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/2/answers", json={"answers": {"S1": 3.0}}
    )
    assert resp.status_code == 200

    summary = (await client.get(f"/api/v1/assignments/{SLUG}")).json()
    assert summary["locked"] is False
    assert summary["problems"][0]["locked"] is True
    assert summary["problems"][1]["locked"] is False


@pytest.mark.asyncio
async def test_checking_persists_the_draft(
    open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """A checked-but-unsaved answer must survive a reload."""
    client, _ = open_client
    await client.post(
        f"/api/v1/assignments/{SLUG}/problems/2/check", json={"answers": {"S1": 42.0}}
    )
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/2")).json()
    assert problem["savedAnswers"]["S1"] == 42.0


# ---------------------------------------------------------------------------
# Deadline closure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_past_due_assignment_is_closed_and_read_only(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = past_due_client
    summary = (await client.get(f"/api/v1/assignments/{SLUG}")).json()

    assert summary["status"] == "closed"
    assert summary["locked"] is True
    assert summary["lockReason"] == "past_due"
    assert summary["closesAt"] is not None
    assert summary["score"] is not None

    save = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers", json={"answers": {"S1": 1.0}}
    )
    assert save.status_code == 403
    assert save.json()["detail"] == "Assignment is locked"

    check = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/1/check", json={"answers": {"S1": 1.0}}
    )
    assert check.status_code == 403


@pytest.mark.asyncio
async def test_closed_assignment_is_still_viewable(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """Read-only does not mean inaccessible -- review must still work."""
    client, _ = past_due_client
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    assert problem["locked"] is True
    assert problem["lockReason"] == "past_due"
    assert problem["geometry"]["nodes"]
    assert problem["answerSchema"]["groups"]


@pytest.mark.asyncio
async def test_result_available_without_an_explicit_submit(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = past_due_client
    resp = await client.get(f"/api/v1/assignments/{SLUG}/result")
    assert resp.status_code == 200
    assert resp.json()["score"]["total"] == 2.0

    row = await db.execute(select(StudentAssignment).where(StudentAssignment.seed.isnot(None)))
    sa = row.scalars().first()
    assert sa is not None
    assert sa.final_score == 0.0
    assert sa.finalized_at is not None
    # The student never pressed Submit, and the record must not claim they did.
    assert sa.submitted_at is None


@pytest.mark.asyncio
async def test_finalization_is_idempotent(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, db = past_due_client
    await client.get(f"/api/v1/assignments/{SLUG}")
    row = await db.execute(select(StudentAssignment))
    first = row.scalars().one()
    stamp, score = first.finalized_at, first.final_score

    await client.get(f"/api/v1/assignments/{SLUG}")
    await client.get(f"/api/v1/assignments/{SLUG}/result")
    row2 = await db.execute(select(StudentAssignment))
    again = row2.scalars().one()
    assert again.finalized_at == stamp
    assert again.final_score == score


@pytest.mark.asyncio
async def test_late_work_stays_open_until_the_hard_deadline(
    late_ok_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """Past due but allow_late with a future hard deadline -> still writable."""
    client, _ = late_ok_client
    summary = (await client.get(f"/api/v1/assignments/{SLUG}")).json()
    assert summary["locked"] is False
    assert summary["status"] == "not_started"

    resp = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/1/answers", json={"answers": {"S1": 2.0}}
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Reveal gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_solutions_revealed_only_when_closed_and_opted_in(
    reveal_closed_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = reveal_closed_client
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    assert problem["correctAnswers"] is not None
    assert set(problem["correctAnswers"]) == {
        f["key"] for g in problem["answerSchema"]["groups"] for f in g["fields"]
    }


@pytest.mark.asyncio
async def test_no_solutions_while_open_even_when_opted_in(
    reveal_open_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = reveal_open_client
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/1")
    assert resp.json()["correctAnswers"] is None
    assert (await client.get(f"/api/v1/assignments/{SLUG}")).json()["revealSolutions"] is False


@pytest.mark.asyncio
async def test_no_solver_internals_reach_the_wire(
    reveal_closed_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """Even on the revealing path, only S-keyed numbers are emitted."""
    client, _ = reveal_closed_client
    body = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).text
    for forbidden in (
        "member_solutions",
        "signed_force",
        "magnitude",
        "reactions",
        "member_0_",
        "Tension",
        "Compression",
    ):
        assert forbidden not in body, f"{forbidden} leaked to a student route"


@pytest.mark.asyncio
async def test_closed_without_opt_in_reveals_nothing(
    past_due_client: tuple[AsyncClient, AsyncSession],
) -> None:
    client, _ = past_due_client
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    assert problem["correctAnswers"] is None


@pytest.mark.asyncio
async def test_revealed_answers_are_rounded_for_display(
    reveal_closed_client: tuple[AsyncClient, AsyncSession],
) -> None:
    """A zero-force member reads as 0.0, not 3.79e-18."""
    client, _ = reveal_closed_client
    problem = (await client.get(f"/api/v1/assignments/{SLUG}/problems/1")).json()
    for key, value in problem["correctAnswers"].items():
        assert value == round(value, 2), f"{key} was not rounded: {value}"
        # -0.0 renders as "-0.00" in an input box, which reads as a sign error.
        assert not (value == 0 and str(value).startswith("-")), f"{key} is negative zero"

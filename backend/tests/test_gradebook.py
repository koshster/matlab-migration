"""Instructor gradebook and analytics.

The roster is the denominator, so a student who never opened the assignment
still shows up as `not_started` -- that absence is the signal an instructor
actually wants. Scores are withheld until a student's work is final.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_instructor_id
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    CourseInstructor,
    Instructor,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import Base, get_db
from app.main import app

INSTRUCTOR_ID = uuid.uuid4()
PAST = "2020-01-01T00:00:00+00:00"


class Ctx:
    """Handles the tests need after setup."""

    def __init__(self) -> None:
        self.assignment_id: uuid.UUID
        self.engine: object


@pytest.fixture
async def ctx() -> AsyncIterator[tuple[AsyncClient, Ctx, AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    holder = Ctx()
    holder.engine = engine

    async with factory() as session:
        instructor = Instructor(
            id=INSTRUCTOR_ID, email="gb@ucsd.edu", password_hash="h", name="Prof. GB"
        )
        session.add(instructor)
        await session.flush()

        course = Course(instructor_id=INSTRUCTOR_ID, code="MAE-008", term="Fall 2026")
        session.add(course)
        await session.flush()
        session.add(
            CourseInstructor(course_id=course.id, instructor_id=INSTRUCTOR_ID, role="owner")
        )

        assignment = Assignment(course_id=course.id, slug="gb-hw", title="GB HW", tolerance=0.01)
        session.add(assignment)
        await session.flush()
        holder.assignment_id = assignment.id

        problems = []
        for i in range(2):
            ap = AssignmentProblem(
                assignment_id=assignment.id,
                problem_type="truss",
                order_index=i,
                params={"num_nodes": 3},
            )
            session.add(ap)
            problems.append(ap)
        await session.flush()

        # Ana: submitted, 1 of 2 correct (one wrong attempt on the second).
        ana = Student(pid="A00000001", first_name="Ana", last_name="Alvarez")
        session.add(ana)
        await session.flush()
        session.add(
            RosterEntry(
                course_id=course.id,
                student_id=ana.id,
                pid="A00000001",
                first_name="Ana",
                last_name="Alvarez",
                status="active",
            )
        )
        sa_ana = StudentAssignment(
            student_id=ana.id,
            assignment_id=assignment.id,
            seed=11,
            draft_answers={},
            submitted_at=__import__("datetime").datetime(
                2026, 1, 1, tzinfo=__import__("datetime").UTC
            ),
            finalized_at=__import__("datetime").datetime(
                2026, 1, 1, tzinfo=__import__("datetime").UTC
            ),
            final_score=1.0,
        )
        session.add(sa_ana)
        await session.flush()
        session.add(
            Submission(
                student_assignment_id=sa_ana.id,
                assignment_problem_id=problems[0].id,
                attempt_number=1,
                answers={},
                raw_score=1.0,
                net_score=1.0,
                is_passed=True,
                field_verdicts={},
            )
        )
        session.add(
            Submission(
                student_assignment_id=sa_ana.id,
                assignment_problem_id=problems[1].id,
                attempt_number=1,
                answers={},
                raw_score=0.0,
                net_score=0.0,
                is_passed=False,
                field_verdicts={},
            )
        )

        # Ben: started, nothing final yet.
        ben = Student(pid="A00000002", first_name="Ben", last_name="Boateng")
        session.add(ben)
        await session.flush()
        session.add(
            RosterEntry(
                course_id=course.id,
                student_id=ben.id,
                pid="A00000002",
                first_name="Ben",
                last_name="Boateng",
                status="active",
            )
        )
        sa_ben = StudentAssignment(
            student_id=ben.id, assignment_id=assignment.id, seed=12, draft_answers={}
        )
        session.add(sa_ben)
        await session.flush()
        session.add(
            Submission(
                student_assignment_id=sa_ben.id,
                assignment_problem_id=problems[0].id,
                attempt_number=1,
                answers={},
                raw_score=0.0,
                net_score=0.0,
                is_passed=False,
                field_verdicts={},
            )
        )

        # Cleo: on the roster, never opened the assignment.
        cleo = Student(pid="A00000003", first_name="Cleo", last_name="Costa")
        session.add(cleo)
        await session.flush()
        session.add(
            RosterEntry(
                course_id=course.id,
                student_id=cleo.id,
                pid="A00000003",
                first_name="Cleo",
                last_name="Costa",
                status="active",
            )
        )

        # Dropped students must not appear at all.
        session.add(
            RosterEntry(
                course_id=course.id,
                student_id=None,
                pid="A00000004",
                first_name="Dee",
                last_name="Dropped",
                status="dropped",
            )
        )
        await session.commit()

        async def _db() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_current_instructor_id] = lambda: INSTRUCTOR_ID
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c, holder, session
        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_gradebook_lists_every_active_roster_student(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    client, holder, _ = ctx
    resp = await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")
    assert resp.status_code == 200
    body = resp.json()

    names = [r["displayName"] for r in body["rows"]]
    assert names == ["Ana Alvarez", "Ben Boateng", "Cleo Costa"]
    assert "Dee Dropped" not in names
    assert body["totalPoints"] == 2.0


@pytest.mark.asyncio
async def test_gradebook_statuses_and_scores(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    client, holder, _ = ctx
    rows = (await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")).json()[
        "rows"
    ]
    by_name = {r["displayName"]: r for r in rows}

    ana = by_name["Ana Alvarez"]
    assert ana["status"] == "submitted"
    assert ana["earned"] == 1.0
    assert [c["status"] for c in ana["problems"]] == ["correct", "incorrect"]

    ben = by_name["Ben Boateng"]
    assert ben["status"] == "in_progress"
    # Not final yet: a partial score shown as a grade would misrepresent them.
    assert ben["earned"] is None
    assert ben["problems"][0]["attemptCount"] == 1

    cleo = by_name["Cleo Costa"]
    assert cleo["status"] == "not_started"
    assert cleo["submittedAt"] is None
    assert [c["status"] for c in cleo["problems"]] == ["no_attempt", "no_attempt"]


@pytest.mark.asyncio
async def test_gradebook_is_visible_while_the_assignment_is_open(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    """Live progress, not a post-mortem: no close check anywhere."""
    client, holder, _ = ctx
    resp = await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")
    assert resp.status_code == 200
    assert resp.json()["closesAt"] is None


@pytest.mark.asyncio
async def test_analytics_aggregates(ctx: tuple[AsyncClient, Ctx, AsyncSession]) -> None:
    client, holder, _ = ctx
    body = (await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/analytics")).json()

    assert body["studentCount"] == 3
    assert body["startedCount"] == 2
    assert body["submittedCount"] == 1
    assert body["closedCount"] == 1
    # Only Ana's work is final, so she alone enters the distribution.
    assert body["gradedCount"] == 1
    assert body["meanScore"] == 1.0
    assert body["medianScore"] == 1.0

    first, second = body["problems"]
    assert first["attemptedCount"] == 2
    assert first["correctCount"] == 1
    assert first["successRate"] == 0.5
    assert second["attemptedCount"] == 1
    assert second["correctCount"] == 0
    assert second["successRate"] == 0.0


@pytest.mark.asyncio
async def test_analytics_handles_an_untouched_assignment(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    """No attempts must not divide by zero."""
    client, holder, session = ctx
    course_row = await session.execute(
        __import__("sqlalchemy").select(Course).where(Course.code == "MAE-008")
    )
    course = course_row.scalars().one()
    fresh = Assignment(course_id=course.id, slug="empty-hw", title="Empty", tolerance=0.01)
    session.add(fresh)
    await session.flush()
    session.add(
        AssignmentProblem(
            assignment_id=fresh.id, problem_type="truss", order_index=0, params={"num_nodes": 3}
        )
    )
    await session.commit()

    body = (await client.get(f"/api/v1/admin/assignments/{fresh.id}/analytics")).json()
    assert body["gradedCount"] == 0
    assert body["meanScore"] is None
    assert body["problems"][0]["successRate"] is None
    assert body["problems"][0]["meanAttempts"] is None


@pytest.mark.asyncio
async def test_gradebook_query_count_does_not_grow_with_the_class(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    """Pins the N+1 guarantee.

    A shape assertion cannot catch N+1 and a magic threshold only encodes
    today's incidental query count. What matters is that adding students does
    not add queries, so this measures twice and compares.
    """
    client, holder, session = ctx
    engine = holder.engine
    seen: list[str] = []

    def _count(conn, cursor, statement, parameters, context, executemany):  # noqa: ANN001, ANN202
        if statement.lstrip().upper().startswith("SELECT"):
            seen.append(statement)

    async def measure() -> int:
        seen.clear()
        event.listen(engine.sync_engine, "before_cursor_execute", _count)
        try:
            resp = await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")
            assert resp.status_code == 200
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", _count)
        return len(seen)

    baseline = await measure()

    course_row = await session.execute(
        __import__("sqlalchemy").select(Course).where(Course.code == "MAE-008")
    )
    course = course_row.scalars().one()
    for n in range(20):
        extra = Student(pid=f"A9000{n:04d}", first_name=f"Extra{n}", last_name="Student")
        session.add(extra)
        await session.flush()
        session.add(
            RosterEntry(
                course_id=course.id,
                student_id=extra.id,
                pid=extra.pid,
                first_name=extra.first_name,
                last_name=extra.last_name,
                status="active",
            )
        )
        sa = StudentAssignment(
            student_id=extra.id,
            assignment_id=holder.assignment_id,
            seed=100 + n,
            draft_answers={},
        )
        session.add(sa)
    await session.commit()

    grown = await measure()
    body = (await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")).json()
    assert len(body["rows"]) == 23
    assert grown == baseline, f"{baseline} queries for 3 students, {grown} for 23"


@pytest.mark.asyncio
async def test_unknown_assignment_is_404(ctx: tuple[AsyncClient, Ctx, AsyncSession]) -> None:
    client, _, _ = ctx
    resp = await client.get(f"/api/v1/admin/assignments/{uuid.uuid4()}/gradebook")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_cookie_cannot_reach_the_gradebook(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    """Grades are instructor-only; a student session must be refused."""
    client, holder, _ = ctx
    app.dependency_overrides.pop(get_current_instructor_id, None)

    for path in ("gradebook", "analytics"):
        resp = await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/{path}")
        assert resp.status_code in (401, 403), f"{path} returned {resp.status_code}"


@pytest.mark.asyncio
async def test_instructor_without_a_role_on_the_course_gets_404(
    ctx: tuple[AsyncClient, Ctx, AsyncSession],
) -> None:
    """404, not 403, so course ids cannot be enumerated."""
    client, holder, session = ctx
    stranger_id = uuid.uuid4()
    session.add(
        Instructor(id=stranger_id, email="stranger@ucsd.edu", password_hash="h", name="Stranger")
    )
    await session.commit()
    app.dependency_overrides[get_current_instructor_id] = lambda: stranger_id

    resp = await client.get(f"/api/v1/admin/assignments/{holder.assignment_id}/gradebook")
    assert resp.status_code == 404

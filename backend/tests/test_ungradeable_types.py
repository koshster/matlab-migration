"""Problem types with no server-side solver must refuse to grade, loudly.

`beam` and `rigid_body` are registered so the assignment builder can offer
them, but their solve() returns no solution. Before this guard existed, a beam
problem was served through the truss geometry builder and every answer graded
as wrong forever -- reproduced against the seeded `hw1` assignment, where
`check` returned `perField: {"S1": false}` for any input. The same expression
had a vacuous-truth sibling: with no fields at all, `all({})` is True and the
problem graded as fully correct.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import GRADEABLE_TYPES, is_gradeable
from app.core.security import get_current_student_id
from app.db.models import Assignment, AssignmentProblem, Course, Instructor, Student
from app.db.session import Base, get_db
from app.main import app

STUDENT_ID = uuid.uuid4()
SLUG = "mixed-types-assignment"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(email="mixed@ucsd.edu", password_hash="h", name="Prof Mixed")
        session.add(instructor)
        await session.flush()
        course = Course(instructor_id=instructor.id, code="MAE-008", term="Fall 2026")
        session.add(course)
        await session.flush()
        assignment = Assignment(course_id=course.id, slug=SLUG, title="Mixed", tolerance=0.01)
        session.add(assignment)
        await session.flush()

        # Slot 1 is gradeable, slot 2 is not, slot 3 is not even registered.
        for i, ptype in enumerate(("truss", "beam", "banana")):
            session.add(
                AssignmentProblem(
                    assignment_id=assignment.id,
                    problem_type=ptype,
                    order_index=i,
                    params={"num_nodes": 3},
                )
            )
        session.add(Student(id=STUDENT_ID, pid="A12121212", first_name="Sam", last_name="Diaz"))
        await session.commit()

        async def _db() -> AsyncIterator[AsyncSession]:
            yield session

        app.dependency_overrides[get_db] = _db
        app.dependency_overrides[get_current_student_id] = lambda: STUDENT_ID
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
        app.dependency_overrides.clear()
    await engine.dispose()


def test_only_truss_is_gradeable_today() -> None:
    assert frozenset({"truss"}) == GRADEABLE_TYPES
    assert is_gradeable("truss") is True
    assert is_gradeable("beam") is False
    assert is_gradeable("rigid_body") is False


@pytest.mark.asyncio
async def test_ungradeable_problem_is_viewable_but_unanswerable(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["problemType"] == "beam"
    assert body["locked"] is True
    assert body["lockReason"] == "unavailable"
    assert body["answerSchema"]["groups"] == []
    assert body["geometry"] is None


@pytest.mark.asyncio
async def test_ungradeable_problem_rejects_writes(client: AsyncClient) -> None:
    check = await client.post(
        f"/api/v1/assignments/{SLUG}/problems/2/check", json={"answers": {"S1": 1.0}}
    )
    assert check.status_code == 501
    assert "beam" in check.json()["detail"]

    save = await client.put(
        f"/api/v1/assignments/{SLUG}/problems/2/answers", json={"answers": {"S1": 1.0}}
    )
    assert save.status_code == 501


@pytest.mark.asyncio
async def test_ungradeable_answers_are_never_vacuously_correct(client: AsyncClient) -> None:
    """The old code path graded an empty field set as fully correct."""
    resp = await client.post(f"/api/v1/assignments/{SLUG}/problems/2/check", json={"answers": {}})
    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_unregistered_type_is_a_404_not_a_500(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/assignments/{SLUG}/problems/3")
    assert resp.status_code == 404
    assert "banana" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ungradeable_slots_leave_the_denominator_alone(client: AsyncClient) -> None:
    """One truss + one beam + one unknown must total 1 point, not 3.

    Counting an unimplemented slot would cost every student a point they had
    no way to earn.
    """
    await client.post(f"/api/v1/assignments/{SLUG}/submit")
    result = await client.get(f"/api/v1/assignments/{SLUG}/result")
    assert result.status_code == 200
    assert result.json()["score"]["total"] == 1.0

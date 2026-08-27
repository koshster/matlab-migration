"""Covers the first-open path: a student reaching an assignment with no
StudentAssignment row yet.

`_get_context` lazily creates that row and called `random.randint` in a module
that never imported `random`, so the very first time any student opened an
assignment they got a 500. It was masked because the seed script and the
now-deleted `/auth/student/session` route both pre-created the row — but
"register, then click an assignment" hits it directly.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assignments import _get_context, _resolve_slot
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    Instructor,
    Student,
)
from app.db.session import Base

SLUG = "truss-access-test"


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def _fixtures(session: AsyncSession) -> tuple[Student, Assignment]:
    instructor = Instructor(email="marko@ucsd.edu", password_hash="x", name="Prof. Marko")
    session.add(instructor)
    await session.flush()

    course = Course(instructor_id=instructor.id, code="MAE 008", term="Fall 2026")
    session.add(course)
    await session.flush()

    assignment = Assignment(course_id=course.id, slug=SLUG, title="Homework 1")
    session.add(assignment)
    await session.flush()

    for i, n in enumerate([3, 3, 4, 4, 5, 5, 6, 6]):
        session.add(
            AssignmentProblem(
                assignment_id=assignment.id,
                problem_type="truss",
                order_index=i,
                params={"num_nodes": n},
            )
        )
    student = Student(pid="A12345678", first_name="Ada", last_name="Lovelace")
    session.add(student)
    await session.flush()
    return student, assignment


@pytest.mark.asyncio
async def test_first_open_creates_the_work_record(db: AsyncSession) -> None:
    student, assignment = await _fixtures(db)

    # No StudentAssignment exists yet — this is the path that used to 500.
    got_student, sa, got_assignment = await _get_context(slug=SLUG, student_id=student.id, db=db)

    assert got_student.id == student.id
    assert got_assignment.id == assignment.id
    assert sa.student_id == student.id
    assert sa.assignment_id == assignment.id
    assert 1 <= sa.seed <= 10_000_000
    assert sa.submitted_at is None
    assert sa.draft_answers == {}


@pytest.mark.asyncio
async def test_reopening_reuses_the_same_seed(db: AsyncSession) -> None:
    """The seed must be immutable, or a student's problems would change under
    them between visits."""
    student, _ = await _fixtures(db)

    _, first, _ = await _get_context(slug=SLUG, student_id=student.id, db=db)
    first_seed = first.seed
    await db.flush()

    _, second, _ = await _get_context(slug=SLUG, student_id=student.id, db=db)

    assert second.id == first.id
    assert second.seed == first_seed


@pytest.mark.asyncio
async def test_unknown_slug_is_404(db: AsyncSession) -> None:
    student, _ = await _fixtures(db)
    with pytest.raises(Exception) as exc:
        await _get_context(slug="no-such-assignment", student_id=student.id, db=db)
    assert "404" in str(exc.value) or "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_unknown_student_is_401(db: AsyncSession) -> None:
    await _fixtures(db)
    with pytest.raises(Exception) as exc:
        await _get_context(slug=SLUG, student_id=uuid.uuid4(), db=db)
    assert "401" in str(exc.value) or "not found" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_slot_resolution_is_one_based(db: AsyncSession) -> None:
    _, assignment = await _fixtures(db)
    await db.refresh(assignment, ["problems"])

    slot, ap = _resolve_slot(assignment, 1)
    assert (slot, ap.order_index) == (0, 0)

    slot, ap = _resolve_slot(assignment, 8)
    assert (slot, ap.order_index) == (7, 7)

    for bad in (0, -1, 9, 99):
        with pytest.raises(Exception) as exc:
            _resolve_slot(assignment, bad)
        assert "404" in str(exc.value) or "out of range" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_unenrolled_student_can_access_unpublished_assignment_by_slug(
    db: AsyncSession,
) -> None:
    """Invariant: Direct assignment routes (/assignments/{slug}/...) do NOT enforce
    course enrollment or publication status. Any authenticated student with the slug
    can access and work on the assignment."""
    student, assignment = await _fixtures(db)
    assignment.is_published = False
    assignment.audience = "selected"  # targeted to nobody
    await db.flush()

    # Even though unpublished, audience=selected, and student has no enrollment/roster entry,
    # context resolution succeeds.
    got_student, sa, got_assignment = await _get_context(slug=SLUG, student_id=student.id, db=db)
    assert got_student.id == student.id
    assert got_assignment.id == assignment.id
    assert got_assignment.is_published is False
    assert sa.student_id == student.id

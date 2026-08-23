"""The student assignment list must carry its course.

Without it the dashboard cannot group work, so a student in two of Marko's
classes sees one undifferentiated list — and accepting a course invitation has
no visible effect.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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

STUDENT_ID = uuid.uuid4()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(email="marko@ucsd.edu", password_hash="x", name="Prof. Marko")
        session.add(instructor)
        await session.flush()

        student = Student(id=STUDENT_ID, pid="A12345678", first_name="Ada", last_name="Lovelace")
        session.add(student)

        # Two courses, so grouping is actually exercised.
        for code, slug, title in (
            ("MAE-008", "truss-fall-2026", "Truss Analysis"),
            ("MAE-130", "beam-hw1", "Beam Reactions"),
        ):
            course = Course(instructor_id=instructor.id, code=code, term="Fall 2026")
            session.add(course)
            await session.flush()

            assignment = Assignment(course_id=course.id, slug=slug, title=title)
            session.add(assignment)
            await session.flush()

            session.add(
                AssignmentProblem(
                    assignment_id=assignment.id,
                    problem_type="truss",
                    order_index=0,
                    params={"num_nodes": 3},
                )
            )
            session.add(
                StudentAssignment(
                    student_id=student.id, assignment_id=assignment.id, seed=42, draft_answers={}
                )
            )
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


@pytest.mark.asyncio
async def test_each_assignment_carries_its_course(client: AsyncClient) -> None:
    response = await client.get("/api/v1/student/assignments")
    assert response.status_code == 200

    items = response.json()
    assert len(items) == 2
    for item in items:
        course = item["course"]
        # Contract requires all four keys on StudentCourseRef.
        assert set(course) == {"id", "code", "term", "title"}
        assert course["term"] == "Fall 2026"
        uuid.UUID(course["id"])  # a real UUID, not a slug or a PID

    codes = {item["course"]["code"] for item in items}
    assert codes == {"MAE-008", "MAE-130"}


@pytest.mark.asyncio
async def test_assignments_from_different_courses_are_distinguishable(
    client: AsyncClient,
) -> None:
    items = (await client.get("/api/v1/student/assignments")).json()
    by_slug = {item["slug"]: item for item in items}

    assert by_slug["truss-fall-2026"]["course"]["code"] == "MAE-008"
    assert by_slug["beam-hw1"]["course"]["code"] == "MAE-130"
    assert (
        by_slug["truss-fall-2026"]["course"]["id"] != by_slug["beam-hw1"]["course"]["id"]
    )


@pytest.mark.asyncio
async def test_no_pid_or_solution_leaks_into_the_list(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/student/assignments")).text
    assert "A12345678" not in body  # standing rule #7
    assert "member_solutions" not in body  # standing rule #1
    assert "seed" not in body

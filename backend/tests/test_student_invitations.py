"""Tests for student invitations, accept/decline flows, and assignment visibility."""

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
    RosterEntry,
    Student,
)
from app.db.session import Base, get_db
from app.main import app

STUDENT_ID = uuid.uuid4()
STUDENT_PID = "A12345678"


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(
            email="marko@ucsd.edu",
            password_hash="pw",
            name="Prof. Marko",
        )
        session.add(instructor)
        await session.flush()

        course1 = Course(
            instructor_id=instructor.id,
            code="MAE-008",
            term="Fall 2026",
            section="001",
            title="Statics",
        )
        course2 = Course(
            instructor_id=instructor.id,
            code="MAE-130",
            term="Fall 2026",
            section="001",
            title="Solids",
        )
        session.add_all([course1, course2])
        await session.flush()

        # Assignment 1 in Course 1 (published, audience: all)
        a1 = Assignment(
            course_id=course1.id,
            slug="truss-hw1",
            title="Truss Homework 1",
            is_published=True,
            is_active=True,
            audience="all",
        )
        session.add(a1)
        await session.flush()

        session.add(
            AssignmentProblem(
                assignment_id=a1.id,
                problem_type="truss",
                order_index=0,
                params={"num_nodes": 3},
            )
        )

        # Assignment 2 in Course 1 (published, audience: selected)
        a2 = Assignment(
            course_id=course1.id,
            slug="truss-quiz",
            title="Truss Quiz (Targeted)",
            is_published=True,
            is_active=True,
            audience="selected",
        )
        session.add(a2)
        await session.flush()

        session.add(
            AssignmentProblem(
                assignment_id=a2.id,
                problem_type="truss",
                order_index=0,
                params={"num_nodes": 4},
            )
        )

        student = Student(
            id=STUDENT_ID,
            pid=STUDENT_PID,
            first_name="Ada",
            last_name="Lovelace",
            password_hash="pw",
        )
        session.add(student)
        await session.flush()

        # Pre-rostered in Course 1 (invited) and Course 2 (invited)
        r1 = RosterEntry(
            course_id=course1.id,
            student_id=student.id,
            pid=STUDENT_PID,
            status="invited",
        )
        r2 = RosterEntry(
            course_id=course2.id,
            student_id=student.id,
            pid=STUDENT_PID,
            status="invited",
        )
        session.add_all([r1, r2])
        await session.commit()
        yield session

    await engine.dispose()


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
async def test_invitation_list_and_accept_flow(student_client: AsyncClient) -> None:
    # 1. View invitations
    inv_resp = await student_client.get("/api/v1/student/invitations")
    assert inv_resp.status_code == 200
    invitations = inv_resp.json()
    assert len(invitations) == 2
    codes = {inv["course"]["code"] for inv in invitations}
    assert codes == {"MAE-008", "MAE-130"}

    # Initially student has no active courses or assignments
    courses_resp = await student_client.get("/api/v1/student/courses")
    assert courses_resp.status_code == 200
    assert courses_resp.json() == []

    assign_resp = await student_client.get("/api/v1/student/assignments")
    assert assign_resp.status_code == 200
    assert assign_resp.json() == []

    # 2. Accept MAE-008 invitation
    mae8_inv = next(inv for inv in invitations if inv["course"]["code"] == "MAE-008")
    accept_resp = await student_client.post(f"/api/v1/student/invitations/{mae8_inv['id']}/accept")
    assert accept_resp.status_code == 200
    assert accept_resp.json()["code"] == "MAE-008"

    # 3. Verify MAE-008 is now an active course
    active_courses = (await student_client.get("/api/v1/student/courses")).json()
    assert len(active_courses) == 1
    assert active_courses[0]["code"] == "MAE-008"

    # 4. Verify MAE-008 assignment (audience: all) is now visible
    assignments = (await student_client.get("/api/v1/student/assignments")).json()
    assert len(assignments) == 1
    assert assignments[0]["slug"] == "truss-hw1"
    # Targeted quiz is not yet visible because student wasn't in assignment_targets


@pytest.mark.asyncio
async def test_invitation_decline_flow(student_client: AsyncClient) -> None:
    invitations = (await student_client.get("/api/v1/student/invitations")).json()
    mae130_inv = next(inv for inv in invitations if inv["course"]["code"] == "MAE-130")

    decline_resp = await student_client.post(
        f"/api/v1/student/invitations/{mae130_inv['id']}/decline"
    )
    assert decline_resp.status_code == 200
    assert decline_resp.json()["ok"] is True

    # Remaining invitations should only have MAE-008
    remaining_invs = (await student_client.get("/api/v1/student/invitations")).json()
    assert len(remaining_invs) == 1
    assert remaining_invs[0]["course"]["code"] == "MAE-008"


@pytest.mark.asyncio
async def test_student_registration_auto_links_roster_entry(db_session: AsyncSession) -> None:
    # 1. Instructor pre-rosters a student with PID "B99999999" before account creation
    course = (await db_session.execute(Course.__table__.select())).first()
    assert course is not None
    course_id = course.id

    pre_roster = RosterEntry(
        course_id=course_id,
        student_id=None,
        pid="B99999999",
        email="newstudent@ucsd.edu",
        first_name="New",
        last_name="Student",
        status="invited",
    )
    db_session.add(pre_roster)
    await db_session.commit()

    # 2. Student registers with PID "b99999999" (lowercase)
    transport = ASGITransport(app=app)

    async def _db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _db
    async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
        reg_resp = await anon_client.post(
            "/api/v1/auth/student/register",
            json={
                "pid": "b99999999",
                "firstName": "New",
                "lastName": "Student",
                "password": "password123",
            },
        )
        assert reg_resp.status_code == 201
        student_id = uuid.UUID(reg_resp.json()["student"]["id"])

    app.dependency_overrides.clear()

    # 3. Check that the roster entry has been linked to the new student account
    await db_session.refresh(pre_roster)
    assert pre_roster.student_id == student_id

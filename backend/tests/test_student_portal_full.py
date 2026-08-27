"""Comprehensive tests for Student Portal: invitations, courses, and assignments dashboard."""

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import get_current_student_id
from app.db.models import (
    Assignment,
    AssignmentProblem,
    AssignmentTarget,
    Course,
    Instructor,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import Base, get_db
from app.main import app

STUDENT_ID = uuid.uuid4()
OTHER_STUDENT_ID = uuid.uuid4()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as session:
        instructor = Instructor(email="marko@ucsd.edu", password_hash="hash", name="Prof. Marko")
        student = Student(id=STUDENT_ID, pid="A12345678", first_name="Ada", last_name="Lovelace")
        other_student = Student(
            id=OTHER_STUDENT_ID, pid="A87654321", first_name="Charles", last_name="Babbage"
        )
        session.add_all([instructor, student, other_student])
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
async def test_invitation_lifecycle_and_courses(
    student_client: AsyncClient, db_session: AsyncSession
) -> None:
    instructor = await db_session.execute(
        Course.__table__.select().where(Course.instructor_id != None)  # noqa: E711
    )
    # 1. Create a course with 2 roster entries for student
    inst = (await db_session.execute(Instructor.__table__.select())).first()
    course1 = Course(instructor_id=inst.id, code="MAE 008", term="Fall 2026", title="Statics")
    course2 = Course(instructor_id=inst.id, code="MAE 130", term="Fall 2026", title="Dynamics")
    db_session.add_all([course1, course2])
    await db_session.flush()

    inv1 = RosterEntry(
        course_id=course1.id,
        student_id=STUDENT_ID,
        email="ada@ucsd.edu",
        first_name="Ada",
        last_name="Lovelace",
        status="invited",
    )
    inv2 = RosterEntry(
        course_id=course2.id,
        pid="A12345678",
        email="ada@ucsd.edu",
        first_name="Ada",
        last_name="Lovelace",
        status="invited",
    )
    db_session.add_all([inv1, inv2])
    await db_session.commit()

    # 2. List pending invitations
    res_inv = await student_client.get("/api/v1/student/invitations")
    assert res_inv.status_code == 200
    inv_list = res_inv.json()
    assert len(inv_list) == 2

    # 3. Accept first invitation
    res_accept = await student_client.post(f"/api/v1/student/invitations/{inv1.id}/accept")
    assert res_accept.status_code == 200
    assert res_accept.json()["code"] == "MAE 008"

    # 4. Decline second invitation
    res_decline = await student_client.post(f"/api/v1/student/invitations/{inv2.id}/decline")
    assert res_decline.status_code == 200
    assert res_decline.json()["ok"] is True

    # 5. List enrolled courses (should only contain course 1)
    res_courses = await student_client.get("/api/v1/student/courses")
    assert res_courses.status_code == 200
    enrolled = res_courses.json()
    assert len(enrolled) == 1
    assert enrolled[0]["code"] == "MAE 008"


@pytest.mark.asyncio
async def test_student_dashboard_assignment_targeting_and_statuses(
    student_client: AsyncClient, db_session: AsyncSession
) -> None:
    inst = (await db_session.execute(Instructor.__table__.select())).first()
    course = Course(instructor_id=inst.id, code="MAE 008", term="Fall 2026", title="Statics")
    db_session.add(course)
    await db_session.flush()

    # Active roster entry for student
    roster_entry = RosterEntry(
        course_id=course.id,
        student_id=STUDENT_ID,
        email="ada@ucsd.edu",
        status="active",
    )
    db_session.add(roster_entry)
    await db_session.flush()

    # Assignment 1: audience="all", not started
    assign_all = Assignment(
        course_id=course.id,
        slug="hw-all",
        title="HW for All",
        is_published=True,
        audience="all",
    )
    db_session.add(assign_all)
    await db_session.flush()

    prob1 = AssignmentProblem(
        assignment_id=assign_all.id,
        problem_type="truss",
        order_index=0,
        params={"num_nodes": 3},
    )
    db_session.add(prob1)

    # Assignment 2: audience="selected", targeted to this student's roster entry -> in_progress
    assign_targeted = Assignment(
        course_id=course.id,
        slug="hw-targeted",
        title="HW Targeted",
        is_published=True,
        audience="selected",
    )
    db_session.add(assign_targeted)
    await db_session.flush()

    target = AssignmentTarget(
        assignment_id=assign_targeted.id,
        roster_entry_id=roster_entry.id,
    )
    prob2 = AssignmentProblem(
        assignment_id=assign_targeted.id,
        problem_type="truss",
        order_index=0,
        params={"num_nodes": 3},
    )
    sa_targeted = StudentAssignment(
        student_id=STUDENT_ID,
        assignment_id=assign_targeted.id,
        seed=123,
    )
    db_session.add_all([target, prob2, sa_targeted])
    await db_session.flush()

    # Submitting an attempt to mark in_progress
    sub = Submission(
        student_assignment_id=sa_targeted.id,
        assignment_problem_id=prob2.id,
        attempt_number=1,
        is_passed=False,
        raw_score=0.0,
        net_score=0.0,
        answers={},
    )
    db_session.add(sub)

    # Assignment 3: audience="selected", targeted to another student -> should NOT show up
    other_roster = RosterEntry(
        course_id=course.id,
        student_id=OTHER_STUDENT_ID,
        email="charles@ucsd.edu",
        status="active",
    )
    db_session.add(other_roster)
    await db_session.flush()

    assign_excluded = Assignment(
        course_id=course.id,
        slug="hw-excluded",
        title="HW Excluded",
        is_published=True,
        audience="selected",
    )
    db_session.add(assign_excluded)
    await db_session.flush()

    target_other = AssignmentTarget(
        assignment_id=assign_excluded.id,
        roster_entry_id=other_roster.id,
    )
    db_session.add(target_other)
    await db_session.commit()

    # Query student assignments dashboard
    res_dash = await student_client.get("/api/v1/student/assignments")
    assert res_dash.status_code == 200
    items = res_dash.json()
    slugs = [it["slug"] for it in items]

    assert "hw-all" in slugs
    assert "hw-targeted" in slugs
    assert "hw-excluded" not in slugs  # Excluded by audience targeting

    hw_all_item = next(it for it in items if it["slug"] == "hw-all")
    assert hw_all_item["status"] == "not_started"

    hw_target_item = next(it for it in items if it["slug"] == "hw-targeted")
    assert hw_target_item["status"] == "in_progress"

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    CourseEnrollment,
    Instructor,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import Base


@pytest.fixture
async def async_test_session():
    """Provides an isolated in-memory SQLite async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_full_course_and_assignment_lifecycle(async_test_session: AsyncSession):
    session = async_test_session

    # 1. Create Instructor
    instructor = Instructor(
        email="marko@ucsd.edu",
        password_hash="argon2id_hash_placeholder",
        name="Prof. Marko",
    )
    session.add(instructor)
    await session.flush()

    # 2. Create Course
    course = Course(
        instructor_id=instructor.id,
        code="MAE 130A",
        term="Fall 2026",
    )
    session.add(course)
    await session.flush()

    # 3. Create Student & Enrollment
    student = Student(
        pid="A12345678",
        email="student@ucsd.edu",
        name="John Doe",
    )
    session.add(student)
    await session.flush()

    enrollment = CourseEnrollment(
        course_id=course.id,
        student_id=student.id,
        status="active",
    )
    session.add(enrollment)
    await session.flush()

    # 4. Create Assignment with dynamic N problems
    assignment = Assignment(
        course_id=course.id,
        title="Homework 1: Trusses",
        tolerance=0.01,
        scoring_strategy="pass_fail",
        allow_late=False,
    )
    session.add(assignment)
    await session.flush()

    # Add 2 problem slots
    prob1 = AssignmentProblem(
        assignment_id=assignment.id,
        problem_type="truss",
        order_index=1,
        params={"num_nodes": 3},
    )
    prob2 = AssignmentProblem(
        assignment_id=assignment.id,
        problem_type="truss",
        order_index=2,
        params={"num_nodes": 4},
    )
    session.add_all([prob1, prob2])
    await session.flush()

    # 5. Start Student Assignment Session with dedicated random seed
    student_assignment = StudentAssignment(
        student_id=student.id,
        assignment_id=assignment.id,
        seed=98765,
    )
    session.add(student_assignment)
    await session.flush()

    # 6. Record a Submission attempt
    submission = Submission(
        student_assignment_id=student_assignment.id,
        assignment_problem_id=prob1.id,
        attempt_number=1,
        answers={"member_0_1": 4.5, "member_0_1_state": "Tension"},
        raw_score=1.0,
        net_score=1.0,
        is_passed=True,
        field_verdicts={"member_0_1": True, "member_0_1_state": True},
    )
    session.add(submission)
    await session.flush()

    # Verify everything persisted and retrieved cleanly
    assert student.pid == "A12345678"
    assert enrollment.status == "active"
    assert student_assignment.seed == 98765
    assert submission.is_passed is True
    assert submission.raw_score == 1.0

"""Seed script: creates instructor, course, roster entries, assignments, and demo student."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    CourseEnrollment,
    CourseInstructor,
    Instructor,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import async_session_factory


async def seed() -> None:
    async with async_session_factory() as db:
        # ------------------------------------------------------------------
        # Instructor
        # ------------------------------------------------------------------
        instructor_row = await db.execute(
            select(Instructor).where(Instructor.email == "marko@university.edu")
        )
        instructor = instructor_row.scalar_one_or_none()
        if instructor is None:
            instructor = Instructor(
                email="marko@university.edu",
                password_hash=hash_password("statics2026"),
                name="Prof. Marko",
            )
            db.add(instructor)
            await db.flush()
            print("Created instructor marko@university.edu")
        else:
            print("Instructor already exists")

        # ------------------------------------------------------------------
        # Course
        # ------------------------------------------------------------------
        course_row = await db.execute(
            select(Course).where(Course.code == "ENGR301", Course.term == "Fall 2026")
        )
        course = course_row.scalar_one_or_none()
        if course is None:
            course = Course(
                instructor_id=instructor.id,
                code="ENGR301",
                term="Fall 2026",
                section="001",
                title="Statics & Structural Mechanics",
                is_archived=False,
            )
            db.add(course)
            await db.flush()

            staff_entry = CourseInstructor(
                course_id=course.id,
                instructor_id=instructor.id,
                role="owner",
            )
            db.add(staff_entry)
            await db.flush()
            print("Created course ENGR301 Fall 2026")
        else:
            print("Course already exists")

        # ------------------------------------------------------------------
        # Helper: find-or-create an assignment with 8 problems
        # ------------------------------------------------------------------
        async def get_or_create_assignment(
            slug: str,
            title: str,
            due_at: datetime | None = None,
        ) -> tuple[Assignment, list[AssignmentProblem]]:
            assignment_row = await db.execute(select(Assignment).where(Assignment.slug == slug))
            a = assignment_row.scalar_one_or_none()
            if a is None:
                a = Assignment(
                    course_id=course.id,
                    slug=slug,
                    title=title,
                    instructions="Determine the internal force in each truss member.",
                    tolerance=0.01,
                    feedback_mode="per_field",
                    max_attempts=None,
                    is_active=True,
                    is_published=True,
                    audience="all",
                    due_at=due_at,
                )
                db.add(a)
                await db.flush()
                node_counts = [3, 3, 4, 4, 5, 5, 6, 6]
                for i, n in enumerate(node_counts):
                    db.add(
                        AssignmentProblem(
                            assignment_id=a.id,
                            problem_type="truss",
                            order_index=i,
                            points=1.0,
                            params={"num_nodes": n, "max_force": 5, "load_count": 1},
                        )
                    )
                await db.flush()
                print(f"Created assignment {slug}")
            else:
                print(f"Assignment {slug} already exists")
                a.is_published = True
                if due_at is not None and a.due_at is None:
                    a.due_at = due_at
                db.add(a)
                await db.flush()

            problem_rows = await db.execute(
                select(AssignmentProblem)
                .where(AssignmentProblem.assignment_id == a.id)
                .order_by(AssignmentProblem.order_index)
            )
            problems = list(problem_rows.scalars().all())
            return a, problems

        a1, a1_probs = await get_or_create_assignment(
            "truss-fall-2026",
            "Truss Analysis — Fall 2026",
            due_at=datetime(2026, 12, 15, 23, 59, tzinfo=UTC),
        )
        a2, _ = await get_or_create_assignment(
            "truss-quiz-week8",
            "Truss Review Quiz — Week 8",
            due_at=datetime(2026, 10, 30, 23, 59, tzinfo=UTC),
        )
        a3, a3_probs = await get_or_create_assignment(
            "truss-practice-final",
            "Final Exam Practice",
        )

        # ------------------------------------------------------------------
        # Demo student
        # ------------------------------------------------------------------
        student_row = await db.execute(select(Student).where(Student.pid == "demo001"))
        student = student_row.scalar_one_or_none()
        if student is None:
            student = Student(
                pid="demo001",
                first_name="Demo",
                last_name="Student",
                password_hash=hash_password("demo1234"),
            )
            db.add(student)
            await db.flush()
            print("Created student demo001 / demo1234")
        else:
            print("Student demo001 already exists")

        # ------------------------------------------------------------------
        # Course Enrollment & Roster Entry for demo student
        # ------------------------------------------------------------------
        roster_row = await db.execute(
            select(RosterEntry).where(
                RosterEntry.course_id == course.id,
                RosterEntry.student_id == student.id,
            )
        )
        if roster_row.scalar_one_or_none() is None:
            roster_entry = RosterEntry(
                course_id=course.id,
                student_id=student.id,
                pid="DEMO001",
                email="demo@student.edu",
                first_name="Demo",
                last_name="Student",
                status="active",
                accepted_at=datetime.now(UTC),
            )
            db.add(roster_entry)
            await db.flush()

        enrollment_row = await db.execute(
            select(CourseEnrollment).where(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.student_id == student.id,
            )
        )
        if enrollment_row.scalar_one_or_none() is None:
            enrollment = CourseEnrollment(
                course_id=course.id,
                student_id=student.id,
                status="active",
            )
            db.add(enrollment)
            await db.flush()

        # ------------------------------------------------------------------
        # StudentAssignment 1: truss-fall-2026 -> in_progress
        # ------------------------------------------------------------------
        sa1_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a1.id,
            )
        )
        sa1 = sa1_row.scalar_one_or_none()
        if sa1 is None:
            sa1 = StudentAssignment(
                student_id=student.id,
                assignment_id=a1.id,
                seed=42,
                draft_answers={},
            )
            db.add(sa1)
            await db.flush()

            # Problem 0: passed
            db.add(
                Submission(
                    student_assignment_id=sa1.id,
                    assignment_problem_id=a1_probs[0].id,
                    attempt_number=1,
                    answers={"S1": 0.0, "S2": 0.0, "S3": 0.0},
                    raw_score=1.0,
                    net_score=1.0,
                    is_passed=True,
                    field_verdicts={"S1": True, "S2": True, "S3": True},
                )
            )
            # Problem 1: failed attempt
            db.add(
                Submission(
                    student_assignment_id=sa1.id,
                    assignment_problem_id=a1_probs[1].id,
                    attempt_number=1,
                    answers={"S1": 999.0},
                    raw_score=0.0,
                    net_score=0.0,
                    is_passed=False,
                    field_verdicts={"S1": False},
                )
            )
            # Problem 2: passed
            db.add(
                Submission(
                    student_assignment_id=sa1.id,
                    assignment_problem_id=a1_probs[2].id,
                    attempt_number=1,
                    answers={"S1": 0.0, "S2": 0.0, "S3": 0.0},
                    raw_score=1.0,
                    net_score=1.0,
                    is_passed=True,
                    field_verdicts={"S1": True, "S2": True, "S3": True},
                )
            )
            await db.flush()
            print("Seeded submissions for truss-fall-2026 (in_progress)")

        # ------------------------------------------------------------------
        # StudentAssignment 3: truss-practice-final -> submitted (6/8)
        # ------------------------------------------------------------------
        sa3_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a3.id,
            )
        )
        sa3 = sa3_row.scalar_one_or_none()
        if sa3 is None:
            sa3 = StudentAssignment(
                student_id=student.id,
                assignment_id=a3.id,
                seed=99,
                draft_answers={},
                submitted_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
                final_score=6.0,
            )
            db.add(sa3)
            await db.flush()

            for i, prob in enumerate(a3_probs):
                passed = i < 6
                db.add(
                    Submission(
                        student_assignment_id=sa3.id,
                        assignment_problem_id=prob.id,
                        attempt_number=1,
                        answers={},
                        raw_score=1.0 if passed else 0.0,
                        net_score=1.0 if passed else 0.0,
                        is_passed=passed,
                        field_verdicts={},
                    )
                )
            await db.flush()
            print("Seeded submissions for truss-practice-final (submitted 6/8)")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

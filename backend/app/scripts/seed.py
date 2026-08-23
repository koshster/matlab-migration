"""Seed script: creates instructor, course, assignments, and a demo student."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    Instructor,
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
            course = Course(instructor_id=instructor.id, code="ENGR301", term="Fall 2026")
            db.add(course)
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
            assignment_row = await db.execute(
                select(Assignment).where(Assignment.slug == slug)
            )
            a = assignment_row.scalar_one_or_none()
            if a is None:
                a = Assignment(
                    course_id=course.id,
                    slug=slug,
                    title=title,
                    tolerance=0.01,
                    feedback_mode="per_field",
                    max_attempts=None,
                    is_active=True,
                    due_at=due_at,
                )
                db.add(a)
                await db.flush()
                node_counts = [3, 3, 4, 4, 5, 5, 6, 6]
                for i, n in enumerate(node_counts):
                    db.add(AssignmentProblem(
                        assignment_id=a.id,
                        problem_type="truss",
                        order_index=i,
                        params={"num_nodes": n},
                    ))
                await db.flush()
                print(f"Created assignment {slug}")
            else:
                print(f"Assignment {slug} already exists")
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
        # StudentAssignment 1: truss-fall-2026 → in_progress
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

            # 3 problem attempts: problems 0 (correct), 1 (incorrect), 2 (correct)
            attempt_results = [(0, True), (1, False), (2, True)]
            for prob_idx, is_passed in attempt_results:
                ap = a1_probs[prob_idx]
                db.add(Submission(
                    student_assignment_id=sa1.id,
                    assignment_problem_id=ap.id,
                    attempt_number=1,
                    answers={"S1": 1.5, "S2": -2.0},
                    raw_score=1.0 if is_passed else 0.0,
                    net_score=1.0 if is_passed else 0.0,
                    is_passed=is_passed,
                    field_verdicts={"S1": is_passed, "S2": is_passed},
                ))
            await db.flush()
            print("Created StudentAssignment truss-fall-2026 (in_progress, 3 attempts)")
        else:
            print("StudentAssignment truss-fall-2026 already exists")

        # ------------------------------------------------------------------
        # StudentAssignment 2: truss-quiz-week8 → not_started
        # ------------------------------------------------------------------
        sa2_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a2.id,
            )
        )
        sa2 = sa2_row.scalar_one_or_none()
        if sa2 is None:
            sa2 = StudentAssignment(
                student_id=student.id,
                assignment_id=a2.id,
                seed=100,
                draft_answers={},
            )
            db.add(sa2)
            await db.flush()
            print("Created StudentAssignment truss-quiz-week8 (not_started)")
        else:
            print("StudentAssignment truss-quiz-week8 already exists")

        # ------------------------------------------------------------------
        # StudentAssignment 3: truss-practice-final → submitted, 6/8 correct
        # ------------------------------------------------------------------
        sa3_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a3.id,
            )
        )
        sa3 = sa3_row.scalar_one_or_none()
        if sa3 is None:
            submitted_at = datetime(2026, 8, 10, 14, 30, tzinfo=UTC)
            sa3 = StudentAssignment(
                student_id=student.id,
                assignment_id=a3.id,
                seed=200,
                draft_answers={},
                submitted_at=submitted_at,
                final_score=6.0,
            )
            db.add(sa3)
            await db.flush()

            # 8 submissions: problems 0-5 correct, 6-7 incorrect
            for i, ap in enumerate(a3_probs):
                is_passed = i < 6
                db.add(Submission(
                    student_assignment_id=sa3.id,
                    assignment_problem_id=ap.id,
                    attempt_number=1,
                    answers={"S1": 1.5, "S2": -2.0},
                    raw_score=1.0 if is_passed else 0.0,
                    net_score=1.0 if is_passed else 0.0,
                    is_passed=is_passed,
                    field_verdicts={"S1": is_passed, "S2": is_passed},
                    submitted_at=submitted_at,
                ))
            await db.flush()
            print("Created StudentAssignment truss-practice-final (submitted, 6/8)")
        else:
            print("StudentAssignment truss-practice-final already exists")

        await db.commit()
        print("\nSeed complete.")
        print("  Instructor: marko@university.edu / statics2026")
        print("  Student:    demo001 / demo1234")


if __name__ == "__main__":
    asyncio.run(seed())

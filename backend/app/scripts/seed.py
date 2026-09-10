"""Seed script: creates instructor, course, roster entries, assignments, and demo student."""

import asyncio
from datetime import UTC, datetime
from typing import Any

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
from app.problems.rigid_body.loads import (
    FORCE_DIRECTION_ANY,
    FORCE_DIRECTION_DOWNWARD,
    FORCE_DIRECTION_HORIZONTAL,
    FORCE_DIRECTION_VERTICAL,
    MOMENT_DIRECTION_ANY,
    MOMENT_DIRECTION_CCW,
    MOMENT_DIRECTION_CW,
)


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
            instructions: str,
            problem_type: str,
            problem_slots: list[dict[str, Any]],
            due_at: datetime | None = None,
        ) -> tuple[Assignment, list[AssignmentProblem]]:
            assignment_row = await db.execute(select(Assignment).where(Assignment.slug == slug))
            a = assignment_row.scalar_one_or_none()
            if a is None:
                a = Assignment(
                    course_id=course.id,
                    slug=slug,
                    title=title,
                    instructions=instructions,
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
                for i, slot in enumerate(problem_slots):
                    db.add(
                        AssignmentProblem(
                            assignment_id=a.id,
                            problem_type=problem_type,
                            order_index=i,
                            points=1.0,
                            params=slot,
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

        truss_slots = [
            {"num_nodes": n, "max_force": 5, "load_count": 2}
            for n in [3, 3, 4, 4, 5, 5, 6, 6]
        ]
        # 8 rigid-body problems: cycle support_case 1→2→3 to exercise all three
        # support types (rollers / pin+roller / cantilever wall), escalating loads.
        rigid_body_slots = [
            {"support_case": 2, "num_loads": 1, "num_moments": 0, "max_force": 3},
            {"support_case": 1, "num_loads": 1, "num_moments": 0, "max_force": 3},
            {"support_case": 3, "num_loads": 1, "num_moments": 0, "max_force": 3},
            {"support_case": 2, "num_loads": 2, "num_moments": 0, "max_force": 5},
            {"support_case": 1, "num_loads": 2, "num_moments": 1, "max_force": 5},
            {"support_case": 3, "num_loads": 2, "num_moments": 1, "max_force": 5},
            {"support_case": 2, "num_loads": 3, "num_moments": 1, "max_force": 8},
            {"support_case": 1, "num_loads": 3, "num_moments": 2, "max_force": 8},
        ]

        # One slot per load-configuration knob combination, so the effect of
        # `load_direction` / magnitude range is visible by paging between
        # problems instead of by re-rolling seeds. Equal min/max bounds pin
        # every load to one magnitude, which is what makes each slot legible.
        load_config_slots = [
            # 1. Gravity-style: every arrow points down, every label reads 3F.
            {
                "support_case": 2,
                "num_loads": 2,
                "load_direction": FORCE_DIRECTION_DOWNWARD,
                "min_force": 3,
                "max_force": 3,
                "num_moments": 0,
            },
            # 2. Same supports, horizontal loads only, all 2F.
            {
                "support_case": 2,
                "num_loads": 2,
                "load_direction": FORCE_DIRECTION_HORIZONTAL,
                "min_force": 2,
                "max_force": 2,
                "num_moments": 0,
            },
            # 3. Vertical only -- up or down, unlike slot 1 -- all 4F.
            {
                "support_case": 2,
                "num_loads": 2,
                "load_direction": FORCE_DIRECTION_VERTICAL,
                "min_force": 4,
                "max_force": 4,
                "num_moments": 0,
            },
            # 4. The unconstrained default over a wide magnitude range.
            {
                "support_case": 2,
                "num_loads": 3,
                "load_direction": FORCE_DIRECTION_ANY,
                "min_force": 1,
                "max_force": 9,
                "num_moments": 0,
            },
            # 5. The deck's slide-3 figure: three rollers, one horizontal F,
            #    one 4Fa couple.
            {
                "support_case": 1,
                "num_loads": 1,
                "load_direction": FORCE_DIRECTION_HORIZONTAL,
                "min_force": 1,
                "max_force": 1,
                "num_moments": 1,
                "moment_direction": MOMENT_DIRECTION_ANY,
                "min_moment": 4,
                "max_moment": 4,
            },
            # 6. Couples clockwise only, all 2Fa.
            {
                "support_case": 1,
                "num_loads": 1,
                "load_direction": FORCE_DIRECTION_DOWNWARD,
                "min_force": 2,
                "max_force": 2,
                "num_moments": 2,
                "moment_direction": MOMENT_DIRECTION_CW,
                "min_moment": 2,
                "max_moment": 2,
            },
            # 7. Couples counterclockwise only, all 5Fa.
            {
                "support_case": 2,
                "num_loads": 1,
                "load_direction": FORCE_DIRECTION_DOWNWARD,
                "min_force": 2,
                "max_force": 2,
                "num_moments": 1,
                "moment_direction": MOMENT_DIRECTION_CCW,
                "min_moment": 5,
                "max_moment": 5,
            },
            # 8. Cantilever wall carrying gravity-style loads only.
            {
                "support_case": 3,
                "num_loads": 3,
                "load_direction": FORCE_DIRECTION_DOWNWARD,
                "min_force": 1,
                "max_force": 4,
                "num_moments": 0,
            },
        ]

        a1, a1_probs = await get_or_create_assignment(
            "truss-fall-2026",
            "Truss Analysis — Fall 2026",
            "Determine the internal force in each truss member.",
            "truss",
            truss_slots,
            due_at=datetime(2026, 12, 15, 23, 59, tzinfo=UTC),
        )
        a2, _ = await get_or_create_assignment(
            "truss-quiz-week8",
            "Truss Review Quiz — Week 8",
            "Determine the internal force in each truss member.",
            "truss",
            truss_slots,
            due_at=datetime(2026, 10, 30, 23, 59, tzinfo=UTC),
        )
        a3, a3_probs = await get_or_create_assignment(
            "truss-practice-final",
            "Final Exam Practice",
            "Determine the internal force in each truss member.",
            "truss",
            truss_slots,
        )
        a4, _ = await get_or_create_assignment(
            "rigid-body-fall-2026",
            "Rigid Body Equilibrium — Fall 2026",
            "Determine the support reactions for the given rigid body.",
            "rigid_body",
            rigid_body_slots,
            due_at=datetime(2026, 12, 15, 23, 59, tzinfo=UTC),
        )
        a5, _ = await get_or_create_assignment(
            "rigid-body-load-directions",
            "Rigid Body — Load Direction & Magnitude",
            "Determine the support reactions for the given rigid body.",
            "rigid_body",
            load_config_slots,
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

        # ------------------------------------------------------------------
        # StudentAssignment 4: rigid-body-fall-2026 -> not started (just enrolled)
        # ------------------------------------------------------------------
        sa4_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a4.id,
            )
        )
        if sa4_row.scalar_one_or_none() is None:
            db.add(
                StudentAssignment(
                    student_id=student.id,
                    assignment_id=a4.id,
                    seed=77,
                    draft_answers={},
                )
            )
            await db.flush()
            print("Seeded rigid-body-fall-2026 for demo001 (not_started)")

        # ------------------------------------------------------------------
        # StudentAssignment 5: rigid-body-load-directions -> not started
        # ------------------------------------------------------------------
        sa5_row = await db.execute(
            select(StudentAssignment).where(
                StudentAssignment.student_id == student.id,
                StudentAssignment.assignment_id == a5.id,
            )
        )
        if sa5_row.scalar_one_or_none() is None:
            db.add(
                StudentAssignment(
                    student_id=student.id,
                    assignment_id=a5.id,
                    seed=2026,
                    draft_answers={},
                )
            )
            await db.flush()
            print("Seeded rigid-body-load-directions for demo001 (not_started)")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

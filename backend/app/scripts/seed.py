"""Seed script: creates instructor, course, and the truss-fall-2026 assignment."""

import asyncio

from passlib.context import CryptContext
from sqlalchemy import select

from app.db.models import Assignment, AssignmentProblem, Course, Instructor
from app.db.session import async_session_factory

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


async def seed() -> None:
    async with async_session_factory() as db:
        # Instructor
        result = await db.execute(select(Instructor).where(Instructor.email == "marko@university.edu"))
        instructor = result.scalar_one_or_none()
        if instructor is None:
            instructor = Instructor(
                email="marko@university.edu",
                password_hash=pwd_context.hash("statics2026"),
                name="Prof. Marko",
            )
            db.add(instructor)
            await db.flush()
            print("Created instructor marko@university.edu")
        else:
            print("Instructor already exists")

        # Course
        result = await db.execute(
            select(Course).where(Course.code == "ENGR301", Course.term == "Fall 2026")
        )
        course = result.scalar_one_or_none()
        if course is None:
            course = Course(
                instructor_id=instructor.id,
                code="ENGR301",
                term="Fall 2026",
            )
            db.add(course)
            await db.flush()
            print("Created course ENGR301 Fall 2026")
        else:
            print("Course already exists")

        # Assignment
        result = await db.execute(
            select(Assignment).where(Assignment.slug == "truss-fall-2026")
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            assignment = Assignment(
                course_id=course.id,
                slug="truss-fall-2026",
                title="Truss Analysis — Fall 2026",
                tolerance=0.01,
                feedback_mode="per_field",
                max_attempts=None,
                is_active=True,
            )
            db.add(assignment)
            await db.flush()
            print("Created assignment truss-fall-2026")

            node_counts = [3, 3, 4, 4, 5, 5, 6, 6]
            for i, n in enumerate(node_counts):
                ap = AssignmentProblem(
                    assignment_id=assignment.id,
                    problem_type="truss",
                    order_index=i,
                    params={"num_nodes": n},
                )
                db.add(ap)
            await db.flush()
            print("Created 8 problem slots")
        else:
            print("Assignment truss-fall-2026 already exists")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

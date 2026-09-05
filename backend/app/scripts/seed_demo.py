"""Demo seed: rich student roster with varied submission states for testing.

Run with:
    docker compose run --rm backend python -m app.scripts.seed_demo

Students created
----------------
A11111111  Alice Chen        demo1234   enrolled, in_progress  (3 correct, 1 wrong attempt)
A22222222  Bob Torres        demo1234   enrolled, submitted     (8/8 perfect on truss-fall-2026)
A33333333  Carol Kim         demo1234   enrolled, not_started   (opened the course, zero attempts)
A44444444  Dave Patel        demo1234   pending invite  (has account, not yet accepted)
A55555555  Emma Wu           -          unclaimed slot  (no account; links on register)
"""

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models import (
    Assignment,
    AssignmentProblem,
    Course,
    CourseEnrollment,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import async_session_factory

PASSWORD = "demo1234"

# Problem answers are stored in submissions but not re-graded, so we use
# placeholder values. is_passed / field_verdicts are the source of truth for
# the UI; the raw answer dict is audit-only here.
_CORRECT_ANSWERS = {"S1": 2.5, "S2": -1.5, "S3": 0.5}
_WRONG_ANSWERS = {"S1": 999.0, "S2": -999.0, "S3": 0.0}


async def _get_student(db: AsyncSession, pid: str) -> Student | None:
    row = await db.execute(select(Student).where(Student.pid == pid))
    return row.scalar_one_or_none()


async def _ensure_student(db: AsyncSession, pid: str, first: str, last: str) -> Student:
    s = await _get_student(db, pid)
    if s is None:
        s = Student(
            pid=pid,
            first_name=first,
            last_name=last,
            password_hash=hash_password(PASSWORD),
        )
        db.add(s)
        await db.flush()
        print(f"  Created student {pid} ({first} {last})")
    else:
        print(f"  Student {pid} already exists")
    return s


async def _ensure_roster(
    db: AsyncSession,
    course: Course,
    student_id: uuid.UUID | None,
    pid: str,
    first: str,
    last: str,
    status: str,
    accepted_at: datetime | None = None,
) -> None:
    row = await db.execute(
        select(RosterEntry).where(
            RosterEntry.course_id == course.id,
            RosterEntry.pid == pid.upper(),
        )
    )
    if row.scalar_one_or_none() is not None:
        print(f"  Roster entry {pid} already exists")
        return
    entry = RosterEntry(
        course_id=course.id,
        student_id=student_id,
        pid=pid.upper(),
        email=f"{first.lower()}.{last.lower()}@university.edu",
        first_name=first,
        last_name=last,
        status=status,
        accepted_at=accepted_at,
    )
    db.add(entry)
    await db.flush()
    print(f"  Roster entry {pid} ({status})")


async def _ensure_enrollment(db: AsyncSession, course: Course, student_id: uuid.UUID) -> None:
    row = await db.execute(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.student_id == student_id,
        )
    )
    if row.scalar_one_or_none() is None:
        db.add(
            CourseEnrollment(
                course_id=course.id,
                student_id=student_id,
                status="active",
            )
        )
        await db.flush()


async def _get_assignment(db: AsyncSession, slug: str) -> Assignment | None:
    row = await db.execute(select(Assignment).where(Assignment.slug == slug))
    return row.scalar_one_or_none()


async def _get_problems(db: AsyncSession, assignment: Assignment) -> list[AssignmentProblem]:
    rows = await db.execute(
        select(AssignmentProblem)
        .where(AssignmentProblem.assignment_id == assignment.id)
        .order_by(AssignmentProblem.order_index)
    )
    return list(rows.scalars().all())


async def _get_or_create_sa(
    db: AsyncSession,
    student_id: uuid.UUID,
    assignment_id: uuid.UUID,
    seed: int,
) -> tuple[StudentAssignment, bool]:
    row = await db.execute(
        select(StudentAssignment).where(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id,
        )
    )
    sa = row.scalar_one_or_none()
    if sa is not None:
        return sa, False
    sa = StudentAssignment(
        student_id=student_id,
        assignment_id=assignment_id,
        seed=seed,
        draft_answers={},
    )
    db.add(sa)
    await db.flush()
    return sa, True


def _correct_verdicts(n_members: int) -> dict[str, bool]:
    return {f"S{i + 1}": True for i in range(n_members)}


def _wrong_verdicts(n_members: int) -> dict[str, bool]:
    return {f"S{i + 1}": False for i in range(n_members)}


async def _submission(
    db: AsyncSession,
    sa_id: uuid.UUID,
    prob_id: uuid.UUID,
    attempt: int,
    passed: bool,
    n_members: int = 3,
) -> None:
    db.add(
        Submission(
            student_assignment_id=sa_id,
            assignment_problem_id=prob_id,
            attempt_number=attempt,
            answers=_CORRECT_ANSWERS if passed else _WRONG_ANSWERS,
            raw_score=1.0 if passed else 0.0,
            net_score=1.0 if passed else 0.0,
            is_passed=passed,
            field_verdicts=_correct_verdicts(n_members) if passed else _wrong_verdicts(n_members),
        )
    )


async def seed_demo() -> None:
    async with async_session_factory() as db:
        course_row = await db.execute(
            select(Course).where(Course.code == "ENGR301", Course.term == "Fall 2026")
        )
        course = course_row.scalar_one_or_none()
        if course is None:
            print("ERROR: ENGR301 course not found — run `make seed` first.")
            return

        a1 = await _get_assignment(db, "truss-fall-2026")
        a3 = await _get_assignment(db, "truss-practice-final")
        if a1 is None or a3 is None:
            print("ERROR: assignments not found — run `make seed` first.")
            return

        a1_probs = await _get_problems(db, a1)
        a3_probs = await _get_problems(db, a3)
        accepted = datetime(2026, 8, 20, 9, 0, tzinfo=UTC)

        # ------------------------------------------------------------------
        # Alice Chen — in_progress, 3 correct + 1 wrong attempt on problem 4
        # ------------------------------------------------------------------
        print("\nAlice Chen (A11111111):")
        alice = await _ensure_student(db, "A11111111", "Alice", "Chen")
        await _ensure_roster(db, course, alice.id, "A11111111", "Alice", "Chen", "active", accepted)
        await _ensure_enrollment(db, course, alice.id)

        sa, created = await _get_or_create_sa(db, alice.id, a1.id, seed=1001)
        if created:
            # Problems 0–2: correct first try
            for i in range(3):
                await _submission(db, sa.id, a1_probs[i].id, attempt=1, passed=True)
            # Problem 3: one wrong attempt, then correct
            await _submission(db, sa.id, a1_probs[3].id, attempt=1, passed=False)
            await _submission(db, sa.id, a1_probs[3].id, attempt=2, passed=True)
            # Problem 4: one wrong attempt, still incorrect
            await _submission(db, sa.id, a1_probs[4].id, attempt=1, passed=False)
            await db.flush()
            print("  Seeded Alice's submissions (3 correct, 1 wrong in progress)")

        # ------------------------------------------------------------------
        # Bob Torres — submitted truss-fall-2026, 8/8 perfect
        # ------------------------------------------------------------------
        print("\nBob Torres (A22222222):")
        bob = await _ensure_student(db, "A22222222", "Bob", "Torres")
        await _ensure_roster(db, course, bob.id, "A22222222", "Bob", "Torres", "active", accepted)
        await _ensure_enrollment(db, course, bob.id)

        sa, created = await _get_or_create_sa(db, bob.id, a1.id, seed=2002)
        if created:
            for prob in a1_probs:
                await _submission(db, sa.id, prob.id, attempt=1, passed=True)
            sa.submitted_at = datetime(2026, 8, 25, 14, 30, tzinfo=UTC)
            sa.final_score = 8.0
            db.add(sa)
            await db.flush()
            print("  Seeded Bob's submissions (8/8, submitted)")

        # Also give Bob the practice final with 6/8
        sa3, created3 = await _get_or_create_sa(db, bob.id, a3.id, seed=2099)
        if created3:
            for i, prob in enumerate(a3_probs):
                await _submission(db, sa3.id, prob.id, attempt=1, passed=(i < 6))
            sa3.submitted_at = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)
            sa3.final_score = 6.0
            db.add(sa3)
            await db.flush()
            print("  Seeded Bob's practice final (6/8, submitted)")

        # ------------------------------------------------------------------
        # Carol Kim — enrolled, not started (zero attempts)
        # ------------------------------------------------------------------
        print("\nCarol Kim (A33333333):")
        carol = await _ensure_student(db, "A33333333", "Carol", "Kim")
        await _ensure_roster(db, course, carol.id, "A33333333", "Carol", "Kim", "active", accepted)
        await _ensure_enrollment(db, course, carol.id)
        print("  Enrolled, no attempts (not_started)")

        # ------------------------------------------------------------------
        # Dave Patel — has account but roster entry is still "invited"
        # He can log in and will see a pending ENGR301 invitation to accept
        # ------------------------------------------------------------------
        print("\nDave Patel (A44444444):")
        dave = await _ensure_student(db, "A44444444", "Dave", "Patel")
        await _ensure_roster(
            db,
            course,
            dave.id,
            "A44444444",
            "Dave",
            "Patel",
            status="invited",
            accepted_at=None,
        )
        print("  Has account, invitation pending (log in as Dave to test accept flow)")

        # ------------------------------------------------------------------
        # Emma Wu — no student account; unclaimed roster slot
        # She will see the invitation once she registers as A55555555
        # ------------------------------------------------------------------
        print("\nEmma Wu (A55555555):")
        row = await db.execute(
            select(RosterEntry).where(
                RosterEntry.course_id == course.id,
                RosterEntry.pid == "A55555555",
            )
        )
        if row.scalar_one_or_none() is None:
            db.add(
                RosterEntry(
                    course_id=course.id,
                    student_id=None,
                    pid="A55555555",
                    email="emma.wu@university.edu",
                    first_name="Emma",
                    last_name="Wu",
                    status="invited",
                )
            )
            await db.flush()
            print("  Unclaimed roster slot (register as A55555555 to claim)")
        else:
            print("  Roster slot already exists")

        await db.commit()
        print("\nDemo seed complete.")
        print("\nCredentials:")
        print("  Instructor : marko@university.edu  /  statics2026")
        print("  Alice Chen : A11111111  /  demo1234   (in_progress)")
        print("  Bob Torres : A22222222  /  demo1234   (submitted 8/8)")
        print("  Carol Kim  : A33333333  /  demo1234   (enrolled, not started)")
        print("  Dave Patel : A44444444  /  demo1234   (pending invitation)")
        print("  Emma Wu    : A55555555  /  demo1234   (register to claim invite)")


if __name__ == "__main__":
    asyncio.run(seed_demo())

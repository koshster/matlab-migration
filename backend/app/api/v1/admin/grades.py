"""Instructor gradebook and assignment analytics.

Deliberately not gated on the assignment being closed: staff need to watch a
class work through an assignment, not just read the post-mortem. Reader is
enough -- TAs and graders need visibility without edit rights.

The roster, not the set of students who happened to open the assignment, is the
denominator. A student who never started still appears as `not_started`, which
is exactly the signal an instructor is looking for.
"""

import statistics
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.assignments import is_gradeable
from app.db.models import (
    Assignment,
    Instructor,
    RosterEntry,
    Student,
    StudentAssignment,
    Submission,
)
from app.db.session import get_db
from app.services.access import compute_access, effective_close_at, isoformat_utc
from app.services.authz import assert_course_role, require_instructor

router = APIRouter(tags=["admin-grades"])


async def _load_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> Assignment:
    row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(selectinload(Assignment.problems), selectinload(Assignment.targets))
    )
    assignment = row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return assignment


async def _gather(
    db: AsyncSession, assignment: Assignment
) -> tuple[list[tuple[RosterEntry, Student | None, StudentAssignment | None]], dict[Any, Any]]:
    """Three queries total, independent of class size.

    The per-problem aggregate is grouped in SQL rather than eager-loading every
    Submission row: a 40-student, 8-problem, 3-attempt assignment would
    otherwise materialize ~960 ORM objects to produce 320 integers.
    """
    targeted_entry_ids: set[uuid.UUID] | None = None
    if assignment.audience == "selected":
        targeted_entry_ids = {t.roster_entry_id for t in assignment.targets}

    roster_rows = (
        await db.execute(
            select(RosterEntry, Student, StudentAssignment)
            .outerjoin(Student, Student.id == RosterEntry.student_id)
            .outerjoin(
                StudentAssignment,
                and_(
                    StudentAssignment.student_id == RosterEntry.student_id,
                    StudentAssignment.assignment_id == assignment.id,
                ),
            )
            .where(
                RosterEntry.course_id == assignment.course_id,
                RosterEntry.status != "dropped",
            )
            .order_by(RosterEntry.last_name, RosterEntry.first_name)
        )
    ).all()

    rows = [
        (entry, student, sa)
        for entry, student, sa in roster_rows
        if targeted_entry_ids is None or entry.id in targeted_entry_ids
    ]

    # func.max(case(...)) rather than bool_or: bool_or is Postgres-only and the
    # test suite runs on SQLite.
    agg_rows = (
        await db.execute(
            select(
                Submission.student_assignment_id,
                Submission.assignment_problem_id,
                func.count(Submission.id).label("attempts"),
                func.max(case((Submission.is_passed, 1), else_=0)).label("passed"),
                func.max(Submission.submitted_at).label("last_at"),
            )
            .join(StudentAssignment, StudentAssignment.id == Submission.student_assignment_id)
            .where(StudentAssignment.assignment_id == assignment.id)
            .group_by(Submission.student_assignment_id, Submission.assignment_problem_id)
        )
    ).all()

    agg = {(r.student_assignment_id, r.assignment_problem_id): r for r in agg_rows}
    return rows, agg


def _student_status(
    assignment: Assignment, sa: StudentAssignment | None, attempted: bool
) -> tuple[str, Any]:
    if sa is None:
        return "not_started", None
    state = compute_access(assignment, sa)
    if state.close_reason == "submitted":
        return "submitted", state
    if state.closed:
        return "closed", state
    return ("in_progress" if attempted else "not_started"), state


def _display_name(entry: RosterEntry, student: Student | None) -> str:
    if student is not None:
        return f"{student.first_name} {student.last_name}".strip()
    parts = [p for p in (entry.first_name, entry.last_name) if p]
    return " ".join(parts) if parts else (entry.email or "Unknown")


@router.get(
    "/assignments/{assignment_id}/gradebook",
    summary="Per-student scores and problem status for an assignment",
)
async def get_gradebook(
    assignment_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    assignment = await _load_assignment(db, assignment_id)
    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")

    problems = sorted(assignment.problems, key=lambda p: p.order_index)
    gradeable = {ap.id: is_gradeable(ap.problem_type) for ap in problems}
    total_points = sum(float(ap.points) for ap in problems if gradeable[ap.id])

    rows, agg = await _gather(db, assignment)

    out_rows: list[dict[str, Any]] = []
    for entry, student, sa in rows:
        cells: list[dict[str, Any]] = []
        earned = 0.0
        attempted = False
        last_activity: datetime | None = None

        for offset, ap in enumerate(problems):
            record = agg.get((sa.id, ap.id)) if sa is not None else None
            attempts = int(record.attempts) if record else 0
            passed = bool(record.passed) if record else False
            if attempts:
                attempted = True
                if record is not None and record.last_at is not None:
                    candidate = record.last_at
                    if last_activity is None or candidate > last_activity:
                        last_activity = candidate
            if passed and gradeable[ap.id]:
                earned += float(ap.points)
            cells.append(
                {
                    "index": offset + 1,
                    "status": "correct" if passed else "incorrect" if attempts else "no_attempt",
                    "attemptCount": attempts,
                }
            )

        row_status, state = _student_status(assignment, sa, attempted)
        is_final = state is not None and state.closed
        out_rows.append(
            {
                "studentId": str(student.id) if student else None,
                "displayName": _display_name(entry, student),
                "externalId": entry.pid or "",
                "status": row_status,
                # Withheld until the work is final: a partial score shown as a
                # grade would misrepresent a student mid-assignment.
                "earned": earned if is_final else None,
                "total": total_points,
                "submittedAt": isoformat_utc(sa.submitted_at) if sa else None,
                "lastActivityAt": isoformat_utc(last_activity),
                "problems": cells,
            }
        )

    return {
        "assignmentId": str(assignment.id),
        "slug": assignment.slug,
        "title": assignment.title,
        "totalPoints": total_points,
        "closesAt": isoformat_utc(effective_close_at(assignment)),
        "problems": [
            {
                "index": offset + 1,
                "problemType": ap.problem_type,
                "points": float(ap.points),
                "gradeable": gradeable[ap.id],
            }
            for offset, ap in enumerate(problems)
        ],
        "rows": out_rows,
    }


@router.get(
    "/assignments/{assignment_id}/analytics",
    summary="Score distribution and per-problem success rates",
)
async def get_analytics(
    assignment_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    assignment = await _load_assignment(db, assignment_id)
    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")

    problems = sorted(assignment.problems, key=lambda p: p.order_index)
    gradeable = {ap.id: is_gradeable(ap.problem_type) for ap in problems}
    total_points = sum(float(ap.points) for ap in problems if gradeable[ap.id])

    rows, agg = await _gather(db, assignment)

    scores: list[float] = []
    started = submitted = closed = 0
    per_problem: dict[uuid.UUID, dict[str, float]] = {
        ap.id: {"attempted": 0.0, "correct": 0.0, "attempts": 0.0} for ap in problems
    }

    for _entry, _student, sa in rows:
        attempted_any = False
        earned = 0.0
        for ap in problems:
            record = agg.get((sa.id, ap.id)) if sa is not None else None
            if not record:
                continue
            attempted_any = True
            bucket = per_problem[ap.id]
            bucket["attempted"] += 1
            bucket["attempts"] += int(record.attempts)
            if record.passed:
                bucket["correct"] += 1
                if gradeable[ap.id]:
                    earned += float(ap.points)

        if attempted_any:
            started += 1
        if sa is None:
            continue
        state = compute_access(assignment, sa)
        if state.close_reason == "submitted":
            submitted += 1
        if state.closed:
            closed += 1
            # Only final work enters the distribution; mixing in half-finished
            # sessions would drag every average toward zero.
            scores.append(earned)

    return {
        "assignmentId": str(assignment.id),
        "slug": assignment.slug,
        "title": assignment.title,
        "totalPoints": total_points,
        "closesAt": isoformat_utc(effective_close_at(assignment)),
        "studentCount": len(rows),
        "startedCount": started,
        "submittedCount": submitted,
        "closedCount": closed,
        "gradedCount": len(scores),
        "meanScore": round(statistics.fmean(scores), 4) if scores else None,
        "medianScore": round(statistics.median(scores), 4) if scores else None,
        "minScore": min(scores) if scores else None,
        "maxScore": max(scores) if scores else None,
        "problems": [
            {
                "index": offset + 1,
                "problemType": ap.problem_type,
                "gradeable": gradeable[ap.id],
                "attemptedCount": int(per_problem[ap.id]["attempted"]),
                "correctCount": int(per_problem[ap.id]["correct"]),
                "successRate": (
                    round(per_problem[ap.id]["correct"] / per_problem[ap.id]["attempted"], 4)
                    if per_problem[ap.id]["attempted"]
                    else None
                ),
                "meanAttempts": (
                    round(per_problem[ap.id]["attempts"] / per_problem[ap.id]["attempted"], 4)
                    if per_problem[ap.id]["attempted"]
                    else None
                ),
            }
            for offset, ap in enumerate(problems)
        ],
    }

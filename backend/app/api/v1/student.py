import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_student_id
from app.db.models import Assignment, StudentAssignment, Submission
from app.db.session import get_db

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/assignments")
async def list_student_assignments(
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(StudentAssignment, Assignment)
                .join(Assignment, StudentAssignment.assignment_id == Assignment.id)
                .where(StudentAssignment.student_id == student_id)
                .options(
                    selectinload(StudentAssignment.submissions),
                    selectinload(Assignment.problems),
                )
                .order_by(Assignment.created_at.desc())
            )
        ).all()
    )

    items: list[dict[str, Any]] = []
    for sa, assignment in rows:
        locked = bool(sa.submitted_at)
        subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
        for sub in sa.submissions:
            subs_by_problem.setdefault(sub.assignment_problem_id, []).append(sub)

        problems_status = [
            (
                "correct"
                if any(s.is_passed for s in subs_by_problem.get(ap.id, []))
                else "incorrect"
                if subs_by_problem.get(ap.id)
                else "no_attempt"
            )
            for ap in assignment.problems
        ]

        if locked:
            earned = sum(1 for s in problems_status if s == "correct")
            assign_status: str = "submitted"
            score: dict[str, int] | None = {"earned": earned, "total": len(assignment.problems)}
        elif any(s != "no_attempt" for s in problems_status):
            assign_status = "in_progress"
            score = None
        else:
            assign_status = "not_started"
            score = None

        items.append(
            {
                "slug": assignment.slug,
                "title": assignment.title,
                "status": assign_status,
                "score": score,
                "dueAt": assignment.due_at.isoformat() if assignment.due_at else None,
                "problemCount": len(assignment.problems),
            }
        )

    return items

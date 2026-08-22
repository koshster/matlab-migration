import random
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_student_token
from app.db.models import Assignment, Student, StudentAssignment, Submission
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class StudentSessionRequest(BaseModel):
    externalId: str
    firstName: str
    lastName: str
    assignmentSlug: str


def _build_assignment_summary(
    assignment: Assignment,
    student_assignment: StudentAssignment,
    submissions: list[Submission],
) -> dict[str, Any]:
    sub_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for sub in submissions:
        sub_by_problem.setdefault(sub.assignment_problem_id, []).append(sub)

    problems = []
    for ap in sorted(assignment.problems, key=lambda p: p.order_index):
        subs = sub_by_problem.get(ap.id, [])
        attempt_count = len(subs)
        if not subs:
            prob_status = "no_attempt"
        elif any(s.is_passed for s in subs):
            prob_status = "correct"
        else:
            prob_status = "incorrect"
        problems.append(
            {
                "index": ap.order_index,
                "problemType": ap.problem_type,
                "status": prob_status,
                "attemptCount": attempt_count,
            }
        )

    score = None
    if student_assignment.submitted_at:
        earned = sum(1 for p in problems if p["status"] == "correct")
        score = {"earned": earned, "total": len(problems)}

    locked = bool(student_assignment.submitted_at)
    assign_status = (
        "submitted"
        if locked
        else ("in_progress" if any(p["status"] != "no_attempt" for p in problems) else "not_started")
    )

    return {
        "slug": assignment.slug,
        "title": assignment.title,
        "problemCount": len(problems),
        "status": assign_status,
        "feedbackMode": assignment.feedback_mode,
        "maxAttempts": assignment.max_attempts,
        "dueAt": assignment.due_at.isoformat() if assignment.due_at else None,
        "locked": locked,
        "problems": problems,
        "score": score,
    }


@router.post("/student/session")
async def create_student_session(
    body: StudentSessionRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    # Find or create student
    result = await db.execute(select(Student).where(Student.pid == body.externalId))
    student = result.scalar_one_or_none()
    if student is None:
        student = Student(
            pid=body.externalId,
            first_name=body.firstName,
            last_name=body.lastName,
        )
        db.add(student)
        await db.flush()

    # Find assignment
    result = await db.execute(
        select(Assignment)
        .where(Assignment.slug == body.assignmentSlug)
        .options(selectinload(Assignment.problems))
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    # Find or create student assignment
    result = await db.execute(
        select(StudentAssignment).where(
            StudentAssignment.student_id == student.id,
            StudentAssignment.assignment_id == assignment.id,
        )
    )
    student_assignment = result.scalar_one_or_none()
    if student_assignment is None:
        student_assignment = StudentAssignment(
            student_id=student.id,
            assignment_id=assignment.id,
            seed=random.randint(1, 10_000_000),
            draft_answers={},
        )
        db.add(student_assignment)
        await db.flush()

    # Load submissions for this student assignment
    result = await db.execute(
        select(Submission).where(Submission.student_assignment_id == student_assignment.id)
    )
    submissions = list(result.scalars().all())

    # Already submitted → 409
    if student_assignment.submitted_at:
        earned = sum(
            1
            for ap in assignment.problems
            if any(
                s.is_passed
                for s in submissions
                if s.assignment_problem_id == ap.id
            )
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ALREADY_SUBMITTED",
                "submittedAt": student_assignment.submitted_at.isoformat(),
                "score": earned,
                "total": len(assignment.problems),
            },
        )

    token = create_student_token(student.id, student_assignment.id)
    response.set_cookie(
        key="student_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.jwt_expire_minutes * 60,
    )

    summary = _build_assignment_summary(assignment, student_assignment, submissions)
    return {
        "student": {
            "id": str(student.id),
            "firstName": student.first_name,
            "lastName": student.last_name,
        },
        "assignment": summary,
    }

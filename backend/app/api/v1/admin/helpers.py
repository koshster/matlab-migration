"""Helper formatting and visual schema serialization utilities for admin endpoints."""

from typing import Any

from app.db.models import Assignment, Course, RosterEntry
from app.services.access import effective_close_at, isoformat_utc



def _course_summary(
    c: Course,
    viewer_role: str,
    student_count: int = 0,
    pending_invite_count: int = 0,
    assignment_count: int = 0,
) -> dict[str, Any]:
    """Serialize Course ORM model into CourseSummary response DTO."""
    return {
        "id": str(c.id),
        "code": c.code,
        "term": c.term,
        "section": c.section,
        "title": c.title,
        "isArchived": c.is_archived,
        "createdAt": c.created_at.isoformat() if c.created_at else "",
        "viewerRole": viewer_role,
        "studentCount": student_count,
        "pendingInviteCount": pending_invite_count,
        "assignmentCount": assignment_count,
    }


def _roster_entry_out(entry: RosterEntry) -> dict[str, Any]:
    """Serialize RosterEntry ORM model into JSON response DTO."""
    return {
        "id": str(entry.id),
        "courseId": str(entry.course_id),
        "studentId": str(entry.student_id) if entry.student_id else None,
        "hasAccount": entry.student_id is not None,
        "pid": entry.pid,
        "email": entry.email,
        "firstName": entry.first_name,
        "lastName": entry.last_name,
        "status": entry.status,
        "invitedAt": entry.invited_at.isoformat() if entry.invited_at else "",
        "acceptedAt": entry.accepted_at.isoformat() if entry.accepted_at else None,
    }


def _admin_assignment_summary(a: Assignment) -> dict[str, Any]:
    """Serialize Assignment into admin list item DTO."""
    return {
        "id": str(a.id),
        "courseId": str(a.course_id),
        "slug": a.slug,
        "title": a.title,
        "isPublished": a.is_published,
        "audience": a.audience,
        "problemCount": len(a.problems),
        "opensAt": isoformat_utc(a.opens_at),
        "dueAt": isoformat_utc(a.due_at),
        "hardDeadlineAt": isoformat_utc(a.hard_deadline_at),
        "allowLate": a.allow_late,
        "latePenaltyRate": a.late_penalty_rate,
        "revealSolutionsAfterClose": a.reveal_solutions_after_close,
        # The instant the late policy actually closes it, so the builder does
        # not make the instructor apply the rules in their head.
        "effectiveCloseAt": isoformat_utc(effective_close_at(a)),
        "createdAt": a.created_at.isoformat() if a.created_at else "",
    }


def _admin_assignment_detail(a: Assignment) -> dict[str, Any]:
    """Serialize Assignment into full builder detail response DTO."""
    problems_sorted = sorted(a.problems, key=lambda p: p.order_index)
    return {
        "id": str(a.id),
        "courseId": str(a.course_id),
        "slug": a.slug,
        "title": a.title,
        "instructions": a.instructions,
        "tolerance": a.tolerance,
        "feedbackMode": a.feedback_mode,
        "maxAttempts": a.max_attempts,
        "penaltyPerAttempt": a.penalty_per_attempt,
        "scoringStrategy": a.scoring_strategy,
        "isPublished": a.is_published,
        "audience": a.audience,
        "problemCount": len(problems_sorted),
        "targetEntryIds": [str(t.roster_entry_id) for t in a.targets],
        "problems": [
            {
                "orderIndex": p.order_index + 1,
                "problemType": p.problem_type,
                "params": p.params,
                "points": p.points,
            }
            for p in problems_sorted
        ],
        "opensAt": isoformat_utc(a.opens_at),
        "dueAt": isoformat_utc(a.due_at),
        "hardDeadlineAt": isoformat_utc(a.hard_deadline_at),
        "allowLate": a.allow_late,
        "latePenaltyRate": a.late_penalty_rate,
        "revealSolutionsAfterClose": a.reveal_solutions_after_close,
        # The instant the late policy actually closes it, so the builder does
        # not make the instructor apply the rules in their head.
        "effectiveCloseAt": isoformat_utc(effective_close_at(a)),
        "createdAt": a.created_at.isoformat() if a.created_at else "",
    }

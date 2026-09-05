"""Helper formatting and visual schema serialization utilities for admin endpoints."""

from typing import Any

from app.db.models import Assignment, Course, RosterEntry
from app.problems.base import VisualElementSchema
from app.services.access import effective_close_at, isoformat_utc


def _build_truss_geometry(visual_schema: list[VisualElementSchema]) -> dict[str, Any]:
    """Convert raw VisualElementSchema list into structured frontend geometry contract."""
    nodes: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    supports: list[dict[str, Any]] = []
    forces: list[dict[str, Any]] = []

    for el in visual_schema:
        if el.element_type == "node":
            nodes.append(
                {
                    "id": el.properties["id"],
                    "x": el.properties["x"],
                    "y": el.properties["y"],
                }
            )
        elif el.element_type == "member":
            members.append(
                {
                    "id": el.properties["id"],
                    "startNode": el.properties["start_node"],
                    "endNode": el.properties["end_node"],
                }
            )
        elif el.element_type == "pin":
            supports.append(
                {
                    "type": "pin",
                    "nodeId": el.properties["node_index"],
                    "r": el.properties["r"],
                }
            )
        elif el.element_type == "roller":
            supports.append(
                {
                    "type": "roller",
                    "nodeId": el.properties["node_index"],
                    "r": el.properties["r"],
                    "rotation": el.properties.get("rotation", 0),
                }
            )
        elif el.element_type == "point_load":
            forces.append(
                {
                    "nodeId": el.properties["node_index"],
                    "fx": el.properties["force_vector"][0],
                    "fy": el.properties["force_vector"][1],
                }
            )

    # Compute bounding box
    xs = [n["x"] for n in nodes]
    ys = [n["y"] for n in nodes]
    min_x, max_x = (min(xs), max(xs)) if xs else (0.0, 10.0)
    min_y, max_y = (min(ys), max(ys)) if ys else (0.0, 10.0)

    return {
        "nodes": sorted(nodes, key=lambda n: int(n["id"])),
        "members": members,
        "supports": supports,
        "forces": forces,
        "bounds": {
            "minX": min_x - 1.0,
            "maxX": max_x + 1.0,
            "minY": min_y - 1.0,
            "maxY": max_y + 1.0,
        },
    }


def _build_answer_schema(members: list[dict[str, Any]]) -> dict[str, Any]:
    """Build answer input field schema for each truss member."""
    fields: list[dict[str, Any]] = []
    for m in members:
        fields.append(
            {
                "name": f"force_{m['id']}",
                "label": f"{m['id']} force",
                "type": "number",
                "unit": "kN",
            }
        )
        fields.append(
            {
                "name": f"state_{m['id']}",
                "label": f"{m['id']} state",
                "type": "choice",
                "choices": ["T", "C", "Zero"],
            }
        )
    return {"groups": [{"label": "Member Forces & States", "fields": fields}]}


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

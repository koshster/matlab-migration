import random
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.problems  # noqa: F401 — triggers registry registration
from app.core.security import get_current_student_id
from app.db.models import Assignment, AssignmentProblem, Student, StudentAssignment, Submission
from app.db.session import get_db
from app.problems.registry import problem_registry

router = APIRouter(prefix="/assignments", tags=["assignments"])


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

class AnswersRequest(BaseModel):
    answers: dict[str, float | None]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _effective_seed(student_assignment: StudentAssignment, index: int) -> int:
    return student_assignment.seed + index


_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def member_field_key(member_id: int) -> str:
    """Answer-field key for a member, e.g. 1 -> 'S1'. Stable across releases."""
    return f"S{member_id}"


def _member_label(member_id: int) -> str:
    """Display label for a member, e.g. 1 -> 'S₁'."""
    return "S" + str(member_id).translate(_SUBSCRIPT_DIGITS)


def _build_truss_geometry(visual_schema: list[Any]) -> dict[str, Any]:
    """Translate generator primitives into the contract's TrussGeometry shape.

    Node and member ids are 1-based on the wire; the generator emits 0-based
    node indices, so every node reference is offset by one here.
    """
    nodes, members, supports, forces = [], [], [], []
    member_idx = 0
    for el in visual_schema:
        p = el.properties
        t = el.element_type
        if t == "node":
            nodes.append({"id": int(p["id"]) + 1, "x": p["x"], "y": p["y"]})
        elif t == "member":
            member_idx += 1
            members.append({
                "id": member_idx,
                "from": int(p["start_node"]) + 1,
                "to": int(p["end_node"]) + 1,
                "label": _member_label(member_idx),
            })
        elif t in ("pin", "roller"):
            supports.append({
                "node": int(p["node_index"]) + 1,
                "type": t,
                # Pins always sit base-down; rollers carry an outward rotation.
                "angleDeg": int(p.get("rotation", 0)),
            })
        elif t == "point_load":
            fv = p["force_vector"]
            mag = (fv[0] ** 2 + fv[1] ** 2) ** 0.5
            forces.append({
                "node": int(p["node_index"]) + 1,
                "fx": float(fv[0]),
                "fy": float(fv[1]),
                "label": f"{mag:.1f}F",
            })

    if nodes:
        xs = [n["x"] for n in nodes]
        ys = [n["y"] for n in nodes]
        raw_range = max(max(xs) - min(xs), max(ys) - min(ys))
        # Normalize so the largest span is 4 SVG units; the SVG
        # sub-components are sized for ~4-unit geometry.
        scale = 4.0 / raw_range if raw_range > 0.01 else 1.0
        for n in nodes:
            n["x"] = round(n["x"] * scale, 4)
            n["y"] = round(n["y"] * scale, 4)
        xs = [n["x"] for n in nodes]
        ys = [n["y"] for n in nodes]
        pad_x = max((max(xs) - min(xs)) * 0.15, 1.0)
        pad_y = max((max(ys) - min(ys)) * 0.15, 1.0)
        bounds = {
            "xMin": min(xs) - pad_x,
            "xMax": max(xs) + pad_x,
            "yMin": min(ys) - pad_y,
            "yMax": max(ys) + pad_y,
        }
    else:
        bounds = {"xMin": -1, "xMax": 1, "yMin": -1, "yMax": 1}

    return {
        "schemaVersion": 1,
        "nodes": nodes,
        "members": members,
        "supports": supports,
        "forces": forces,
        "bounds": bounds,
    }


def _build_answer_schema(members: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        {
            "key": member_field_key(m["id"]),
            "label": m["label"],
            "unit": "F",
            "type": "number",
            "decimals": 2,
        }
        for m in members
    ]
    return {"groups": [{"id": "member-forces", "label": "Member Forces", "fields": fields}]}


def _resolve_slot(assignment: Assignment, index: int) -> tuple[int, AssignmentProblem]:
    """Map a 1-based wire index to its 0-based slot and problem row.

    The wire is 1-based (contract: `index minimum: 1`); `order_index`, the
    per-problem seed offset, and draft-answer keys all stay 0-based so existing
    student data keeps generating the same problems.
    """
    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    slot = index - 1
    if slot < 0 or slot >= len(problems_sorted):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem index out of range"
        )
    return slot, problems_sorted[slot]


def _member_key_order(member_solutions: dict[str, Any]) -> list[str]:
    """Return member keys in insertion order (matches generator's member ordering)."""
    return list(member_solutions.keys())


def _check_answers(
    submitted: dict[str, float | None],
    member_solutions: dict[str, Any],
    members: list[dict[str, Any]],
    tolerance: float,
) -> dict[str, bool]:
    """Map S1/S2/... to member_solutions keys and compare signed forces."""
    keys = _member_key_order(member_solutions)
    per_field: dict[str, bool] = {}
    for i, m in enumerate(members):
        sid = member_field_key(m["id"])  # "S1", "S2", ...
        if i >= len(keys):
            per_field[sid] = False
            continue
        true_signed = member_solutions[keys[i]]["signed_force"]
        submitted_val = submitted.get(sid)
        if submitted_val is None:
            per_field[sid] = False
        else:
            delta = abs(float(submitted_val) - true_signed)
            per_field[sid] = delta <= tolerance * max(abs(true_signed), 1.0)
    return per_field


def _problem_summary(
    ap: AssignmentProblem,
    submissions: list[Submission],
) -> dict[str, Any]:
    attempt_count = len(submissions)
    if not submissions:
        prob_status = "no_attempt"
    elif any(s.is_passed for s in submissions):
        prob_status = "correct"
    else:
        prob_status = "incorrect"
    return {
        "index": ap.order_index + 1,
        "problemType": ap.problem_type,
        "status": prob_status,
        "attemptCount": attempt_count,
    }


def _assignment_summary(
    assignment: Assignment,
    student_assignment: StudentAssignment,
    subs_by_problem: dict[uuid.UUID, list[Submission]],
) -> dict[str, Any]:
    problems = [
        _problem_summary(ap, subs_by_problem.get(ap.id, []))
        for ap in sorted(assignment.problems, key=lambda p: p.order_index)
    ]
    locked = bool(student_assignment.submitted_at)
    started = any(p["status"] != "no_attempt" for p in problems)
    assign_status = "submitted" if locked else "in_progress" if started else "not_started"
    score = None
    if locked:
        earned = sum(1 for p in problems if p["status"] == "correct")
        score = {"earned": earned, "total": len(problems)}
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


# ---------------------------------------------------------------------------
# Shared dependency
# ---------------------------------------------------------------------------

async def _get_context(
    slug: str,
    student_id: uuid.UUID = Depends(get_current_student_id),
    db: AsyncSession = Depends(get_db),
) -> tuple[Student, StudentAssignment, Assignment]:
    student_row = await db.execute(select(Student).where(Student.id == student_id))
    student = student_row.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Student not found")

    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.slug == slug)
        .options(selectinload(Assignment.problems))
    )
    assignment = assignment_row.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    sa_row = await db.execute(
        select(StudentAssignment).where(
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment.id,
        )
    )
    sa = sa_row.scalar_one_or_none()
    if sa is None:
        sa = StudentAssignment(
            student_id=student_id,
            assignment_id=assignment.id,
            seed=random.randint(1, 10_000_000),
            draft_answers={},
        )
        db.add(sa)
        await db.flush()

    return student, sa, assignment


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/{slug}")
async def get_assignment(
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    result = await db.execute(
        select(Submission).where(Submission.student_assignment_id == sa.id)
    )
    all_subs = list(result.scalars().all())
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)
    return _assignment_summary(assignment, sa, subs_by_problem)


@router.get("/{slug}/problems/{index}")
async def get_problem(
    index: int,
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    slot, ap = _resolve_slot(assignment, index)

    generator = problem_registry.get(ap.problem_type)
    seed = _effective_seed(sa, slot)
    display = generator.generate(seed=seed, params={"problem_id": index})

    geometry = _build_truss_geometry(display.visual_schema)
    answer_schema = _build_answer_schema(geometry["members"])

    # Fetch attempt count for this problem
    result = await db.execute(
        select(Submission).where(
            Submission.student_assignment_id == sa.id,
            Submission.assignment_problem_id == ap.id,
        )
    )
    subs = list(result.scalars().all())
    attempt_count = len(subs)
    locked = bool(sa.submitted_at)

    saved_answers = (sa.draft_answers or {}).get(str(slot), {})

    return {
        "schemaVersion": 1,
        "index": index,
        "problemType": ap.problem_type,
        "prompt": {
            "title": display.title,
            "body": display.instructions,
            "notes": [],
        },
        "geometry": geometry,
        "answerSchema": answer_schema,
        "savedAnswers": saved_answers,
        "attemptCount": attempt_count,
        "maxAttempts": assignment.max_attempts,
        "locked": locked,
    }


@router.put("/{slug}/problems/{index}/answers")
async def save_answers(
    index: int,
    body: AnswersRequest,
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    if sa.submitted_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assignment is locked")
    slot, _ap = _resolve_slot(assignment, index)
    drafts = dict(sa.draft_answers or {})
    drafts[str(slot)] = body.answers
    sa.draft_answers = drafts
    db.add(sa)
    return {"savedAt": datetime.now(UTC).isoformat()}


@router.post("/{slug}/problems/{index}/check")
async def check_answers(
    index: int,
    body: AnswersRequest,
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    if sa.submitted_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Assignment is locked")

    slot, ap = _resolve_slot(assignment, index)

    generator = problem_registry.get(ap.problem_type)
    seed = _effective_seed(sa, slot)

    display = generator.generate(seed=seed, params={"problem_id": index})
    geometry = _build_truss_geometry(display.visual_schema)
    members = geometry["members"]

    ground_truth = generator.solve(seed=seed, params={"problem_id": index})
    member_solutions = ground_truth["member_solutions"]

    per_field = _check_answers(body.answers, member_solutions, members, assignment.tolerance)
    all_correct = all(per_field.values()) and len(per_field) == len(members)

    result = await db.execute(
        select(Submission).where(
            Submission.student_assignment_id == sa.id,
            Submission.assignment_problem_id == ap.id,
        )
    )
    existing_subs = list(result.scalars().all())
    attempt_number = len(existing_subs) + 1

    submission = Submission(
        student_assignment_id=sa.id,
        assignment_problem_id=ap.id,
        attempt_number=attempt_number,
        answers=dict(body.answers),
        raw_score=1.0 if all_correct else 0.0,
        net_score=1.0 if all_correct else 0.0,
        is_passed=all_correct,
        field_verdicts=dict(per_field),
    )
    db.add(submission)

    if all_correct:
        prob_status = "correct"
        message = "All members correct. Great work!"
    elif attempt_number > 1:
        wrong = sum(1 for v in per_field.values() if not v)
        message = (
            f"{wrong} of {len(members)} members incorrect. "
            "Check your signs and equilibrium equations."
        )
        prob_status = "incorrect"
    else:
        wrong = sum(1 for v in per_field.values() if not v)
        message = f"{wrong} of {len(members)} members incorrect."
        prob_status = "incorrect"

    return {
        "correct": all_correct,
        "perField": per_field,
        "message": message,
        "attemptCount": attempt_number,
        "problemStatus": prob_status,
    }


@router.post("/{slug}/submit")
async def submit_assignment(
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx

    result = await db.execute(
        select(Submission).where(Submission.student_assignment_id == sa.id)
    )
    all_subs = list(result.scalars().all())

    if sa.submitted_at:
        return _build_submission_result(sa, assignment, all_subs)

    sa.submitted_at = datetime.now(UTC)
    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    earned = sum(
        1
        for ap in problems_sorted
        if any(s.is_passed for s in subs_by_problem.get(ap.id, []))
    )
    sa.final_score = float(earned)
    db.add(sa)

    return _build_submission_result(sa, assignment, all_subs)


@router.get("/{slug}/result")
async def get_result(
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    if not sa.submitted_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not submitted yet")

    result = await db.execute(
        select(Submission).where(Submission.student_assignment_id == sa.id)
    )
    all_subs = list(result.scalars().all())
    return _build_submission_result(sa, assignment, all_subs)


def _build_submission_result(
    sa: StudentAssignment,
    assignment: Assignment,
    all_subs: list[Submission],
) -> dict[str, Any]:
    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    problem_results: list[dict[str, Any]] = []
    earned = 0
    for ap in problems_sorted:
        subs = subs_by_problem.get(ap.id, [])
        if not subs:
            prob_status, points = "no_attempt", 0
        elif any(s.is_passed for s in subs):
            prob_status, points = "correct", 1
        else:
            prob_status, points = "incorrect", 0
        earned += points
        problem_results.append(
            {"index": ap.order_index + 1, "status": prob_status, "points": points}
        )

    return {
        "submittedAt": sa.submitted_at.isoformat() if sa.submitted_at else None,
        "score": {"earned": earned, "total": len(problems_sorted)},
        "problems": problem_results,
    }

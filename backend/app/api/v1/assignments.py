import random
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.problems  # noqa: F401 — triggers registry registration
from app.core.security import get_current_student_id
from app.db.models import Assignment, AssignmentProblem, Student, StudentAssignment, Submission
from app.db.session import get_db
from app.problems.registry import problem_registry
from app.services.access import (
    AccessState,
    assert_writable,
    compute_access,
    isoformat_utc,
    lock_reason_for_problem,
    problem_access,
    problem_status,
)
from app.services.scoring import compute_score, resolve_saved_answers

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


# Problem types with a real server-side solver. `beam` and `rigid_body` are
# registered so the assignment builder can list them, but their solve() returns
# no solution -- previously that made every answer grade as wrong forever, and
# an empty geometry would have graded as vacuously correct. Anything not in
# this set is displayable but explicitly not gradeable.
GRADEABLE_TYPES: frozenset[str] = frozenset({"truss"})


def is_gradeable(problem_type: str) -> bool:
    return problem_type in GRADEABLE_TYPES


GRADEABLE_BY_TYPE: dict[str, bool] = {}


def _gradeable_map(assignment: Assignment) -> dict[str, bool]:
    return {ap.problem_type: is_gradeable(ap.problem_type) for ap in assignment.problems}


def _generator_for(ap: AssignmentProblem) -> Any:
    """Look up a problem generator, turning an unknown type into a 404.

    Nothing validates `assignment_problems.problem_type` on the way in, so a
    stale or hand-edited row would otherwise raise KeyError and surface as a
    500 to the student.
    """
    try:
        return problem_registry.get(ap.problem_type)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem type '{ap.problem_type}' is not available",
        ) from exc


def _require_gradeable(ap: AssignmentProblem) -> None:
    """Reject writes to a problem type that has no solver.

    Previously these graded as permanently wrong (no solution to compare
    against), or -- when the geometry produced no fields at all -- as
    vacuously correct. Both are worse than an explicit refusal.
    """
    if not is_gradeable(ap.problem_type):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"Grading is not available for problem type '{ap.problem_type}'",
        )


async def _submissions_for_problem(
    db: AsyncSession, sa: StudentAssignment, ap: AssignmentProblem
) -> list[Submission]:
    result = await db.execute(
        select(Submission).where(
            Submission.student_assignment_id == sa.id,
            Submission.assignment_problem_id == ap.id,
        )
    )
    return list(result.scalars().all())


def _solution_answers(
    generator: Any,
    seed: int,
    params: dict[str, Any],
    members: list[dict[str, Any]],
) -> dict[str, float]:
    """Reference answers keyed exactly like the student's own fields.

    Renaming into S1/S2/... is a second wall behind the reveal gate: no solver
    internals (`member_solutions`, `signed_force`, `magnitude`, `reactions`)
    can reach the wire even through a bug upstream.
    """
    truth = generator.solve(seed=seed, params=params)
    keys = _member_key_order(truth["member_solutions"])
    out: dict[str, float] = {}
    for i, m in enumerate(members):
        if i < len(keys):
            out[member_field_key(m["id"])] = float(
                truth["member_solutions"][keys[i]]["signed_force"]
            )
    return out


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
            members.append(
                {
                    "id": member_idx,
                    "from": int(p["start_node"]) + 1,
                    "to": int(p["end_node"]) + 1,
                    "label": _member_label(member_idx),
                }
            )
        elif t in ("pin", "roller"):
            supports.append(
                {
                    "node": int(p["node_index"]) + 1,
                    "type": t,
                    # Pins always sit base-down; rollers carry an outward rotation.
                    "angleDeg": int(p.get("rotation", 0)),
                }
            )
        elif t == "point_load":
            fv = p["force_vector"]
            mag = (fv[0] ** 2 + fv[1] ** 2) ** 0.5
            forces.append(
                {
                    "node": int(p["node_index"]) + 1,
                    "fx": float(fv[0]),
                    "fy": float(fv[1]),
                    "label": f"{mag:.1f}F",
                }
            )

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


def _generator_params(ap: AssignmentProblem, index: int) -> dict[str, Any]:
    """Build the generator params for a problem slot.

    `problem_id` (the 1-based wire index) only seeds the legacy
    `[3,3,4,4,5,5,6,6]` node-count schedule as a fallback. Stored
    `assignment_problems.params` come last so they win — that column is the
    source of truth for problem configuration (ADR 0015), and until now it was
    written by the seed but never read.
    """
    return {"problem_id": index, **(ap.params or {})}


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
    state: AccessState,
) -> dict[str, Any]:
    return {
        "index": ap.order_index + 1,
        "problemType": ap.problem_type,
        "status": problem_status(submissions),
        "attemptCount": len(submissions),
        "locked": problem_access(state, submissions) != "editable",
    }


def _assignment_summary(
    assignment: Assignment,
    student_assignment: StudentAssignment,
    subs_by_problem: dict[uuid.UUID, list[Submission]],
    state: AccessState | None = None,
) -> dict[str, Any]:
    if state is None:
        state = compute_access(assignment, student_assignment)

    problems = [
        _problem_summary(ap, subs_by_problem.get(ap.id, []), state)
        for ap in sorted(assignment.problems, key=lambda p: p.order_index)
    ]
    started = any(p["status"] != "no_attempt" for p in problems)

    # `submitted` and `closed` are both final, but they are not the same fact:
    # only one of them means the student actually pressed Submit.
    if state.close_reason == "submitted":
        assign_status = "submitted"
    elif state.closed:
        assign_status = "closed"
    elif started:
        assign_status = "in_progress"
    else:
        assign_status = "not_started"

    score = None
    if state.closed:
        breakdown = compute_score(assignment.problems, subs_by_problem, _gradeable_map(assignment))
        score = {"earned": breakdown.earned, "total": breakdown.total}

    return {
        "slug": assignment.slug,
        "title": assignment.title,
        "problemCount": len(problems),
        "status": assign_status,
        "feedbackMode": assignment.feedback_mode,
        "maxAttempts": assignment.max_attempts,
        "dueAt": isoformat_utc(assignment.due_at),
        "locked": state.closed,
        "lockReason": state.close_reason,
        "closesAt": isoformat_utc(state.closes_at),
        "revealSolutions": state.reveal_solutions,
        "problems": problems,
        "score": score,
    }


async def _finalize_if_closed(
    db: AsyncSession,
    assignment: Assignment,
    sa: StudentAssignment,
    subs_by_problem: dict[uuid.UUID, list[Submission]],
    state: AccessState,
) -> None:
    """Stamp a deadline-closed session with its final score.

    Lazy, on read: there is no scheduler in this stack, and adding one for a
    single row update is not worth a new dependency. Convergence is guaranteed
    because the student summary, the result page and the instructor gradebook
    all call this.

    `submitted_at` is deliberately left alone -- the student never submitted,
    and telling the instructor otherwise would be a lie. `finalized_at` carries
    the deadline instant rather than "now", so two concurrent requests compute
    an identical value and the guarded UPDATE makes the write single-shot.
    """
    if state.close_reason != "past_due" or sa.finalized_at is not None:
        return

    breakdown = compute_score(assignment.problems, subs_by_problem, _gradeable_map(assignment))
    closed_at = state.closes_at

    result = await db.execute(
        update(StudentAssignment)
        .where(
            StudentAssignment.id == sa.id,
            StudentAssignment.finalized_at.is_(None),
            StudentAssignment.submitted_at.is_(None),
        )
        .values(finalized_at=closed_at, final_score=breakdown.earned)
        .execution_options(synchronize_session=False)
    )
    # CursorResult exposes rowcount; the Result base class does not.
    if cast("CursorResult[Any]", result).rowcount:
        sa.finalized_at = closed_at
        sa.final_score = breakdown.earned
    else:
        await db.refresh(sa)


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
        select(Assignment).where(Assignment.slug == slug).options(selectinload(Assignment.problems))
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
    result = await db.execute(select(Submission).where(Submission.student_assignment_id == sa.id))
    all_subs = list(result.scalars().all())
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    state = compute_access(assignment, sa)
    await _finalize_if_closed(db, assignment, sa, subs_by_problem, state)
    return _assignment_summary(assignment, sa, subs_by_problem, state)


@router.get("/{slug}/problems/{index}")
async def get_problem(
    index: int,
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    slot, ap = _resolve_slot(assignment, index)

    generator = _generator_for(ap)
    seed = _effective_seed(sa, slot)
    params = _generator_params(ap, index)
    display = generator.generate(seed=seed, params=params)

    result = await db.execute(
        select(Submission).where(
            Submission.student_assignment_id == sa.id,
            Submission.assignment_problem_id == ap.id,
        )
    )
    subs = list(result.scalars().all())

    state = compute_access(assignment, sa)

    if not is_gradeable(ap.problem_type):
        # Displayable but unanswerable. Returning 200 with an empty answer
        # schema keeps one unimplemented slot from breaking the whole review
        # page; the write routes reject it explicitly with a 501.
        return {
            "schemaVersion": 1,
            "index": index,
            "problemType": ap.problem_type,
            "prompt": {"title": display.title, "body": display.instructions, "notes": []},
            "geometry": None,
            "answerSchema": {"groups": []},
            "savedAnswers": {},
            "attemptCount": len(subs),
            "maxAttempts": assignment.max_attempts,
            "locked": True,
            "lockReason": "unavailable",
            "correctAnswers": None,
        }

    geometry = _build_truss_geometry(display.visual_schema)
    answer_schema = _build_answer_schema(geometry["members"])
    field_keys = [f["key"] for g in answer_schema["groups"] for f in g["fields"]]

    access = problem_access(state, subs)
    saved_answers = resolve_saved_answers(slot, sa.draft_answers, subs, access, field_keys)

    # The single choke point for solution data on a student route. Building it
    # is gated on the assignment being closed AND the instructor opting in;
    # every other path never calls solve() at all.
    correct_answers: dict[str, float] | None = None
    if state.reveal_solutions:
        correct_answers = _solution_answers(generator, seed, params, geometry["members"])

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
        "attemptCount": len(subs),
        "maxAttempts": assignment.max_attempts,
        "locked": access != "editable",
        "lockReason": lock_reason_for_problem(state, access),
        "correctAnswers": correct_answers,
    }


@router.put("/{slug}/problems/{index}/answers")
async def save_answers(
    index: int,
    body: AnswersRequest,
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx
    slot, ap = _resolve_slot(assignment, index)
    _require_gradeable(ap)

    subs = await _submissions_for_problem(db, sa, ap)
    assert_writable(problem_access(compute_access(assignment, sa), subs))

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
    slot, ap = _resolve_slot(assignment, index)
    _require_gradeable(ap)

    existing_subs = await _submissions_for_problem(db, sa, ap)
    assert_writable(problem_access(compute_access(assignment, sa), existing_subs))

    generator = _generator_for(ap)
    seed = _effective_seed(sa, slot)
    params = _generator_params(ap, index)

    display = generator.generate(seed=seed, params=params)
    geometry = _build_truss_geometry(display.visual_schema)
    members = geometry["members"]

    # Same seed and same params as generate(), or the student would be graded
    # against a different truss than the one they were shown.
    ground_truth = generator.solve(seed=seed, params=params)
    member_solutions = ground_truth["member_solutions"]

    per_field = _check_answers(body.answers, member_solutions, members, assignment.tolerance)
    # `len(per_field) > 0` matters: with no fields, all({}) is vacuously True
    # and the problem would grade as fully correct without an answer.
    all_correct = len(per_field) > 0 and all(per_field.values()) and len(per_field) == len(members)

    if assignment.max_attempts is not None and len(existing_subs) >= assignment.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have exceeded the maximum number of attempts.",
        )

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

    # Checking is also saving. Without this a student who checks but never
    # presses "Save Progress" loses the answer on reload, because savedAnswers
    # reads the draft blob and check only ever wrote the submission row.
    # Copy-then-reassign: draft_answers is a plain JSON column, so in-place
    # mutation is not tracked and would silently not persist.
    drafts = dict(sa.draft_answers or {})
    drafts[str(slot)] = dict(body.answers)
    sa.draft_answers = drafts
    db.add(sa)

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

    result = await db.execute(select(Submission).where(Submission.student_assignment_id == sa.id))
    all_subs = list(result.scalars().all())

    if sa.submitted_at:
        return _build_submission_result(sa, assignment, all_subs)

    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    now = datetime.now(UTC)
    breakdown = compute_score(assignment.problems, subs_by_problem, _gradeable_map(assignment))
    sa.submitted_at = now
    sa.finalized_at = now
    sa.final_score = breakdown.earned
    db.add(sa)

    return _build_submission_result(sa, assignment, all_subs)


@router.get("/{slug}/result")
async def get_result(
    ctx: tuple[Student, StudentAssignment, Assignment] = Depends(_get_context),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _, sa, assignment = ctx

    result = await db.execute(select(Submission).where(Submission.student_assignment_id == sa.id))
    all_subs = list(result.scalars().all())
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    state = compute_access(assignment, sa)
    if not state.closed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not submitted yet")

    # A deadline-closed assignment has a result even though nobody submitted.
    await _finalize_if_closed(db, assignment, sa, subs_by_problem, state)
    return _build_submission_result(sa, assignment, all_subs)


def _build_submission_result(
    sa: StudentAssignment,
    assignment: Assignment,
    all_subs: list[Submission],
) -> dict[str, Any]:
    subs_by_problem: dict[uuid.UUID, list[Submission]] = {}
    for s in all_subs:
        subs_by_problem.setdefault(s.assignment_problem_id, []).append(s)

    breakdown = compute_score(assignment.problems, subs_by_problem, _gradeable_map(assignment))

    return {
        # Falls back to finalized_at so a deadline-closed assignment reports
        # when it closed rather than a bare null.
        "submittedAt": isoformat_utc(sa.submitted_at or sa.finalized_at),
        "score": {"earned": breakdown.earned, "total": breakdown.total},
        "problems": [
            {"index": p.index, "status": p.status, "points": p.earned} for p in breakdown.problems
        ],
    }

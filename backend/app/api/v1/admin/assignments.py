"""Assignment builder, polymorphic problem slot management, and preview endpoints."""

import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.admin.helpers import (
    _admin_assignment_detail,
    _admin_assignment_summary,
)
from app.db.models import (
    Assignment,
    AssignmentProblem,
    AssignmentTarget,
    Course,
    Instructor,
)
from app.db.session import get_db
from app.api.v1.assignments import GRADEABLE_TYPES
from app.problems.registry import problem_registry
from app.services.problem_display import build_display_payload
from app.schemas.admin import (
    AssignmentCreateRequest,
    AssignmentUpdateRequest,
    PublishAssignmentRequest,
    _assert_date_order,
)
from app.services.authz import assert_course_role, require_instructor

router = APIRouter(tags=["admin-assignments"])


@router.get("/problem-types", summary="List registered problem domain generators")
async def list_problem_types(
    _instructor: Instructor = Depends(require_instructor),
) -> list[dict[str, Any]]:
    """Retrieve catalog of available problem types, display names, and parameter schemas."""
    result: list[dict[str, Any]] = []
    for p_type in problem_registry.list_types():
        if p_type not in GRADEABLE_TYPES:
            continue
        gen = problem_registry.get(p_type)
        result.append(
            {
                "problemType": gen.problem_type,
                "displayName": gen.display_name,
                "paramsSchema": [
                    {
                        "name": s.name,
                        "label": s.label,
                        # Contract key is `valueType`; this used to emit `type`,
                        # so the builder never saw it and fell back to step="any".
                        "valueType": s.value_type,
                        "default": s.default,
                        "minimum": s.minimum,
                        "maximum": s.maximum,
                        "step": s.step,
                        "helpText": s.help_text,
                        "options": (
                            [{"value": o.value, "label": o.label} for o in s.options]
                            if s.options
                            else None
                        ),
                    }
                    for s in gen.params_schema
                ],
            }
        )
    return result


@router.get("/courses/{course_id}/assignments", summary="List assignments in a course")
async def list_course_assignments(
    course_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Retrieve all assignments (published and draft) for a course section."""
    await assert_course_role(db, course_id, instructor, minimum="reader")
    assignments = (
        (
            await db.execute(
                select(Assignment)
                .where(Assignment.course_id == course_id)
                .options(selectinload(Assignment.problems))
                .order_by(Assignment.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

    return [_admin_assignment_summary(a) for a in assignments]


@router.post(
    "/courses/{course_id}/assignments",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new assignment",
)
async def create_assignment(
    course_id: uuid.UUID,
    body: AssignmentCreateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new homework assignment with problem slots and targeting."""
    await assert_course_role(db, course_id, instructor, minimum="ta")

    course = (await db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    # Generate slug if omitted
    slug = body.slug
    if not slug:
        clean_title = re.sub(r"[^\w\s-]", "", body.title).strip().lower()
        base_slug = re.sub(r"[-\s]+", "-", clean_title)
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # Check slug collision
    existing = (
        await db.execute(select(Assignment).where(Assignment.slug == slug))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment with this slug already exists",
        )

    assignment = Assignment(
        course_id=course_id,
        slug=slug,
        title=body.title.strip(),
        instructions=body.instructions.strip(),
        tolerance=body.tolerance,
        feedback_mode=body.feedbackMode,
        max_attempts=body.maxAttempts,
        penalty_per_attempt=body.penaltyPerAttempt,
        scoring_strategy=body.scoringStrategy,
        allow_late=body.allowLate,
        late_penalty_rate=body.latePenaltyRate,
        opens_at=body.opensAt,
        due_at=body.dueAt,
        hard_deadline_at=body.hardDeadlineAt,
        reveal_solutions_after_close=body.revealSolutionsAfterClose,
        is_published=False,
        audience=body.audience,
    )
    db.add(assignment)
    await db.flush()

    # Add problem slots
    for idx, slot_spec in enumerate(body.problems):
        prob = AssignmentProblem(
            assignment_id=assignment.id,
            order_index=slot_spec.orderIndex - 1 if slot_spec.orderIndex > 0 else idx,
            problem_type=slot_spec.problemType,
            params=slot_spec.params,
            points=slot_spec.points,
        )
        db.add(prob)

    # Add targeted audience if selected
    if body.audience == "selected" and body.targetEntryIds:
        for entry_id_str in body.targetEntryIds:
            try:
                e_uuid = uuid.UUID(entry_id_str)
                target = AssignmentTarget(
                    assignment_id=assignment.id,
                    roster_entry_id=e_uuid,
                )
                db.add(target)
            except ValueError:
                continue

    await db.commit()

    # Reload with relationships
    assignment_reloaded = (
        await db.execute(
            select(Assignment)
            .where(Assignment.id == assignment.id)
            .options(
                selectinload(Assignment.problems),
                selectinload(Assignment.targets),
            )
        )
    ).scalar_one()

    return _admin_assignment_detail(assignment_reloaded)


@router.get("/assignments/{assignment_id}", summary="Get assignment builder details")
async def get_assignment(
    assignment_id: uuid.UUID,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve full configuration and problem slots for an assignment."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")
    return _admin_assignment_detail(assignment)


@router.patch(
    "/assignments/{assignment_id}",
    summary="Update assignment settings and problem slots",
)
async def update_assignment(
    assignment_id: uuid.UUID,
    body: AssignmentUpdateRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update settings, audience targets, and problem slots for an assignment."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="ta")

    if body.title is not None:
        assignment.title = body.title.strip()
    if body.slug is not None:
        new_slug = body.slug.strip()
        if new_slug != assignment.slug:
            existing = (
                await db.execute(
                    select(Assignment).where(
                        Assignment.slug == new_slug,
                        Assignment.id != assignment.id,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Assignment slug already taken",
                )
            assignment.slug = new_slug
    if body.instructions is not None:
        assignment.instructions = body.instructions.strip()
    if body.tolerance is not None:
        assignment.tolerance = body.tolerance
    if body.feedbackMode is not None:
        assignment.feedback_mode = body.feedbackMode
    if body.maxAttempts is not None:
        assignment.max_attempts = body.maxAttempts
    if body.penaltyPerAttempt is not None:
        assignment.penalty_per_attempt = body.penaltyPerAttempt
    if body.scoringStrategy is not None:
        assignment.scoring_strategy = body.scoringStrategy
    if body.allowLate is not None:
        assignment.allow_late = body.allowLate
    if body.latePenaltyRate is not None:
        assignment.late_penalty_rate = body.latePenaltyRate
    if body.revealSolutionsAfterClose is not None:
        assignment.reveal_solutions_after_close = body.revealSolutionsAfterClose

    # Dates use model_fields_set, not an is-not-None test: an explicit null has
    # to be able to clear a deadline, and "omitted" and "null" are different
    # requests. The is-not-None idiom used above cannot express that.
    for wire_name, column in (
        ("opensAt", "opens_at"),
        ("dueAt", "due_at"),
        ("hardDeadlineAt", "hard_deadline_at"),
    ):
        if wire_name in body.model_fields_set:
            setattr(assignment, column, getattr(body, wire_name))

    # Validate against the merged row: a PATCH sending only dueAt still has to
    # agree with the hard deadline already stored.
    try:
        _assert_date_order(assignment.opens_at, assignment.due_at, assignment.hard_deadline_at)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if body.audience is not None:
        assignment.audience = body.audience

    if body.targetEntryIds is not None:
        assignment.targets.clear()
        await db.flush()
        for entry_id_str in body.targetEntryIds:
            try:
                e_uuid = uuid.UUID(entry_id_str)
                assignment.targets.append(
                    AssignmentTarget(
                        assignment_id=assignment.id,
                        roster_entry_id=e_uuid,
                    )
                )
            except ValueError:
                continue

    if body.problems is not None:
        assignment.problems.clear()
        await db.flush()
        for idx, slot_spec in enumerate(body.problems):
            assignment.problems.append(
                AssignmentProblem(
                    assignment_id=assignment.id,
                    order_index=slot_spec.orderIndex - 1 if slot_spec.orderIndex > 0 else idx,
                    problem_type=slot_spec.problemType,
                    params=slot_spec.params,
                    points=slot_spec.points,
                )
            )

    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return _admin_assignment_detail(assignment)


@router.patch(
    "/assignments/{assignment_id}/publish",
    summary="Toggle assignment published state",
)
@router.post(
    "/assignments/{assignment_id}/publish",
    summary="Toggle assignment published state",
)
async def set_assignment_published(
    assignment_id: uuid.UUID,
    body: PublishAssignmentRequest,
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Publish or unpublish an assignment. Publishing requires at least 1 problem."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(
            selectinload(Assignment.problems),
            selectinload(Assignment.targets),
        )
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="instructor")

    # Invariant: Cannot publish an assignment with 0 problems
    if body.isPublished and len(assignment.problems) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish an assignment with 0 problems",
        )

    assignment.is_published = body.isPublished
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return _admin_assignment_detail(assignment)


@router.get(
    "/assignments/{assignment_id}/preview/{index}",
    summary="Preview problem payload for instructor",
)
async def preview_assignment_problem(
    assignment_id: uuid.UUID,
    index: int,
    seed: int = Query(default=1),
    instructor: Instructor = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Generate problem display payload without saving answers or leaking solutions."""
    assignment_row = await db.execute(
        select(Assignment)
        .where(Assignment.id == assignment_id)
        .options(selectinload(Assignment.problems))
    )
    assignment = assignment_row.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    await assert_course_role(db, assignment.course_id, instructor, minimum="reader")

    problems_sorted = sorted(assignment.problems, key=lambda p: p.order_index)
    slot = index - 1
    if slot < 0 or slot >= len(problems_sorted):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Problem index out of range"
        )

    ap = problems_sorted[slot]
    generator = problem_registry.get(ap.problem_type)
    params = {"problem_id": index, **(ap.params or {})}
    display = generator.generate(seed=seed, params=params)

    geometry, answer_schema = build_display_payload(ap.problem_type, display)

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
        "savedAnswers": {},
        "attemptCount": 0,
        "maxAttempts": assignment.max_attempts,
        "locked": False,
    }

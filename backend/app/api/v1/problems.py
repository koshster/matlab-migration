import random
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

import app.problems  # noqa: F401
from app.core.security import get_current_student_id
from app.problems.base import ProblemDisplayData
from app.problems.registry import problem_registry

# These are introspection/debug routes, not part of the student workflow. They
# require a session so they are not open to the internet; Phase C should move
# them behind instructor auth, since only the admin builder needs them.
router = APIRouter(prefix="/problems", tags=["problems"])


class GenerateProblemRequest(BaseModel):
    """Request payload to synthesize a problem instance."""

    seed: int | None = Field(
        default=None,
        description="Optional integer seed; if omitted, a random seed is chosen",
    )
    params: dict[str, Any] | None = Field(
        default=None, description="Optional problem configuration parameters"
    )


@router.get("/types", summary="List all supported problem types")
async def list_problem_types(
    _student_id: uuid.UUID = Depends(get_current_student_id),
) -> dict[str, list[str]]:
    """Returns a list of all problem domain generators currently registered."""
    return {"problem_types": problem_registry.list_types()}


@router.post(
    "/{problem_type}/generate",
    response_model=ProblemDisplayData,
    summary="Generate problem geometry and input schema",
)
async def generate_problem(
    problem_type: str,
    request: GenerateProblemRequest | None = None,
    _student_id: uuid.UUID = Depends(get_current_student_id),
) -> ProblemDisplayData:
    """Generate problem visual elements and form input fields without exposing solutions."""
    try:
        generator = problem_registry.get(problem_type)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Problem type '{problem_type}' not found. "
                f"Available types: {problem_registry.list_types()}"
            ),
        ) from exc

    seed = request.seed if (request and request.seed is not None) else random.randint(1, 1_000_000)
    params = request.params if request else None

    return generator.generate(seed=seed, params=params)


# NOTE: there is deliberately no `POST /{problem_type}/check` route.
# Grading a caller-supplied (seed, answers) pair is an answer oracle: it reports
# per-field correctness without recording an attempt, so answers can be
# brute-forced one member at a time. Real grading goes through
# `POST /assignments/{slug}/problems/{index}/check`, which is scoped to the
# student's own seed and writes a Submission row. `TrussGenerator.check` is
# still covered directly in tests/test_problems.py.

from typing import Any
import random
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.problems.base import (
    AnswerSubmission,
    GradingResult,
    ProblemDisplayData,
)
from app.problems.registry import problem_registry
import app.problems  # noqa: F401


router = APIRouter(prefix="/problems", tags=["problems"])


class GenerateProblemRequest(BaseModel):
    """Request payload to synthesize a problem instance."""

    seed: int | None = Field(
        default=None, description="Optional integer seed; if omitted, a random seed is chosen"
    )
    params: dict[str, Any] | None = Field(
        default=None, description="Optional problem configuration parameters"
    )


class CheckAnswerRequest(BaseModel):
    """Request payload to grade a student submission."""

    seed: int = Field(..., description="Integer seed corresponding to the problem instance")
    answers: dict[str, Any] = Field(
        ..., description="Dictionary mapping field_id to submitted value"
    )
    tolerance: float = Field(
        default=0.01, description="Acceptable relative grading tolerance (default: 0.01 = 1%)"
    )


@router.get("/types", summary="List all supported problem types")
async def list_problem_types() -> dict[str, list[str]]:
    """Returns a list of all problem domain generators currently registered."""
    return {"problem_types": problem_registry.list_types()}


@router.post(
    "/{problem_type}/generate",
    response_model=ProblemDisplayData,
    summary="Generate problem geometry and input schema",
)
async def generate_problem(
    problem_type: str, request: GenerateProblemRequest | None = None
) -> ProblemDisplayData:
    """Generate problem visual elements and form input fields from seed without exposing solutions."""
    try:
        generator = problem_registry.get(problem_type)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem type '{problem_type}' not found. Available types: {problem_registry.list_types()}",
        ) from exc

    seed = request.seed if (request and request.seed is not None) else random.randint(1, 1_000_000)
    params = request.params if request else None

    return generator.generate(seed=seed, params=params)


@router.post(
    "/{problem_type}/check",
    response_model=GradingResult,
    summary="Evaluate student answers against ground truth",
)
async def check_problem_answer(
    problem_type: str, request: CheckAnswerRequest
) -> GradingResult:
    """Statelessly solve the problem server-side using the seed and grade the student's submission."""
    try:
        generator = problem_registry.get(problem_type)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem type '{problem_type}' not found.",
        ) from exc

    submission = AnswerSubmission(answers=request.answers)
    return generator.check(
        seed=request.seed, submission=submission, tolerance=request.tolerance
    )

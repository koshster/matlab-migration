"""Instructor-facing admin routes.

Only the problem-type catalogue is implemented here. Courses, rosters and
assignment persistence need the Phase B migration (course_instructors, a
nullable roster student_id, assignment_targets), so those endpoints are
specified in openapi.yaml and served by MSW on the client until the schema
lands.

This endpoint exists now because the assignment builder renders its difficulty
form from it. Hardcoding truss fields in the admin UI would break the registry
invariant on day one (CLAUDE.md), and the catalogue is derivable from the
generator registry alone — no schema change required.
"""

from typing import Any

from fastapi import APIRouter, Depends

import app.problems  # noqa: F401 — triggers generator registration
from app.db.models import Instructor
from app.problems.registry import problem_registry
from app.services.authz import require_instructor

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/problem-types", summary="Problem types and their configurable params")
async def list_problem_types(
    _instructor: Instructor = Depends(require_instructor),
) -> list[dict[str, Any]]:
    return [
        {
            "problemType": generator.problem_type,
            "displayName": generator.display_name,
            "paramsSchema": [
                {
                    "name": field.name,
                    "label": field.label,
                    "valueType": field.value_type,
                    "default": field.default,
                    "minimum": field.minimum,
                    "maximum": field.maximum,
                    "step": field.step,
                    "helpText": field.help_text,
                }
                for field in generator.params_schema
            ],
        }
        for generator in problem_registry.all()
    ]

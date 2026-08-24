"""Beam reaction and internal shear/moment problem domain generator stub.

Provides the seam for future beam statics problems.
"""

from typing import Any

from app.problems.base import (
    AnswerFieldSpec,
    AnswerSubmission,
    GradingResult,
    ParamFieldSpec,
    ProblemDisplayData,
    VisualElementSchema,
)
from app.problems.registry import problem_registry


class BeamGenerator:
    """Simply supported and cantilever beam problem generator stub."""

    @property
    def problem_type(self) -> str:
        """Domain identifier string."""
        return "beam"

    @property
    def display_name(self) -> str:
        """Human readable name for UI assignment builder."""
        return "Beam Reactions & Loadings"

    @property
    def params_schema(self) -> list[ParamFieldSpec]:
        """Configurable difficulty knobs for beam problems."""
        return [
            ParamFieldSpec(
                name="span_length",
                label="Span length (m)",
                value_type="integer",
                default=6,
                minimum=2,
                maximum=12,
                step=1,
                help_text="Total span length of the beam.",
            ),
            ParamFieldSpec(
                name="load_type",
                label="Loading configuration",
                value_type="integer",
                default=1,
                minimum=1,
                maximum=3,
                step=1,
                help_text="1: Point loads, 2: Uniformly distributed load, 3: Combined.",
            ),
        ]

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize placeholder display data for beam problems."""
        return ProblemDisplayData(
            problem_type=self.problem_type,
            seed=seed,
            title="Beam Reactions (Upcoming)",
            instructions=(
                "Determine the support reactions and internal shear force / bending moments."
            ),
            visual_schema=[
                VisualElementSchema(
                    element_type="node",
                    properties={"id": 0, "x": 0.0, "y": 0.0},
                ),
                VisualElementSchema(
                    element_type="node",
                    properties={"id": 1, "x": 6.0, "y": 0.0},
                ),
                VisualElementSchema(
                    element_type="member",
                    properties={"id": "Beam_0_1", "start_node": 0, "end_node": 1},
                ),
            ],
            answer_schema=[
                AnswerFieldSpec(
                    field_id="reaction_Ay",
                    label="Ay (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_By",
                    label="By (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
            ],
        )

    def solve(self, seed: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Ground truth solver stub for beam problems."""
        return {
            "reactions": {"Ay": 0.0, "By": 0.0},
            "member_solutions": {},
        }

    def check(
        self,
        seed: int,
        submission: AnswerSubmission,
        tolerance: float = 0.01,
        params: dict[str, Any] | None = None,
    ) -> GradingResult:
        """Evaluate submission against solver stub."""
        return GradingResult(
            is_passed=True,
            score=1.0,
            field_results={},
        )


beam_generator = BeamGenerator()
problem_registry.register(beam_generator)

"""Rigid body problem domain generator stub implementing ProblemGeneratorProtocol.

Provides the seam for future 2D rigid body equilibrium problems.
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


class RigidBodyGenerator:
    """2D Rigid Body equilibrium problem generator stub."""

    @property
    def problem_type(self) -> str:
        """Domain identifier string."""
        return "rigid_body"

    @property
    def display_name(self) -> str:
        """Human readable name for UI assignment builder."""
        return "2D Rigid Body Equilibrium"

    @property
    def params_schema(self) -> list[ParamFieldSpec]:
        """Configurable difficulty knobs for rigid body problems."""
        return [
            ParamFieldSpec(
                name="body_shape",
                label="Geometry type",
                value_type="integer",
                default=1,
                minimum=1,
                maximum=3,
                step=1,
                help_text="Body geometry template (1: L-bracket, 2: T-frame, 3: Angled bar).",
            ),
            ParamFieldSpec(
                name="num_loads",
                label="Applied forces / moments",
                value_type="integer",
                default=2,
                minimum=1,
                maximum=4,
                step=1,
                help_text="Number of external force and moment vectors applied to the body.",
            ),
        ]

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize placeholder display data for rigid body problems."""
        return ProblemDisplayData(
            problem_type=self.problem_type,
            seed=seed,
            title="2D Rigid Body Equilibrium (Upcoming)",
            instructions=(
                "Determine the unknown support reactions for the rigid body in static equilibrium."
            ),
            visual_schema=[
                VisualElementSchema(
                    element_type="node",
                    properties={"id": 0, "x": 0.0, "y": 0.0},
                ),
                VisualElementSchema(
                    element_type="node",
                    properties={"id": 1, "x": 4.0, "y": 0.0},
                ),
                VisualElementSchema(
                    element_type="member",
                    properties={"id": "RB_0_1", "start_node": 0, "end_node": 1},
                ),
            ],
            answer_schema=[
                AnswerFieldSpec(
                    field_id="reaction_Ax",
                    label="Ax (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_Ay",
                    label="Ay (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_B",
                    label="B (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
            ],
        )

    def solve(self, seed: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Ground truth solver stub for rigid body problems."""
        return {
            "reactions": {"Ax": 0.0, "Ay": 0.0, "B": 0.0},
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


rigid_body_generator = RigidBodyGenerator()
problem_registry.register(rigid_body_generator)

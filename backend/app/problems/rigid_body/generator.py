"""2D Rigid Body equilibrium problem domain generator implementing ProblemGeneratorProtocol.

Generates random planar rigid bodies on integer grids with static boundary supports
(Pin + Roller, 3 Rollers, or Fixed Wall) and external loads, solves global equilibrium
reactions server-side, and grades student numerical submissions with tolerance verification.
"""

from typing import Any

import numpy as np

from app.problems.base import (
    AnswerFieldSpec,
    AnswerSubmission,
    FieldResult,
    GradingResult,
    ParamFieldSpec,
    ProblemDisplayData,
    VisualElementSchema,
)
from app.problems.registry import problem_registry
from app.problems.rigid_body.geometry import generate_rigid_body_geometry
from app.problems.rigid_body.loads import generate_loads
from app.problems.rigid_body.solver import solve_rigid_body_reactions
from app.problems.rigid_body.supports import generate_supports


class RigidBodyGenerator:
    """2D Rigid Body equilibrium problem domain generator and grader."""

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
        """Configurable difficulty knobs for rigid body equilibrium problems."""
        return [
            ParamFieldSpec(
                name="support_case",
                label="Support Configuration",
                value_type="integer",
                default=2,
                minimum=1,
                maximum=3,
                step=1,
                help_text="1: 3 Rollers, 2: Pin + Roller (default), 3: Fixed Cantilever Wall.",
            ),
            ParamFieldSpec(
                name="num_loads",
                label="Applied forces",
                value_type="integer",
                default=2,
                minimum=1,
                maximum=4,
                step=1,
                help_text="Number of external point forces applied to the rigid body.",
            ),
            ParamFieldSpec(
                name="num_moments",
                label="Applied couple moments",
                value_type="integer",
                default=0,
                minimum=0,
                maximum=2,
                step=1,
                help_text="Number of concentrated couple moments applied to the rigid body.",
            ),
            ParamFieldSpec(
                name="max_force",
                label="Max load magnitude (kN)",
                value_type="integer",
                default=5,
                minimum=1,
                maximum=20,
                step=1,
                help_text="Upper bound for applied point load magnitudes.",
            ),
        ]

    def _build_instance(
        self, seed: int, params: dict[str, Any] | None = None
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        np.ndarray,
        dict[str, list[dict[str, Any]]],
        dict[str, list[dict[str, Any]]],
    ]:
        rng = np.random.default_rng(seed)
        p = params or {}

        support_case = int(p.get("support_case", 2))
        if support_case not in (1, 2, 3):
            support_case = 2

        n_forces = int(p.get("num_loads", 2))
        n_moments = int(p.get("num_moments", 0))
        max_force = float(p.get("max_force", 5.0))

        # Loop until an admissible determinate configuration is synthesized
        for _ in range(50):
            path_nodes, unique_nodes, surroundings = generate_rigid_body_geometry(
                min_nodes=5, rng=rng
            )
            supports, free_nodes, free_surr, is_invalid = generate_supports(
                unique_nodes, surroundings, support_case=support_case, rng=rng
            )
            if not is_invalid and len(free_nodes) >= max(1, n_forces):
                loads = generate_loads(
                    free_nodes,
                    free_surr,
                    rng,
                    n_forces=n_forces,
                    n_moments=n_moments,
                    max_force=max_force,
                )
                return path_nodes, unique_nodes, surroundings, supports, loads

        # Deterministic fallback
        path_nodes, unique_nodes, surroundings = generate_rigid_body_geometry(
            min_nodes=5, rng=rng, max_attempts=1
        )
        supports, free_nodes, free_surr, _ = generate_supports(
            unique_nodes, surroundings, support_case=2, rng=rng
        )
        loads = generate_loads(
            free_nodes, free_surr, rng, n_forces=1, n_moments=0, max_force=5.0
        )
        return path_nodes, unique_nodes, surroundings, supports, loads

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize problem geometry and display schema. NEVER return solution data."""
        path_nodes, unique_nodes, _surroundings, supports, loads = self._build_instance(
            seed, params
        )

        visual_schema: list[VisualElementSchema] = []

        # Continuous rigid body path
        visual_schema.append(
            VisualElementSchema(
                element_type="rigid_body_path",
                properties={"path": path_nodes.tolist()},
            )
        )

        # Unique joints / nodes
        for idx, pos in enumerate(unique_nodes):
            visual_schema.append(
                VisualElementSchema(
                    element_type="node",
                    properties={"id": idx, "x": float(pos[0]), "y": float(pos[1])},
                )
            )

        # Supports
        for pin in supports.get("fixed_pins", []):
            visual_schema.append(
                VisualElementSchema(
                    element_type="pin",
                    properties={
                        "position": pin["r"],
                        "rotation": pin.get("rotation", 0),
                        "label": pin.get("label", "A"),
                    },
                )
            )

        for roller in supports.get("rollers", []):
            visual_schema.append(
                VisualElementSchema(
                    element_type="roller",
                    properties={
                        "position": roller["r"],
                        "rotation": roller.get("rotation", 0),
                        "label": roller.get("label", "B"),
                    },
                )
            )

        for wall in supports.get("walls", []):
            visual_schema.append(
                VisualElementSchema(
                    element_type="wall",
                    properties={
                        "position": wall["r"],
                        "rotation": wall.get("rotation", 0),
                        "label": wall.get("label", "A"),
                    },
                )
            )

        # Applied Point Loads
        for f in loads.get("forces", []):
            visual_schema.append(
                VisualElementSchema(
                    element_type="point_load",
                    properties={
                        "position": f["P"],
                        "force_vector": f["F"],
                        "magnitude": f["magnitude"],
                        "label": f["label"],
                    },
                )
            )

        # Concentrated Moments
        for m in loads.get("moments", []):
            visual_schema.append(
                VisualElementSchema(
                    element_type="moment",
                    properties={
                        "position": m["P"],
                        "magnitude": m["magnitude"],
                        "direction": m["direction"],
                        "arrow_angle": m["arrow_angle"],
                        "arc_angle": m["arc_angle"],
                        "label": m["label"],
                    },
                )
            )

        # Determine expected answer field specifications based on active supports
        answer_schema: list[AnswerFieldSpec] = []
        walls = supports.get("walls", [])
        fixed_pins = supports.get("fixed_pins", [])
        rollers = supports.get("rollers", [])

        if len(walls) == 1:
            answer_schema.extend([
                AnswerFieldSpec(
                    field_id="reaction_Ax",
                    label="Horizontal Reaction Ax (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_Ay",
                    label="Vertical Reaction Ay (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_MA",
                    label="Reaction Moment MA (kN-m)",
                    unit="kN-m",
                    value_type="numeric",
                ),
            ])
        elif len(fixed_pins) == 1 and len(rollers) == 1:
            roller_rot = int(rollers[0].get("rotation", 0))
            roller_label = "Bx" if roller_rot in (90, 270) else "By"
            answer_schema.extend([
                AnswerFieldSpec(
                    field_id="reaction_Ax",
                    label="Pin Reaction Ax (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id="reaction_Ay",
                    label="Pin Reaction Ay (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
                AnswerFieldSpec(
                    field_id=f"reaction_{roller_label}",
                    label=f"Roller Reaction {roller_label} (kN)",
                    unit="kN",
                    value_type="numeric",
                ),
            ])
        elif len(rollers) == 3:
            support_names = ["A", "B", "C"]
            for i in range(3):
                rot = int(rollers[i].get("rotation", 0))
                axis = "x" if rot in (90, 270) else "y"
                field_id = f"reaction_{support_names[i]}{axis}"
                answer_schema.append(
                    AnswerFieldSpec(
                        field_id=field_id,
                        label=f"Roller Reaction {support_names[i]}{axis} (kN)",
                        unit="kN",
                        value_type="numeric",
                    )
                )

        return ProblemDisplayData(
            problem_type=self.problem_type,
            seed=seed,
            title="2D Rigid Body Equilibrium",
            instructions=(
                "Determine the unknown support reaction forces and moments "
                "for the rigid body in static equilibrium."
            ),
            visual_schema=visual_schema,
            answer_schema=answer_schema,
        )

    def solve(self, seed: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Server-side solver for ground truth reactions and moments."""
        _, _, _, supports, loads = self._build_instance(seed, params)
        reactions = solve_rigid_body_reactions(supports, loads)

        # Standardize reaction dictionary keys
        structured_reactions: dict[str, float] = {}
        for k, v in reactions.items():
            field_id = k if k.startswith("reaction_") else f"reaction_{k}"
            structured_reactions[field_id] = float(v)

        return {
            "reactions": structured_reactions,
            "supports": supports,
        }

    def check(
        self,
        seed: int,
        submission: AnswerSubmission,
        tolerance: float = 0.01,
        params: dict[str, Any] | None = None,
    ) -> GradingResult:
        """Stateless evaluation of student answers against ground truth reactions."""
        ground_truth = self.solve(seed, params)
        expected_reactions = ground_truth["reactions"]

        field_results: dict[str, FieldResult] = {}
        correct_count = 0
        total_fields = len(expected_reactions)

        for field_id, expected_val in expected_reactions.items():
            # Allow submission with or without 'reaction_' prefix
            short_id = field_id.replace("reaction_", "")
            submitted_val = submission.answers.get(field_id)
            if submitted_val is None:
                submitted_val = submission.answers.get(short_id)

            if submitted_val is not None:
                try:
                    sub_num = float(submitted_val)
                    exp_num = float(expected_val)
                    delta = abs(sub_num - exp_num)
                    is_corr = delta <= (tolerance * max(abs(exp_num), 1.0))
                    if is_corr:
                        correct_count += 1
                    field_results[field_id] = FieldResult(
                        is_correct=is_corr,
                        submitted=sub_num,
                        delta=delta,
                    )
                except (ValueError, TypeError):
                    field_results[field_id] = FieldResult(
                        is_correct=False,
                        submitted=submitted_val,
                        message="Invalid numerical input",
                    )
            else:
                field_results[field_id] = FieldResult(
                    is_correct=False,
                    submitted=None,
                    message="Field missing",
                )

        score = correct_count / total_fields if total_fields > 0 else 0.0
        return GradingResult(
            is_passed=(score == 1.0),
            score=score,
            field_results=field_results,
        )


# Register Rigid Body generator instance with problem registry
rigid_body_generator = RigidBodyGenerator()
problem_registry.register(rigid_body_generator)

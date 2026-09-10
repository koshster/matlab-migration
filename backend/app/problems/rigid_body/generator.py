"""2D Rigid Body equilibrium problem domain generator implementing ProblemGeneratorProtocol.

This module provides the unified domain engine for 2D rigid body statics problems.
It implements the 6 required protocol members:
1. `problem_type` -> "rigid_body"
2. `display_name` -> "2D Rigid Body Equilibrium"
3. `params_schema` -> Configurable difficulty knobs: support configuration,
   how many forces and couples are applied, and the direction and magnitude
   range of each load family
4. `generate(seed, params)` -> Emits ProblemDisplayData (zero solution leakage)
5. `solve(seed, params)` -> Computes exact server-side ground truth reactions
6. `check(seed, submission, tolerance, params)` -> Evaluates student answers
"""

from typing import Any

import numpy as np

from app.problems.base import (
    AnswerFieldSpec,
    AnswerSubmission,
    FieldResult,
    GradingResult,
    ParamFieldSpec,
    ParamOption,
    ProblemDisplayData,
    VisualElementSchema,
)
from app.problems.registry import problem_registry
from app.problems.rigid_body.geometry import generate_rigid_body_geometry
from app.problems.rigid_body.loads import (
    FORCE_DIRECTION_ANY,
    FORCE_DIRECTION_DOWNWARD,
    FORCE_DIRECTION_HORIZONTAL,
    FORCE_DIRECTION_VERTICAL,
    MOMENT_DIRECTION_ANY,
    MOMENT_DIRECTION_CCW,
    MOMENT_DIRECTION_CW,
    generate_loads,
)
from app.problems.rigid_body.solver import solve_rigid_body_reactions
from app.problems.rigid_body.supports import generate_supports


class RigidBodyGenerator:
    """2D Rigid Body equilibrium problem domain generator and grader."""

    @property
    def problem_type(self) -> str:
        """Unique domain identifier string used by API routes and client renderers."""
        return "rigid_body"

    @property
    def display_name(self) -> str:
        """Human-readable name displayed in the Assignment Builder UI."""
        return "2D Rigid Body Equilibrium"

    @property
    def params_schema(self) -> list[ParamFieldSpec]:
        """Configurable difficulty knobs exposed to instructors in the assignment builder.

        These cover the "Number, Type, & Placement of Loads" and "Directions and
        Magnitudes of Loads" parameterization axes from the course design deck.

        Knobs:
            - `support_case`: Selects boundary conditions (1: 3 Rollers, 2: Pin+Roller, 3: Wall).
            - `num_loads`: Number of applied point forces (1 to 4).
            - `load_direction`: Which cardinal directions point loads may take.
            - `min_force` / `max_force`: Inclusive point load magnitude range in kN.
            - `num_moments`: Number of concentrated couple moments (0 to 2).
            - `moment_direction`: Rotational sense of the couples (CCW, CW, or either).
            - `min_moment` / `max_moment`: Inclusive couple magnitude range in Fa units.

        Setting a range's two bounds equal pins every load of that family to
        exactly that magnitude, which is how a fixed "3F and F" style problem is
        configured.
        """
        return [
            ParamFieldSpec(
                name="support_case",
                label="Support Configuration",
                value_type="integer",
                default=2,
                minimum=1,
                maximum=3,
                step=1,
                help_text="Boundary conditions holding the body in equilibrium.",
                options=[
                    ParamOption(value=1, label="3 Rollers"),
                    ParamOption(value=2, label="Pin + Roller"),
                    ParamOption(value=3, label="Fixed Cantilever Wall"),
                ],
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
                name="load_direction",
                label="Force direction",
                value_type="integer",
                default=FORCE_DIRECTION_ANY,
                minimum=FORCE_DIRECTION_ANY,
                maximum=FORCE_DIRECTION_DOWNWARD,
                step=1,
                help_text=(
                    "Restricts which cardinal directions point loads may take. "
                    "Downward only produces gravity-style loading."
                ),
                options=[
                    ParamOption(value=FORCE_DIRECTION_ANY, label="Any direction"),
                    ParamOption(value=FORCE_DIRECTION_VERTICAL, label="Vertical only"),
                    ParamOption(value=FORCE_DIRECTION_HORIZONTAL, label="Horizontal only"),
                    ParamOption(value=FORCE_DIRECTION_DOWNWARD, label="Downward only"),
                ],
            ),
            ParamFieldSpec(
                name="min_force",
                label="Min load magnitude (kN)",
                value_type="integer",
                default=1,
                minimum=1,
                maximum=20,
                step=1,
                help_text="Lower bound for applied point load magnitudes.",
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
                name="moment_direction",
                label="Couple direction",
                value_type="integer",
                default=MOMENT_DIRECTION_ANY,
                minimum=MOMENT_DIRECTION_ANY,
                maximum=MOMENT_DIRECTION_CW,
                step=1,
                help_text="Rotational sense of the applied couple moments.",
                options=[
                    ParamOption(value=MOMENT_DIRECTION_ANY, label="Either sense"),
                    ParamOption(value=MOMENT_DIRECTION_CCW, label="Counterclockwise"),
                    ParamOption(value=MOMENT_DIRECTION_CW, label="Clockwise"),
                ],
            ),
            ParamFieldSpec(
                name="min_moment",
                label="Min couple magnitude (Fa)",
                value_type="integer",
                default=1,
                minimum=1,
                maximum=20,
                step=1,
                help_text="Lower bound for applied couple moment magnitudes.",
            ),
            ParamFieldSpec(
                name="max_moment",
                label="Max couple magnitude (Fa)",
                value_type="integer",
                default=5,
                minimum=1,
                maximum=20,
                step=1,
                help_text="Upper bound for applied couple moment magnitudes.",
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
        """Internal helper to deterministically synthesize geometry, supports, and loads."""
        # Initialize explicit NumPy RNG from the seed for 100% reproducibility
        rng = np.random.default_rng(seed)
        p = params or {}

        support_case = int(p.get("support_case", 2))
        if support_case not in (1, 2, 3):
            support_case = 2

        n_forces = int(p.get("num_loads", 2))
        n_moments = int(p.get("num_moments", 0))
        max_force = float(p.get("max_force", 5.0))
        min_force = float(p.get("min_force", 1.0))
        max_moment = float(p.get("max_moment", 5.0))
        min_moment = float(p.get("min_moment", 1.0))

        # Unrecognised direction codes fall back to the unconstrained mode rather
        # than raising: params come from a JSON column an older assignment may
        # have been saved with, and a stale value must still render a problem.
        force_direction = int(p.get("load_direction", FORCE_DIRECTION_ANY))
        if force_direction not in (
            FORCE_DIRECTION_ANY,
            FORCE_DIRECTION_VERTICAL,
            FORCE_DIRECTION_HORIZONTAL,
            FORCE_DIRECTION_DOWNWARD,
        ):
            force_direction = FORCE_DIRECTION_ANY

        moment_direction = int(p.get("moment_direction", MOMENT_DIRECTION_ANY))
        if moment_direction not in (
            MOMENT_DIRECTION_ANY,
            MOMENT_DIRECTION_CCW,
            MOMENT_DIRECTION_CW,
        ):
            moment_direction = MOMENT_DIRECTION_ANY

        # Iteratively synthesize until an admissible determinate configuration is found
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
                    min_force=min_force,
                    force_direction=force_direction,
                    max_moment=max_moment,
                    min_moment=min_moment,
                    moment_direction=moment_direction,
                )
                return path_nodes, unique_nodes, surroundings, supports, loads

        # Deterministic fallback if random synthesis reaches attempt limit
        path_nodes, unique_nodes, surroundings = generate_rigid_body_geometry(
            min_nodes=5, rng=rng, max_attempts=1
        )
        supports, free_nodes, free_surr, _ = generate_supports(
            unique_nodes, surroundings, support_case=2, rng=rng
        )
        loads = generate_loads(
            free_nodes,
            free_surr,
            rng,
            n_forces=1,
            n_moments=0,
            max_force=max_force,
            min_force=min_force,
            force_direction=force_direction,
        )
        return path_nodes, unique_nodes, surroundings, supports, loads

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize problem geometry and display schema. NEVER return solution data.

        Emits graphical primitives (path, nodes, pins, rollers, walls, forces, moments)
        and declarative answer field specifications for student entry.
        """
        path_nodes, unique_nodes, _surroundings, supports, loads = self._build_instance(
            seed, params
        )

        visual_schema: list[VisualElementSchema] = []

        # 1. Continuous rigid body path (rendered as thick structural members in SVG)
        visual_schema.append(
            VisualElementSchema(
                element_type="rigid_body_path",
                properties={"path": path_nodes.tolist()},
            )
        )

        # 2. Joint / node coordinate points
        for idx, pos in enumerate(unique_nodes):
            visual_schema.append(
                VisualElementSchema(
                    element_type="node",
                    properties={"id": idx, "x": float(pos[0]), "y": float(pos[1])},
                )
            )

        # 3. Boundary supports (Pins, Rollers, and Fixed Walls)
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

        # 4. Applied Point Loads (Concentrated force vectors)
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

        # 5. Concentrated Couple Moments (Curved moment arcs)
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

        # 6. Expected Student Answer Fields based on active support reactions
        # Labels are the bare reaction symbol -- "Ax", "By", "MA" -- to match the
        # support letter in the diagram. AnswerPanel renders the label in a narrow
        # fixed-width gutter and shows `unit` separately, so a prose label like
        # "Horizontal Reaction Ax (kN)" both wrapped and repeated the unit.
        answer_schema: list[AnswerFieldSpec] = []
        walls = supports.get("walls", [])
        fixed_pins = supports.get("fixed_pins", [])
        rollers = supports.get("rollers", [])

        # Case 3: Fixed Cantilever Wall -> student solves Ax, Ay, MA
        if len(walls) == 1:
            answer_schema.extend(
                [
                    AnswerFieldSpec(
                        field_id="reaction_Ax",
                        label="Ax",
                        unit="kN",
                        value_type="numeric",
                    ),
                    AnswerFieldSpec(
                        field_id="reaction_Ay",
                        label="Ay",
                        unit="kN",
                        value_type="numeric",
                    ),
                    AnswerFieldSpec(
                        field_id="reaction_MA",
                        label="MA",
                        unit="kN-m",
                        value_type="numeric",
                    ),
                ]
            )

        # Case 2: Pin + Roller -> student solves Ax, Ay, Bx or By
        elif len(fixed_pins) == 1 and len(rollers) == 1:
            roller_rot = int(rollers[0].get("rotation", 0))
            roller_label = "Bx" if roller_rot in (90, 270) else "By"
            answer_schema.extend(
                [
                    AnswerFieldSpec(
                        field_id="reaction_Ax",
                        label="Ax",
                        unit="kN",
                        value_type="numeric",
                    ),
                    AnswerFieldSpec(
                        field_id="reaction_Ay",
                        label="Ay",
                        unit="kN",
                        value_type="numeric",
                    ),
                    AnswerFieldSpec(
                        field_id=f"reaction_{roller_label}",
                        label=roller_label,
                        unit="kN",
                        value_type="numeric",
                    ),
                ]
            )

        # Case 1: 3 Rollers -> student solves reactions at A, B, C
        elif len(rollers) == 3:
            support_names = ["A", "B", "C"]
            for i in range(3):
                rot = int(rollers[i].get("rotation", 0))
                axis = "x" if rot in (90, 270) else "y"
                field_id = f"reaction_{support_names[i]}{axis}"
                answer_schema.append(
                    AnswerFieldSpec(
                        field_id=field_id,
                        label=f"{support_names[i]}{axis}",
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
        """Server-side solver for ground truth reactions and moments. Internal use only."""
        _, _, _, supports, loads = self._build_instance(seed, params)
        reactions = solve_rigid_body_reactions(supports, loads)

        # Standardize reaction dictionary keys (e.g. 'reaction_Ax', 'reaction_Ay')
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
        """Stateless evaluation of student answers against ground truth reactions.

        Grading Rules:
            - Numeric fields are evaluated within relative tolerance:
              delta = |submitted - expected| <= tolerance * max(|expected|, 1.0)
            - Supports both prefixed keys ('reaction_Ax') and short keys ('Ax').
        """
        ground_truth = self.solve(seed, params)
        expected_reactions = ground_truth["reactions"]

        field_results: dict[str, FieldResult] = {}
        correct_count = 0
        total_fields = len(expected_reactions)

        for field_id, expected_val in expected_reactions.items():
            # Allow submission with or without 'reaction_' prefix for student convenience
            short_id = field_id.replace("reaction_", "")
            submitted_val = submission.answers.get(field_id)
            if submitted_val is None:
                submitted_val = submission.answers.get(short_id)

            if submitted_val is not None:
                try:
                    sub_num = float(submitted_val)
                    exp_num = float(expected_val)
                    delta = abs(sub_num - exp_num)
                    # Check tolerance threshold (e.g. within 1%)
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


# Automatically register Rigid Body generator instance with problem registry
rigid_body_generator = RigidBodyGenerator()
problem_registry.register(rigid_body_generator)

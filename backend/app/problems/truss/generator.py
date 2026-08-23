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
from app.problems.truss.geometry import generate_truss_geometry
from app.problems.truss.loads import generate_loads
from app.problems.truss.solver import solve_member_forces, solve_support_reactions
from app.problems.truss.supports import generate_supports


class TrussGenerator:
    """Truss problem domain generator and evaluator implementing ProblemGeneratorProtocol."""

    @property
    def problem_type(self) -> str:
        return "truss"

    @property
    def display_name(self) -> str:
        return "Planar truss"

    @property
    def params_schema(self) -> list[ParamFieldSpec]:
        """Knobs the assignment builder exposes for a truss problem.

        Support profile is deliberately absent: solve_support_reactions raises
        for anything but one pin plus one roller, and the legacy 0-pin/3-roller
        branch is unported. Offering it would let an instructor save a
        configuration that cannot be solved.
        """
        return [
            ParamFieldSpec(
                name="num_nodes",
                label="Joints",
                value_type="integer",
                default=3,
                minimum=3,
                maximum=8,
                step=1,
                help_text="Members scale as 2n−3, so joints drive the problem's size.",
            ),
            ParamFieldSpec(
                name="max_force",
                label="Max load (kN)",
                value_type="integer",
                default=5,
                minimum=1,
                maximum=20,
                step=1,
                help_text="Load magnitudes are whole numbers from 1 to this value.",
            ),
            ParamFieldSpec(
                name="load_count",
                label="Applied loads",
                value_type="integer",
                default=1,
                minimum=1,
                maximum=2,
                step=1,
                help_text="Clamped to the number of free joints on small trusses.",
            ),
        ]

    def _build_truss_instance(
        self, seed: int, params: dict[str, Any] | None = None
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        rng = np.random.default_rng(seed)
        p = params or {}
        node_count_schedule = [3, 3, 4, 4, 5, 5, 6, 6]
        problem_id = p.get("problem_id", 1)
        default_n = node_count_schedule[min(max(problem_id - 1, 0), len(node_count_schedule) - 1)]
        n_nodes = p.get("num_nodes", default_n)

        node_coords, members, _ = generate_truss_geometry(n_nodes, rng)
        pins, rollers = generate_supports(node_coords, rng)
        forces = generate_loads(
            node_coords,
            pins,
            rollers,
            rng,
            max_magnitude=float(p.get("max_force", 5.0)),
            load_count=int(p.get("load_count", 1)),
        )

        return node_coords, members, pins, rollers, forces

    def generate(self, seed: int, params: dict[str, Any] | None = None) -> ProblemDisplayData:
        """Synthesize problem geometry and display schema. NEVER return solution data."""
        node_coords, members, pins, rollers, forces = self._build_truss_instance(seed, params)

        visual_schema: list[VisualElementSchema] = []

        # Nodes
        for idx, pos in enumerate(node_coords):
            visual_schema.append(
                VisualElementSchema(
                    element_type="node",
                    properties={"id": idx, "x": float(pos[0]), "y": float(pos[1])},
                )
            )

        # Members
        for _m_idx, (start, end) in enumerate(members):
            visual_schema.append(
                VisualElementSchema(
                    element_type="member",
                    properties={
                        "id": f"M_{start}_{end}",
                        "start_node": int(start),
                        "end_node": int(end),
                    },
                )
            )

        # Supports
        for pin in pins:
            visual_schema.append(
                VisualElementSchema(
                    element_type="pin",
                    properties={"node_index": pin["node_index"], "r": pin["r"]},
                )
            )

        for roller in rollers:
            visual_schema.append(
                VisualElementSchema(
                    element_type="roller",
                    properties={
                        "node_index": roller["node_index"],
                        "r": roller["r"],
                        "rotation": roller.get("rotation", 0),
                    },
                )
            )

        # External Forces
        for f in forces:
            visual_schema.append(
                VisualElementSchema(
                    element_type="point_load",
                    properties={
                        "node_index": f["node_index"],
                        "force_vector": f["F"],
                        "position": f["P"],
                    },
                )
            )

        # Answer Schema (Student Input Fields)
        answer_schema: list[AnswerFieldSpec] = []
        for _m_idx, (start, end) in enumerate(members):
            field_id = f"member_{start}_{end}"
            answer_schema.append(
                AnswerFieldSpec(
                    field_id=field_id,
                    label=f"Force in Member ({start + 1}-{end + 1})",
                    unit="kN",
                    value_type="numeric",
                )
            )
            answer_schema.append(
                AnswerFieldSpec(
                    field_id=f"{field_id}_state",
                    label=f"State of Member ({start + 1}-{end + 1})",
                    unit="",
                    value_type="enum",
                    options=["Tension", "Compression", "Zero"],
                )
            )

        return ProblemDisplayData(
            problem_type=self.problem_type,
            seed=seed,
            title="2D Planar Truss Analysis",
            instructions=(
                "Determine the reaction forces at supports "
                "and internal axial force in each truss member."
            ),
            visual_schema=visual_schema,
            answer_schema=answer_schema,
        )

    def solve(self, seed: int, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Server-side solver for ground truth reactions and member forces."""
        node_coords, members, pins, rollers, forces = self._build_truss_instance(seed, params)
        reactions = solve_support_reactions(pins, rollers, forces)
        member_forces = solve_member_forces(node_coords, members, reactions, pins, rollers, forces)

        member_solutions = {}
        for m_idx, (start, end) in enumerate(members):
            f_val = float(member_forces[m_idx])
            state = "Zero"
            if abs(f_val) < 1e-4:
                state = "Zero"
            elif f_val > 0:
                state = "Tension"
            else:
                state = "Compression"

            member_solutions[f"member_{start}_{end}"] = {
                "magnitude": abs(f_val),
                "signed_force": f_val,
                "state": state,
            }

        return {
            "reactions": reactions,
            "member_solutions": member_solutions,
        }

    def check(
        self,
        seed: int,
        submission: AnswerSubmission,
        tolerance: float = 0.01,
        params: dict[str, Any] | None = None,
    ) -> GradingResult:
        """Stateless evaluation of student submission against ground truth solution.

        `params` must match the call to `generate()`; omitting it previously
        meant every submission was graded against the default 3-node truss.
        """
        ground_truth = self.solve(seed, params)
        member_solutions = ground_truth["member_solutions"]

        field_results: dict[str, FieldResult] = {}
        correct_count = 0
        total_fields = 0

        for field_id, expected_data in member_solutions.items():
            # Check magnitude
            submitted_val = submission.answers.get(field_id)
            total_fields += 1
            if submitted_val is not None:
                try:
                    sub_num = float(submitted_val)
                    exp_num = float(expected_data["magnitude"])
                    delta = abs(sub_num - exp_num)
                    is_corr = delta <= (tolerance * max(abs(exp_num), 1.0))
                    if is_corr:
                        correct_count += 1
                    field_results[field_id] = FieldResult(
                        is_correct=is_corr,
                        submitted=submitted_val,
                        delta=delta,
                    )
                except ValueError:
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

            # Check state (Tension/Compression/Zero)
            state_field_id = f"{field_id}_state"
            submitted_state = submission.answers.get(state_field_id)
            total_fields += 1
            expected_state = expected_data["state"]
            is_state_corr = (
                submitted_state is not None
                and str(submitted_state).strip().lower() == expected_state.lower()
            )
            if is_state_corr:
                correct_count += 1
            field_results[state_field_id] = FieldResult(
                is_correct=is_state_corr,
                submitted=submitted_state,
            )

        score = correct_count / total_fields if total_fields > 0 else 0.0
        return GradingResult(
            is_passed=(score == 1.0),
            score=score,
            field_results=field_results,
        )


# Automatically register Truss generator instance with the problem registry
truss_generator = TrussGenerator()
problem_registry.register(truss_generator)

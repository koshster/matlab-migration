"""Unit and integration tests for the 2D Rigid Body equilibrium problem domain.

This test suite validates:
1. Registry integration and catalog schema conformance.
2. Seed reproducibility (identical RNG state produces bit-identical geometry and loads).
3. Zero solution leakage (reaction forces and solver matrices never appear in public schemas).
4. Integer Cartesian grid alignment (all nodes and path coordinates lie on whole integers).
5. Kinematic stability & determinacy checks (pin/roller moment arm and roller parallelism).
6. Physics equilibrium satisfaction (sum(Fx) = 0, sum(Fy) = 0, sum(Mo) = 0 for all cases).
7. Student grading logic (evaluation within 1% relative tolerance, partial credit, error handling).
8. Textbook analytical problem solutions matching legacy MATLAB benchmarks.
9. Instructor-configurable load direction and magnitude range.
"""

from typing import Any

import numpy as np
import pytest

from app.problems.base import AnswerSubmission
from app.problems.registry import problem_registry
from app.problems.rigid_body.generator import rigid_body_generator
from app.problems.rigid_body.geometry import collapse_nodes, generate_body_path
from app.problems.rigid_body.loads import (
    FORCE_DIRECTION_ANY,
    FORCE_DIRECTION_DOWNWARD,
    FORCE_DIRECTION_HORIZONTAL,
    FORCE_DIRECTION_VERTICAL,
    MOMENT_DIRECTION_ANY,
    MOMENT_DIRECTION_CCW,
    MOMENT_DIRECTION_CW,
)
from app.problems.rigid_body.solver import solve_rigid_body_reactions
from app.problems.rigid_body.supports import is_support_configuration_invalid


def test_registry_contains_rigid_body() -> None:
    """Verify that the 2D Rigid Body problem domain generator is properly registered."""
    assert "rigid_body" in problem_registry.list_types()
    gen = problem_registry.get("rigid_body")
    assert gen.problem_type == "rigid_body"
    assert gen.display_name == "2D Rigid Body Equilibrium"


def test_rigid_body_generator_reproducibility() -> None:
    """Verify that a given seed generates bit-identical problem instances every time."""
    seed = 42
    data1 = rigid_body_generator.generate(seed)
    data2 = rigid_body_generator.generate(seed)

    assert data1.problem_type == "rigid_body"
    assert data1.seed == seed
    assert len(data1.visual_schema) == len(data2.visual_schema)
    assert len(data1.answer_schema) == len(data2.answer_schema)
    assert data1.model_dump() == data2.model_dump()


def test_rigid_body_zero_solution_leakage() -> None:
    """Security Invariant: Ensure zero solution data is included in student-facing payloads."""
    seed = 12345
    display_data = rigid_body_generator.generate(seed)
    serialized = display_data.model_dump_json()

    # Solution keys must never appear in student-facing JSON
    assert "reactions" not in serialized
    assert "solutionMat" not in serialized
    assert "a_mat" not in serialized


def test_rigid_body_integer_grid_coordinates() -> None:
    """Verify that generated rigid body nodes and paths lie on integer grid coordinates."""
    for seed in [1, 42, 100, 999, 54321]:
        display_data = rigid_body_generator.generate(seed)
        for element in display_data.visual_schema:
            if element.element_type == "node":
                x = element.properties["x"]
                y = element.properties["y"]
                assert float(x).is_integer(), f"Seed {seed} generated non-integer x={x}"
                assert float(y).is_integer(), f"Seed {seed} generated non-integer y={y}"
            elif element.element_type == "rigid_body_path":
                for pt in element.properties["path"]:
                    assert float(pt[0]).is_integer()
                    assert float(pt[1]).is_integer()


def test_geometry_path_and_collapse_integrity() -> None:
    """Verify random walk generation and node collapsing logic."""
    rng = np.random.default_rng(123)
    path = generate_body_path(steps=6, rng=rng)
    assert len(path) == 7
    assert np.array_equal(path[0], [0, 0])

    unique_nodes, surroundings = collapse_nodes(path)
    assert len(unique_nodes) <= len(path)
    assert len(unique_nodes) == len(surroundings)
    assert surroundings.shape[1] == 4


def test_support_determinacy_validation() -> None:
    """Verify detection of kinematically inadmissible support configurations."""
    # Collinear vertical pin and roller (passes through pin -> zero moment arm)
    fixed_pin = [{"r": [0, 0], "rotation": 0}]
    roller_collinear = [{"r": [0, 2], "rotation": 0}]
    assert is_support_configuration_invalid(fixed_pin, roller_collinear, []) is True

    # Non-collinear pin and roller (valid non-zero moment arm)
    roller_valid = [{"r": [2, 1], "rotation": 0}]
    assert is_support_configuration_invalid(fixed_pin, roller_valid, []) is False

    # 3 parallel rollers (all horizontal -> unable to resist vertical forces)
    three_horiz_rollers = [
        {"r": [0, 0], "rotation": 90},
        {"r": [1, 1], "rotation": 90},
        {"r": [2, 2], "rotation": 270},
    ]
    assert is_support_configuration_invalid([], three_horiz_rollers, []) is True


@pytest.mark.parametrize("support_case", [1, 2, 3])
def test_all_support_cases_equilibrium_satisfaction(support_case: int) -> None:
    """Verify that solver reactions exactly satisfy sum(Fx) = 0, sum(Fy) = 0, sum(Mo) = 0."""
    for seed in range(1, 20):
        params = {"support_case": support_case, "num_loads": 2, "num_moments": 1}
        sol = rigid_body_generator.solve(seed, params=params)
        reactions = sol["reactions"]
        supports = sol["supports"]

        display = rigid_body_generator.generate(seed, params=params)
        forces = [el.properties for el in display.visual_schema if el.element_type == "point_load"]
        moments = [el.properties for el in display.visual_schema if el.element_type == "moment"]

        # Sum of external forces and moments about origin
        sum_fx = sum(f["force_vector"][0] for f in forces)
        sum_fy = sum(f["force_vector"][1] for f in forces)
        sum_mo = sum(
            -f["force_vector"][0] * f["position"][1] + f["force_vector"][1] * f["position"][0]
            for f in forces
        )
        sum_mo += sum(m["magnitude"] * m["direction"] for m in moments)

        # Add support reaction contributions
        if support_case == 2:  # Pin + Roller
            sum_fx += reactions["reaction_Ax"]
            sum_fy += reactions["reaction_Ay"]
            pin = supports["fixed_pins"][0]
            roller = supports["rollers"][0]
            sum_mo += (
                -reactions["reaction_Ax"] * pin["r"][1] + reactions["reaction_Ay"] * pin["r"][0]
            )
            if "reaction_Bx" in reactions:
                sum_fx += reactions["reaction_Bx"]
                sum_mo += -reactions["reaction_Bx"] * roller["r"][1]
            elif "reaction_By" in reactions:
                sum_fy += reactions["reaction_By"]
                sum_mo += reactions["reaction_By"] * roller["r"][0]

        elif support_case == 1:  # 3 Rollers
            for r in supports["rollers"]:
                lbl = r["label"]
                rx, ry = r["r"]
                if f"reaction_{lbl}x" in reactions:
                    val = reactions[f"reaction_{lbl}x"]
                    sum_fx += val
                    sum_mo += -val * ry
                elif f"reaction_{lbl}y" in reactions:
                    val = reactions[f"reaction_{lbl}y"]
                    sum_fy += val
                    sum_mo += val * rx

        elif support_case == 3:  # Fixed Wall
            sum_fx += reactions["reaction_Ax"]
            sum_fy += reactions["reaction_Ay"]
            wall = supports["walls"][0]
            wx, wy = wall["r"]
            sum_mo += -reactions["reaction_Ax"] * wy + reactions["reaction_Ay"] * wx
            sum_mo += reactions["reaction_MA"]

        assert np.isclose(sum_fx, 0.0, atol=1e-5), f"Seed {seed}: sum(Fx)={sum_fx}"
        assert np.isclose(sum_fy, 0.0, atol=1e-5), f"Seed {seed}: sum(Fy)={sum_fy}"
        assert np.isclose(sum_mo, 0.0, atol=1e-5), f"Seed {seed}: sum(Mo)={sum_mo}"


def test_rigid_body_grading_evaluation() -> None:
    """Verify grading logic on correct, partial, and incorrect student submissions."""
    seed = 42
    sol = rigid_body_generator.solve(seed)
    reactions = sol["reactions"]

    # 1. Perfectly correct submission
    correct_sub = AnswerSubmission(answers=dict(reactions))
    res_correct = rigid_body_generator.check(seed, correct_sub, tolerance=0.01)
    assert res_correct.is_passed is True
    assert res_correct.score == 1.0

    # 2. Short keys submission without 'reaction_' prefix
    short_answers = {k.replace("reaction_", ""): v for k, v in reactions.items()}
    res_short = rigid_body_generator.check(seed, AnswerSubmission(answers=short_answers))
    assert res_short.is_passed is True

    # 3. Submission with incorrect value
    wrong_answers = dict(reactions)
    first_key = list(reactions.keys())[0]
    wrong_answers[first_key] = reactions[first_key] + 10.0
    res_wrong = rigid_body_generator.check(seed, AnswerSubmission(answers=wrong_answers))
    assert res_wrong.is_passed is False
    assert res_wrong.score < 1.0
    assert res_wrong.field_results[first_key].is_correct is False


def test_matlab_regression_known_system_solve() -> None:
    """Verify exact matrix solution for a known textbook rigid body problem."""
    # 1 Pin at (0, 0), 1 Roller at (4, 0) resisting vertical force By
    # Downward force of 10 kN at (2, 0)
    supports = {
        "fixed_pins": [{"r": [0.0, 0.0], "rotation": 0}],
        "rollers": [{"r": [4.0, 0.0], "rotation": 0}],
        "walls": [],
    }
    loads = {
        "forces": [{"P": [2.0, 0.0], "F": [0.0, -10.0]}],
        "moments": [],
    }
    res = solve_rigid_body_reactions(supports, loads)
    assert np.isclose(res["Ax"], 0.0)
    assert np.isclose(res["Ay"], 5.0)
    assert np.isclose(res["By"], 5.0)


# ---------------------------------------------------------------------------
# Instructor-configurable load direction and magnitude
#
# The design deck lists "Directions and Magnitudes of Loads" as a
# parameterization axis alongside the number and placement of loads, so both
# are knobs rather than fixed generator behaviour.
# ---------------------------------------------------------------------------

SEEDS = range(1, 25)


def _forces(seed: int, params: dict[str, object]) -> list[dict[str, Any]]:
    display = rigid_body_generator.generate(seed, params=dict(params))
    return [el.properties for el in display.visual_schema if el.element_type == "point_load"]


def _moments(seed: int, params: dict[str, object]) -> list[dict[str, Any]]:
    display = rigid_body_generator.generate(seed, params=dict(params))
    return [el.properties for el in display.visual_schema if el.element_type == "moment"]


def test_declared_defaults_reproduce_the_generators_own_behaviour() -> None:
    """An instructor who never touches the difficulty form must get the same
    problem as one who saves every default explicitly."""
    defaults = {f.name: f.default for f in rigid_body_generator.params_schema}
    for seed in SEEDS:
        explicit = rigid_body_generator.generate(seed, params=defaults)
        implicit = rigid_body_generator.generate(seed)
        assert explicit.model_dump() == implicit.model_dump()


def test_load_direction_vertical_only() -> None:
    seen_up = seen_down = False
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 4, "load_direction": FORCE_DIRECTION_VERTICAL}):
            fx, fy = f["force_vector"]
            assert fx == 0.0, f"seed {seed}: vertical-only load has fx={fx}"
            assert fy != 0.0
            seen_up |= fy > 0
            seen_down |= fy < 0
    # Both senses stay reachable -- "vertical" constrains the axis, not the sign.
    assert seen_up and seen_down


def test_load_direction_horizontal_only() -> None:
    seen_left = seen_right = False
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 4, "load_direction": FORCE_DIRECTION_HORIZONTAL}):
            fx, fy = f["force_vector"]
            assert fy == 0.0, f"seed {seed}: horizontal-only load has fy={fy}"
            assert fx != 0.0
            seen_left |= fx < 0
            seen_right |= fx > 0
    assert seen_left and seen_right


def test_load_direction_downward_only() -> None:
    total = 0
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 4, "load_direction": FORCE_DIRECTION_DOWNWARD}):
            fx, fy = f["force_vector"]
            assert fx == 0.0
            assert fy < 0.0, f"seed {seed}: downward-only load has fy={fy}"
            total += 1
    assert total > 0


def test_load_direction_any_produces_both_axes() -> None:
    """The default must stay unconstrained, otherwise the knob's neutral setting
    would silently narrow existing assignments."""
    axes = set()
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 4, "load_direction": FORCE_DIRECTION_ANY}):
            fx, fy = f["force_vector"]
            axes.add("x" if fx != 0.0 else "y")
    assert axes == {"x", "y"}


@pytest.mark.parametrize(("min_force", "max_force"), [(1, 5), (3, 3), (2, 4), (7, 12)])
def test_force_magnitudes_stay_inside_the_configured_range(min_force: int, max_force: int) -> None:
    seen: set[float] = set()
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 4, "min_force": min_force, "max_force": max_force}):
            mag = f["magnitude"]
            fx, fy = f["force_vector"]
            assert min_force <= mag <= max_force, f"seed {seed}: magnitude {mag} out of range"
            # The drawn vector and the label must agree with the magnitude.
            assert abs(fx) + abs(fy) == mag
            seen.add(mag)
    assert seen
    if min_force == max_force:
        assert seen == {float(min_force)}


def test_equal_force_bounds_pin_every_load_to_one_magnitude() -> None:
    """How an instructor asks for the deck's fixed-magnitude problems."""
    labels = set()
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 3, "min_force": 3, "max_force": 3}):
            labels.add(f["label"])
    assert labels == {"3F"}


def test_inverted_force_range_collapses_instead_of_raising() -> None:
    """params come from a JSON column, so a nonsensical range must still render."""
    for seed in SEEDS:
        for f in _forces(seed, {"num_loads": 2, "min_force": 9, "max_force": 2}):
            assert f["magnitude"] == 9.0


@pytest.mark.parametrize(
    ("mode", "expected"),
    [(MOMENT_DIRECTION_CCW, 1), (MOMENT_DIRECTION_CW, -1)],
)
def test_moment_direction_constrains_rotational_sense(mode: int, expected: int) -> None:
    total = 0
    for seed in SEEDS:
        for m in _moments(seed, {"num_moments": 2, "moment_direction": mode}):
            assert m["direction"] == expected, f"seed {seed}: got {m['direction']}"
            total += 1
    assert total > 0


def test_moment_direction_any_produces_both_senses() -> None:
    senses = set()
    for seed in SEEDS:
        for m in _moments(seed, {"num_moments": 2, "moment_direction": MOMENT_DIRECTION_ANY}):
            senses.add(m["direction"])
    assert senses == {1, -1}


@pytest.mark.parametrize(("min_moment", "max_moment"), [(1, 5), (4, 4), (2, 8)])
def test_moment_magnitudes_stay_inside_the_configured_range(
    min_moment: int, max_moment: int
) -> None:
    seen: set[float] = set()
    for seed in SEEDS:
        for m in _moments(
            seed, {"num_moments": 2, "min_moment": min_moment, "max_moment": max_moment}
        ):
            assert min_moment <= m["magnitude"] <= max_moment
            seen.add(m["magnitude"])
    assert seen
    if min_moment == max_moment:
        assert seen == {float(min_moment)}


def test_unknown_direction_codes_fall_back_to_unconstrained() -> None:
    """A slot saved against an older or hand-edited params value must not 500."""
    for seed in SEEDS:
        baseline = rigid_body_generator.generate(seed, params={"num_loads": 2, "num_moments": 1})
        stale = rigid_body_generator.generate(
            seed,
            params={
                "num_loads": 2,
                "num_moments": 1,
                "load_direction": 99,
                "moment_direction": -7,
            },
        )
        assert stale.model_dump() == baseline.model_dump()


@pytest.mark.parametrize("support_case", [1, 2, 3])
@pytest.mark.parametrize(
    "load_direction",
    [
        FORCE_DIRECTION_ANY,
        FORCE_DIRECTION_VERTICAL,
        FORCE_DIRECTION_HORIZONTAL,
        FORCE_DIRECTION_DOWNWARD,
    ],
)
@pytest.mark.parametrize(
    "moment_direction",
    [MOMENT_DIRECTION_ANY, MOMENT_DIRECTION_CCW, MOMENT_DIRECTION_CW],
)
def test_every_offered_load_configuration_stays_solvable_and_gradable(
    support_case: int, load_direction: int, moment_direction: int
) -> None:
    """The builder must not be able to save a load configuration that produces
    an unsolvable problem -- constraining direction narrows the load set, and a
    body loaded only horizontally is still in equilibrium under its reactions."""
    for seed in range(1, 8):
        params = {
            "support_case": support_case,
            "num_loads": 2,
            "num_moments": 1,
            "load_direction": load_direction,
            "moment_direction": moment_direction,
            "min_force": 2,
            "max_force": 6,
            "min_moment": 2,
            "max_moment": 4,
        }
        display = rigid_body_generator.generate(seed, params=params)
        ground_truth = rigid_body_generator.solve(seed, params=params)
        reactions = ground_truth["reactions"]

        # Every field the student is asked for must have a ground-truth value.
        for field in display.answer_schema:
            assert field.field_id in reactions, f"{field.field_id} has no solution"
        assert all(np.isfinite(v) for v in reactions.values())

        result = rigid_body_generator.check(
            seed, AnswerSubmission(answers=dict(reactions)), params=params
        )
        assert result.is_passed, f"case={support_case} seed={seed} not gradable"

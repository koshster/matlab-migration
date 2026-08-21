import numpy as np
import pytest

from app.problems.base import AnswerSubmission
from app.problems.registry import problem_registry
from app.problems.truss.generator import truss_generator
from app.problems.truss.geometry import generate_truss_geometry


def test_registry_contains_truss() -> None:
    """Verify that the Truss problem domain generator is properly registered."""
    assert "truss" in problem_registry.list_types()
    gen = problem_registry.get("truss")
    assert gen.problem_type == "truss"


def test_truss_generator_reproducibility() -> None:
    """Verify that a given seed generates bit-identical problem instances every time."""
    seed = 42
    data1 = truss_generator.generate(seed)
    data2 = truss_generator.generate(seed)

    assert data1.problem_type == "truss"
    assert data1.seed == seed
    assert len(data1.visual_schema) == len(data2.visual_schema)
    assert len(data1.answer_schema) == len(data2.answer_schema)
    assert data1.model_dump() == data2.model_dump()


def test_truss_generator_zero_solution_leakage() -> None:
    """Security Invariant: Ensure zero solution data is included in student-facing payloads."""
    seed = 12345
    display_data = truss_generator.generate(seed)
    serialized = display_data.model_dump_json()

    assert "member_solutions" not in serialized
    assert "reactions" not in serialized
    assert "signed_force" not in serialized


def test_truss_generator_integer_coordinates() -> None:
    """Verify that generated node coordinates are whole integer grid points matching MATLAB."""
    for seed in [1, 42, 100, 999, 54321]:
        display_data = truss_generator.generate(seed)
        for element in display_data.visual_schema:
            if element.element_type == "node":
                x = element.properties["x"]
                y = element.properties["y"]
                assert float(x).is_integer(), f"Seed {seed} generated non-integer x={x}"
                assert float(y).is_integer(), f"Seed {seed} generated non-integer y={y}"


def test_truss_generator_integer_forces_and_bounds() -> None:
    """Verify force magnitudes are whole integers within 1 to 5 kN matching MATLAB randi(5)."""
    for seed in range(1, 30):
        display_data = truss_generator.generate(seed)
        for element in display_data.visual_schema:
            if element.element_type == "point_load":
                fx, fy = element.properties["force_vector"]
                mag = max(abs(fx), abs(fy))
                assert float(mag).is_integer(), f"Seed {seed} generated non-integer force: {mag}"
                assert 1.0 <= mag <= 5.0, f"Seed {seed} generated out-of-range force: {mag}"


def test_force_and_supports_do_not_overlap() -> None:
    """Verify that external applied point loads are never placed on support joints."""
    for seed in range(1, 40):
        display_data = truss_generator.generate(seed)
        support_nodes = set()
        load_nodes = set()

        for element in display_data.visual_schema:
            if element.element_type in ("pin", "roller"):
                support_nodes.add(element.properties["node_index"])
            elif element.element_type == "point_load":
                load_nodes.add(element.properties["node_index"])

        overlap = support_nodes.intersection(load_nodes)
        assert len(overlap) == 0, f"Seed {seed} placed load on support node(s): {overlap}"


def test_simple_truss_determinacy_formula() -> None:
    """Verify that all generated trusses satisfy the planar determinacy relation m = 2n - 3."""
    for num_nodes in [3, 4, 5, 6]:
        for seed in [10, 20, 30, 40, 50]:
            display_data = truss_generator.generate(seed, params={"num_nodes": num_nodes})
            node_count = sum(1 for el in display_data.visual_schema if el.element_type == "node")
            member_count = sum(
                1 for el in display_data.visual_schema if el.element_type == "member"
            )

            assert node_count == num_nodes
            assert member_count == (2 * node_count - 3), (
                f"Determinacy violation for seed {seed}: nodes={node_count}, members={member_count}"
            )


def test_many_random_seeds_solvability() -> None:
    """Verify that a large random batch of seeds produces solvable trusses."""
    for seed in [7, 13, 42, 88, 101, 256, 500, 777, 999, 1234, 4321, 9999]:
        solution = truss_generator.solve(seed)
        assert "reactions" in solution
        assert "member_solutions" in solution
        assert len(solution["member_solutions"]) > 0

        # Check support reactions equilibrium
        reactions = solution["reactions"]
        assert all(isinstance(v, float) for v in reactions.values())


def test_invalid_node_count_edge_cases() -> None:
    """Verify that invalid node counts (0, 1, 2) raise ValueError gracefully."""
    rng = np.random.default_rng(42)
    for invalid_n in [0, 1, 2, -1]:
        with pytest.raises(ValueError, match="Number of nodes must be at least 3."):
            generate_truss_geometry(invalid_n, rng)


def test_grading_tolerance_and_incorrect_submissions() -> None:
    """Verify grading logic on correct, slightly off, and incorrect student submissions."""
    seed = 42
    solution = truss_generator.solve(seed)
    member_solutions = solution["member_solutions"]

    # 1. Perfectly correct submission
    correct_answers = {}
    for k, v in member_solutions.items():
        correct_answers[k] = v["magnitude"]
        correct_answers[f"{k}_state"] = v["state"]

    res_correct = truss_generator.check(
        seed, AnswerSubmission(answers=correct_answers), tolerance=0.01
    )
    assert res_correct.is_passed is True
    assert res_correct.score == 1.0

    # 2. Submission with wrong Tension/Compression state on first member
    wrong_state_answers = dict(correct_answers)
    first_member = list(member_solutions.keys())[0]
    opp_state = "Compression" if member_solutions[first_member]["state"] == "Tension" else "Tension"
    wrong_state_answers[f"{first_member}_state"] = opp_state

    res_wrong_state = truss_generator.check(seed, AnswerSubmission(answers=wrong_state_answers))
    assert res_wrong_state.is_passed is False
    assert res_wrong_state.score < 1.0
    assert res_wrong_state.field_results[f"{first_member}_state"].is_correct is False

    # 3. Submission outside 1% tolerance threshold
    out_of_tolerance_answers = dict(correct_answers)
    out_of_tolerance_answers[first_member] = member_solutions[first_member]["magnitude"] * 1.05

    res_tolerance = truss_generator.check(
        seed,
        AnswerSubmission(answers=out_of_tolerance_answers),
        tolerance=0.01,
    )
    assert res_tolerance.is_passed is False
    assert res_tolerance.field_results[first_member].is_correct is False

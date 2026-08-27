"""Comprehensive tests for problem domains.

Covers Rigid Body, Beam, Truss Geometry & Supports, and Registry.
"""

import numpy as np
import pytest

from app.problems.base import AnswerSubmission
from app.problems.beam.generator import BeamGenerator
from app.problems.registry import ProblemRegistry
from app.problems.rigid_body.generator import RigidBodyGenerator
from app.problems.truss.geometry import _generate_determinate_strip, generate_truss_geometry
from app.problems.truss.supports import generate_supports, get_outward_rotation


def test_rigid_body_generator_contract() -> None:
    gen = RigidBodyGenerator()
    assert gen.problem_type == "rigid_body"
    assert gen.display_name == "2D Rigid Body Equilibrium"
    assert len(gen.params_schema) == 2

    # Generate
    display = gen.generate(seed=42, params={"body_shape": 2, "num_loads": 3})
    assert display.problem_type == "rigid_body"
    assert display.seed == 42
    assert len(display.visual_schema) > 0
    assert len(display.answer_schema) == 3

    # Solve
    solution = gen.solve(seed=42)
    assert "reactions" in solution
    assert "member_solutions" in solution

    # Check
    submission = AnswerSubmission(answers={"reaction_Ax": 0.0, "reaction_Ay": 0.0})
    result = gen.check(seed=42, submission=submission, tolerance=0.01)
    assert result.is_passed is True
    assert result.score == 1.0


def test_beam_generator_contract() -> None:
    gen = BeamGenerator()
    assert gen.problem_type == "beam"
    assert gen.display_name == "Beam Reactions & Loadings"
    assert len(gen.params_schema) == 2

    # Generate
    display = gen.generate(seed=100, params={"span_length": 8, "load_type": 2})
    assert display.problem_type == "beam"
    assert display.seed == 100
    assert len(display.visual_schema) > 0
    assert len(display.answer_schema) == 2

    # Solve
    solution = gen.solve(seed=100)
    assert "reactions" in solution

    # Check
    submission = AnswerSubmission(answers={"reaction_Ay": 0.0})
    result = gen.check(seed=100, submission=submission, tolerance=0.01)
    assert result.is_passed is True
    assert result.score == 1.0


def test_problem_registry_error_handling() -> None:
    custom_reg = ProblemRegistry()
    gen = BeamGenerator()
    custom_reg.register(gen)

    assert custom_reg.get("beam") == gen
    assert "beam" in custom_reg.list_types()

    # Querying unknown generator raises KeyError
    with pytest.raises(KeyError):
        custom_reg.get("unknown_type")


def test_truss_geometry_generation_sweep() -> None:
    # Test across multiple node counts (3 to 8) and multiple RNG seeds
    for n in range(3, 9):
        for s in [42, 101, 777, 9999]:
            rng = np.random.default_rng(s)
            nodes, members, simplices = generate_truss_geometry(
                n, rng, min_angle=20.0, max_attempts=50
            )
            assert len(nodes) == n
            assert len(members) == 2 * n - 3


def test_determinate_strip_direct_generation() -> None:
    # Directly test the determinate strip builder for edge coverage
    rng = np.random.default_rng(12345)
    for n in [3, 4, 5, 6, 7]:
        nodes, members, simplices = _generate_determinate_strip(n, rng)
        assert len(nodes) == n
        assert len(members) >= n


def test_supports_selection_strategies() -> None:
    # Test support placement on different node configurations
    rng = np.random.default_rng(42)
    nodes, members, _ = generate_truss_geometry(5, rng)

    pin_supports, roller_supports = generate_supports(nodes, rng)
    assert len(pin_supports) == 1
    assert len(roller_supports) == 1
    assert "node_index" in pin_supports[0]
    assert "rotation" in roller_supports[0]

    # Test outward rotation helper
    centroid = np.array([2.0, 1.0])
    assert get_outward_rotation(np.array([2.0, -1.0]), centroid) == 0  # bottom -> 0
    assert get_outward_rotation(np.array([2.0, 3.0]), centroid) == 180  # top -> 180
    assert get_outward_rotation(np.array([5.0, 1.0]), centroid) == 90  # right -> 90
    assert get_outward_rotation(np.array([-1.0, 1.0]), centroid) == 270  # left -> 270

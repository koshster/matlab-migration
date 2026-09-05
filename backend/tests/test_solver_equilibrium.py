"""Physics-level guards on the truss solver.

Every other solver test in this suite is self-referential: it takes
``solve()``'s output, feeds it back into ``check()``, and asserts agreement.
That shape cannot fail. Negating the sign convention in
``solver.solve_member_forces`` leaves the whole suite green while making every
student's tension/compression answer wrong.

The tests here close that gap from two directions:

* ``test_hand_computed_*`` pins absolute values and signs against statics done
  by hand, with no call to the RNG. This is the test that fails on a sign flip.
* ``test_joint_equilibrium_*`` re-derives equilibrium from the *student-facing*
  geometry across a seed sweep, catching assembly and reaction errors. It is
  deliberately blind to a global sign flip -- a uniformly negated solution
  still satisfies equilibrium -- so it is not a substitute for the anchor.
"""

import math

import numpy as np
import pytest

from app.problems.truss.generator import TrussGenerator
from app.problems.truss.solver import solve_member_forces, solve_support_reactions

# A symmetric 45-45-90 truss with a single downward load on the apex.
#
#        2 (2,2)
#       / \            pin at node 0, roller at node 1, 10 kN down at node 2.
#      /   \           By symmetry Ay = By = 5.
#     0-----1          Diagonals: -5 / sin45 = -7.0711  (compression)
#   (0,0) (4,0)        Bottom chord: +7.0711 * cos45 = +5.0  (tension)
HAND_NODES = np.array([[0.0, 0.0], [4.0, 0.0], [2.0, 2.0]], dtype=float)
HAND_MEMBERS = np.array([[0, 1], [0, 2], [1, 2]], dtype=int)
HAND_PINS = [{"r": [0.0, 0.0], "node_index": 0}]
HAND_ROLLERS = [{"r": [4.0, 0.0], "node_index": 1, "rotation": 0}]
HAND_FORCES = [{"P": [2.0, 2.0], "F": [0.0, -10.0], "node_index": 2}]

SQRT2 = math.sqrt(2.0)


def test_hand_computed_reactions() -> None:
    """Reactions match statics done by hand, signs included."""
    r = solve_support_reactions(HAND_PINS, HAND_ROLLERS, HAND_FORCES)
    assert r["Ax"] == pytest.approx(0.0, abs=1e-9)
    assert r["Ay"] == pytest.approx(5.0, abs=1e-9)
    assert r["By"] == pytest.approx(5.0, abs=1e-9)


def test_hand_computed_member_forces_and_signs() -> None:
    """The sign anchor: tension positive, compression negative.

    A uniform sign flip anywhere in the solver fails here and nowhere else in
    the suite.
    """
    reactions = solve_support_reactions(HAND_PINS, HAND_ROLLERS, HAND_FORCES)
    s = solve_member_forces(
        HAND_NODES, HAND_MEMBERS, reactions, HAND_PINS, HAND_ROLLERS, HAND_FORCES
    )

    bottom_chord, left_diagonal, right_diagonal = s[0], s[1], s[2]

    # Bottom chord is pulled apart -> tension -> strictly positive.
    assert bottom_chord == pytest.approx(5.0, abs=1e-6)
    assert bottom_chord > 0

    # Both diagonals carry the load down to the supports -> compression.
    assert left_diagonal == pytest.approx(-5.0 * SQRT2, abs=1e-6)
    assert right_diagonal == pytest.approx(-5.0 * SQRT2, abs=1e-6)
    assert left_diagonal < 0
    assert right_diagonal < 0


def test_hand_computed_states_reach_the_student() -> None:
    """The Tension/Compression labels derived from those signs are correct."""
    gen = TrussGenerator()
    states = {}
    reactions = solve_support_reactions(HAND_PINS, HAND_ROLLERS, HAND_FORCES)
    forces = solve_member_forces(
        HAND_NODES, HAND_MEMBERS, reactions, HAND_PINS, HAND_ROLLERS, HAND_FORCES
    )
    for idx, (a, b) in enumerate(HAND_MEMBERS):
        value = float(forces[idx])
        states[f"member_{a}_{b}"] = "Tension" if value > 0 else "Compression"

    assert states["member_0_1"] == "Tension"
    assert states["member_0_2"] == "Compression"
    assert states["member_1_2"] == "Compression"
    assert gen.problem_type == "truss"


def _joint_residual(nodes, members, pins, rollers, forces, solution) -> float:
    """Largest unbalanced force at any joint, re-derived independently."""
    net = np.zeros((len(nodes), 2), dtype=float)

    for f in forces:
        net[f["node_index"]] += np.asarray(f["F"][:2], dtype=float)

    for a, b in members:
        value = solution["member_solutions"][f"member_{a}_{b}"]["signed_force"]
        direction = nodes[b] - nodes[a]
        unit = direction / np.linalg.norm(direction)
        # Tension pulls each joint toward the other end of the member.
        net[a] += value * unit
        net[b] -= value * unit

    reactions = solution["reactions"]
    for pin in pins:
        net[pin["node_index"]] += np.array(
            [reactions.get("Ax", 0.0), reactions.get("Ay", 0.0)], dtype=float
        )
    for roller in rollers:
        net[roller["node_index"]] += np.array(
            [reactions.get("Bx", 0.0), reactions.get("By", 0.0)], dtype=float
        )

    return float(np.max(np.linalg.norm(net, axis=1)))


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
@pytest.mark.parametrize("seed", [0, 1, 7, 42, 99, 1234])
def test_joint_equilibrium_holds(seed: int, num_nodes: int) -> None:
    """Every joint balances for generated problems.

    Catches assembly and reaction errors. Blind to a global sign flip by
    construction -- see test_hand_computed_member_forces_and_signs.
    """
    gen = TrussGenerator()
    params = {"num_nodes": num_nodes}
    nodes, members, pins, rollers, forces = gen._build_truss_instance(seed, params)
    solution = gen.solve(seed, params)

    assert _joint_residual(nodes, members, pins, rollers, forces, solution) < 1e-9


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_global_moment_balance_about_a_non_support_point(num_nodes: int) -> None:
    """Moments balance about an arbitrary point, not just the origin.

    The implementation takes moments about the origin, which is frequently the
    pin itself. Choosing a different pivot is an independent check.
    """
    gen = TrussGenerator()
    params = {"num_nodes": num_nodes}
    _nodes, _members, pins, rollers, forces = gen._build_truss_instance(1, params)
    reactions = gen.solve(1, params)["reactions"]

    pivot = np.array([-3.5, 7.25], dtype=float)
    moment = 0.0
    for f in forces:
        r = np.asarray(f["P"][:2], dtype=float) - pivot
        moment += r[0] * f["F"][1] - r[1] * f["F"][0]
    for pin in pins:
        r = np.asarray(pin["r"][:2], dtype=float) - pivot
        moment += r[0] * reactions.get("Ay", 0.0) - r[1] * reactions.get("Ax", 0.0)
    for roller in rollers:
        r = np.asarray(roller["r"][:2], dtype=float) - pivot
        moment += r[0] * reactions.get("By", 0.0) - r[1] * reactions.get("Bx", 0.0)

    assert abs(moment) < 1e-9


# ---------------------------------------------------------------------------
# Problem quality
#
# A zero-force member is valid statics, so the equilibrium tests above are
# perfectly happy with a problem whose answer is "0, 0, 0, 0, -3, 0, 0, 0, 0".
# Correctness and usefulness are different axes; these pin the second one.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("num_nodes", [4, 5, 6, 7, 8])
def test_most_members_actually_carry_load(num_nodes: int) -> None:
    """Zero-force members must stay a minority across a seed sweep.

    Regression guard: with axis-aligned loads on an integer grid and a single
    applied load, 58% of all member forces came out exactly zero.
    """
    gen = TrussGenerator()
    zero = total = 0
    for seed in range(200):
        solution = gen.solve(seed, {"num_nodes": num_nodes})
        for entry in solution["member_solutions"].values():
            total += 1
            if abs(entry["signed_force"]) < 5e-3:
                zero += 1

    ratio = zero / total
    assert ratio < 0.35, f"{ratio:.1%} of members carry no load at n={num_nodes}"


def test_problems_have_a_variety_of_answers() -> None:
    """A student should not be typing the same number into most of the boxes."""
    gen = TrussGenerator()
    too_uniform = 0
    trials = 200

    for seed in range(trials):
        solution = gen.solve(seed, {"num_nodes": 6})
        values = {
            round(entry["signed_force"], 2) + 0.0 for entry in solution["member_solutions"].values()
        }
        # Nine members with two or fewer distinct answers reads as broken.
        if len(values) <= 2:
            too_uniform += 1

    assert too_uniform == 0, f"{too_uniform}/{trials} nine-member problems had <=2 distinct answers"

"""Matrix equilibrium physics solver for 2D statically determinate trusses.

Implements the standard method of joints via linear algebra:
1. Support Reactions: Solves global rigid-body equilibrium:
   - sum(Fx) = 0 (Horizontal force equilibrium)
   - sum(Fy) = 0 (Vertical force equilibrium)
   - sum(M_pin) = 0 (Moment equilibrium about the pin support)
2. Member Forces: Solves the global joint equilibrium matrix:
   - A * s = b
   Where A contains the unit directional cosines of members at each joint,
   s is the unknown member forces vector, and b contains external loads & reactions.
   Sign convention: s > 0 indicates Tension (T), s < 0 indicates Compression (C).
"""

from typing import Any

import numpy as np


def solve_support_reactions(
    pin_supports: list[dict[str, Any]],
    roller_supports: list[dict[str, Any]],
    forces: list[dict[str, Any]],
    moments: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    """Solve for 2D external support reaction forces under static equilibrium.

    Calculates the 3 external reaction components (Ax, Ay at the pin support,
    and Bx or By at the roller support) by solving the 3 global equilibrium equations:
    - sum(Fx) = 0
    - sum(Fy) = 0
    - sum(M) = 0

    Args:
        pin_supports: List containing pin support position and node index.
        roller_supports: List containing roller support position, rotation, and node index.
        forces: List of applied external point loads with magnitude and application points.
        moments: Optional list of applied concentrated external moments.

    Returns:
        Dictionary mapping reaction force names (e.g. 'Ax', 'By') to their numerical values (kN).
    """
    if moments is None:
        moments = []

    # Step 1: Accumulate total external forces and moments into load vector b
    b = np.zeros(3)
    for f in forces:
        fx, fy = f["F"]
        px, py = f["P"]
        b[0] -= fx  # -sum(Fx_ext)
        b[1] -= fy  # -sum(Fy_ext)
        b[2] -= -fx * py + fy * px  # -sum(Moment_ext about origin)

    for m in moments:
        b[2] -= m["M"]

    num_pins = len(pin_supports)
    num_rollers = len(roller_supports)

    # Standard statically determinate support configuration: 1 pin + 1 roller (3 unknowns)
    if num_pins == 1 and num_rollers == 1:
        pin = pin_supports[0]
        roller = roller_supports[0]

        pin_r = np.array(pin["r"], dtype=float)
        roller_r = np.array(roller["r"], dtype=float)
        rot = roller.get("rotation", 0)

        # A vertical roller (rot 0 or 180) provides vertical reaction By.
        # A horizontal roller (rot 90 or 270) provides horizontal reaction Bx.
        if rot in (90, 270):
            roller_x_coeff, roller_y_coeff = 1.0, 0.0
            roller_name = "Bx"
        else:
            roller_x_coeff, roller_y_coeff = 0.0, 1.0
            roller_name = "By"

        # Construct the 3x3 equilibrium coefficient matrix A_mat
        # Row 0: Fx equilibrium (Ax + roller_x = b[0])
        # Row 1: Fy equilibrium (Ay + roller_y = b[1])
        # Row 2: Moment equilibrium about origin (-Ax*py + Ay*px + M_roller = b[2])
        a_mat = np.array(
            [
                [1.0, 0.0, roller_x_coeff],
                [0.0, 1.0, roller_y_coeff],
                [
                    -pin_r[1],
                    pin_r[0],
                    -roller_x_coeff * roller_r[1] + roller_y_coeff * roller_r[0],
                ],
            ],
            dtype=float,
        )

        # Solve system: A_mat * [Ax, Ay, B] = b
        res = np.linalg.solve(a_mat, b)
        return {
            "Ax": float(res[0]),
            "Ay": float(res[1]),
            roller_name: float(res[2]),
        }

    raise NotImplementedError(
        f"Unsupported support configuration: {num_pins} pins, {num_rollers} rollers"
    )


def solve_member_forces(
    node_coords: np.ndarray,
    members: np.ndarray,
    reactions: dict[str, float],
    pin_supports: list[dict[str, Any]],
    roller_supports: list[dict[str, Any]],
    forces: list[dict[str, Any]],
) -> np.ndarray:
    """Solve for internal member forces in a 2D planar truss using the method of joints.

    Assembles the 2N x M joint equilibrium equations (Fx = 0 and Fy = 0 at every joint):
    A * s = b
    where unit directional cosines are calculated from member end-to-end vectors.

    Args:
        node_coords: N x 2 array of node positions.
        members: M x 2 array of member connectivity (start_node, end_node indices).
        reactions: Dictionary of computed external support reactions (Ax, Ay, Bx/By).
        pin_supports: List of pin support configurations.
        roller_supports: List of roller support configurations.
        forces: List of applied point load dictionaries.

    Returns:
        Array of M internal member forces (s > 0: Tension, s < 0: Compression).
    """
    n_nodes = len(node_coords)
    n_members = len(members)

    # Step 1: Assign support reaction vectors to their corresponding joint indices
    support_x = np.zeros(n_nodes)
    support_y = np.zeros(n_nodes)

    for pin in pin_supports:
        pin_r = np.array(pin["r"], dtype=float)
        dists = np.linalg.norm(node_coords - pin_r, axis=1)
        node_idx = int(np.argmin(dists))
        support_x[node_idx] += reactions.get("Ax", 0.0)
        support_y[node_idx] += reactions.get("Ay", 0.0)

    for roller in roller_supports:
        roller_r = np.array(roller["r"], dtype=float)
        dists = np.linalg.norm(node_coords - roller_r, axis=1)
        node_idx = int(np.argmin(dists))
        support_x[node_idx] += reactions.get("Bx", 0.0)
        support_y[node_idx] += reactions.get("By", 0.0)

    # Step 2: Assign external applied point loads to their corresponding joint indices
    load_x = np.zeros(n_nodes)
    load_y = np.zeros(n_nodes)
    for f in forces:
        px, py = f["P"]
        fx, fy = f["F"]
        dists = np.linalg.norm(node_coords - np.array([px, py]), axis=1)
        node_idx = int(np.argmin(dists))
        load_x[node_idx] += fx
        load_y[node_idx] += fy

    # Step 3: Assemble the 2N global load equilibrium vector b_vec
    # At each joint i: sum(F_internal) + F_applied + F_reaction = 0
    # => sum(F_internal) = -(F_applied + F_reaction)
    b_vec = np.zeros(2 * n_nodes)
    for i in range(n_nodes):
        b_vec[2 * i] = -(load_x[i] + support_x[i])
        b_vec[2 * i + 1] = -(load_y[i] + support_y[i])

    # Step 4: Assemble the 2N x M equilibrium matrix A_mat
    # For each member connecting node u to node v, compute unit direction vector:
    # u_dir = (p_v - p_u) / length
    # A_mat contribution at node u: +u_dir
    # A_mat contribution at node v: -u_dir
    a_mat = np.zeros((2 * n_nodes, n_members))

    for m_idx, (u, v) in enumerate(members):
        u, v = int(u), int(v)
        p_u = node_coords[u]
        p_v = node_coords[v]
        vec = p_v - p_u
        length = float(np.linalg.norm(vec))
        unit_vec = vec / length

        # Node u equations (Fx and Fy)
        a_mat[2 * u, m_idx] = unit_vec[0]
        a_mat[2 * u + 1, m_idx] = unit_vec[1]

        # Node v equations (Fx and Fy)
        a_mat[2 * v, m_idx] = -unit_vec[0]
        a_mat[2 * v + 1, m_idx] = -unit_vec[1]

    # Step 5: Solve the linear system A_mat * s = b_vec using least-squares/exact solve
    s_forces, _, _, _ = np.linalg.lstsq(a_mat, b_vec, rcond=None)
    return s_forces

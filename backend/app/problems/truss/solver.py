from typing import Any

import numpy as np


def solve_support_reactions(
    pin_supports: list[dict[str, Any]],
    roller_supports: list[dict[str, Any]],
    forces: list[dict[str, Any]],
    moments: list[dict[str, Any]] | None = None,
) -> dict[str, float]:
    """Solve for 2D external support reaction forces under static equilibrium.

    Eqs: sum(Fx) = 0, sum(Fy) = 0, sum(M_pin) = 0
    """
    if moments is None:
        moments = []

    b = np.zeros(3)
    for f in forces:
        fx, fy = f["F"]
        px, py = f["P"]
        b[0] -= fx
        b[1] -= fy
        b[2] -= -fx * py + fy * px

    for m in moments:
        b[2] -= m["M"]

    num_pins = len(pin_supports)
    num_rollers = len(roller_supports)

    if num_pins == 1 and num_rollers == 1:
        pin = pin_supports[0]
        roller = roller_supports[0]

        pin_r = np.array(pin["r"], dtype=float)
        roller_r = np.array(roller["r"], dtype=float)
        rot = roller.get("rotation", 0)

        if rot in (90, 270):
            roller_x_coeff, roller_y_coeff = 1.0, 0.0
            roller_name = "Bx"
        else:
            roller_x_coeff, roller_y_coeff = 0.0, 1.0
            roller_name = "By"

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
    """Solve for internal member forces in a 2D planar truss using joint equilibrium.

    Uses equilibrium matrix A * s = b.
    Returns array of member axial forces S (S > 0: Tension, S < 0: Compression).
    """
    n_nodes = len(node_coords)
    n_members = len(members)

    # 1. Support reaction vectors per node
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
        rot = roller.get("rotation", 0)
        r_val = reactions.get("Bx", 0.0) if rot in (90, 270) else reactions.get("By", 0.0)

        if rot in (0, 180):
            support_y[node_idx] += r_val
        elif rot in (90, 270):
            support_x[node_idx] += r_val

    # 2. External applied force vectors per node
    external_x = np.zeros(n_nodes)
    external_y = np.zeros(n_nodes)
    for f in forces:
        f_pos = np.array(f["P"], dtype=float)
        dists = np.linalg.norm(node_coords - f_pos, axis=1)
        node_idx = int(np.argmin(dists))
        fx, fy = f["F"]
        external_x[node_idx] += fx
        external_y[node_idx] += fy

    # 3. Build joint equilibrium matrix (2 * n_nodes equations)
    a_mat = np.zeros((2 * n_nodes, n_members))
    b = np.zeros(2 * n_nodes)

    member_con: list[list[int]] = [[] for _ in range(n_nodes)]
    for m_idx, (n1, n2) in enumerate(members):
        member_con[n1].append(m_idx)
        member_con[n2].append(m_idx)

    eqn = 0
    for joint in range(n_nodes):
        for dim in range(2):  # dim 0 = x, dim 1 = y
            for mem_idx in member_con[joint]:
                n1, n2 = members[mem_idx]
                pos_a = node_coords[n1]
                pos_b = node_coords[n2]
                if joint == n1:
                    unit_dir = (pos_b - pos_a) / np.linalg.norm(pos_b - pos_a)
                else:
                    unit_dir = (pos_a - pos_b) / np.linalg.norm(pos_a - pos_b)
                a_mat[eqn, mem_idx] = unit_dir[dim]

            b[eqn] = -(
                support_x[joint] + external_x[joint]
                if dim == 0
                else support_y[joint] + external_y[joint]
            )
            eqn += 1

    # Filter zero rows (unconstrained nodes with no unknowns)
    row_sums = np.sum(np.abs(a_mat), axis=1)
    keep_rows = row_sums > 1e-5

    a_filtered = a_mat[keep_rows]
    b_filtered = b[keep_rows]

    # Solve linear system using least squares / solve
    s_forces, _, _, _ = np.linalg.lstsq(a_filtered, b_filtered, rcond=None)
    return s_forces

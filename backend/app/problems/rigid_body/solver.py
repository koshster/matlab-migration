"""2D Rigid Body static equilibrium physics solver.

Solves global 2D static equilibrium equations for unknown support reactions and moments:
1. sum(Fx) = 0 (Horizontal equilibrium)
2. sum(Fy) = 0 (Vertical equilibrium)
3. sum(Mo) = 0 (Moment equilibrium about origin)
"""

from typing import Any

import numpy as np


def solve_rigid_body_reactions(
    supports: dict[str, list[dict[str, Any]]],
    loads: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    """Solve for 2D external reactions under static equilibrium.

    Args:
        supports: Dictionary containing 'walls', 'fixed_pins', and 'rollers' lists.
        loads: Dictionary containing 'forces' and 'moments' lists.

    Returns:
        Dictionary mapping reaction names (e.g. 'Ax', 'Ay', 'By', 'MA')
        to numerical values in kN / kN-m.
    """
    forces = loads.get("forces", [])
    moments = loads.get("moments", [])
    walls = supports.get("walls", [])
    fixed_pins = supports.get("fixed_pins", [])
    rollers = supports.get("rollers", [])

    # Step 1: Accumulate total external loads into equilibrium vector b in R^3
    b = np.zeros(3, dtype=float)
    for f in forces:
        fx, fy = float(f["F"][0]), float(f["F"][1])
        px, py = float(f["P"][0]), float(f["P"][1])
        b[0] -= fx
        b[1] -= fy
        # Moment about origin: r x F = px * fy - py * fx
        b[2] -= (-fx * py + fy * px)

    for m in moments:
        b[2] -= float(m["M"])

    n_walls = len(walls)
    n_pins = len(fixed_pins)
    n_rollers = len(rollers)

    # Case 2: 1 Fixed Pin + 1 Roller
    if n_pins == 1 and n_rollers == 1:
        pin = fixed_pins[0]
        roller = rollers[0]
        pin_x, pin_y = float(pin["r"][0]), float(pin["r"][1])
        roller_x, roller_y = float(roller["r"][0]), float(roller["r"][1])
        roller_rot = int(roller.get("rotation", 0))

        if roller_rot in (90, 270):
            roller_x_coeff, roller_y_coeff = 1.0, 0.0
            roller_name = "Bx"
        else:
            roller_x_coeff, roller_y_coeff = 0.0, 1.0
            roller_name = "By"

        # 3x3 Equilibrium matrix
        # Row 0: Fx -> Ax + roller_x_coeff * B = b[0]
        # Row 1: Fy -> Ay + roller_y_coeff * B = b[1]
        # Row 2: Mo -> -pin_y * Ax + pin_x * Ay + M_arm * B = b[2]
        a_mat = np.array(
            [
                [1.0, 0.0, roller_x_coeff],
                [0.0, 1.0, roller_y_coeff],
                [
                    -pin_y,
                    pin_x,
                    -roller_x_coeff * roller_y + roller_y_coeff * roller_x,
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

    # Case 1: 3 Rollers
    if n_rollers == 3 and n_pins == 0 and n_walls == 0:
        support_names = ["A", "B", "C"]
        col_names: list[str] = []
        a_cols: list[np.ndarray] = []

        for i in range(3):
            r = rollers[i]
            rx, ry = float(r["r"][0]), float(r["r"][1])
            rot = int(r.get("rotation", 0))

            if rot in (90, 270):
                cx, cy = 1.0, 0.0
                col_names.append(f"{support_names[i]}x")
            else:
                cx, cy = 0.0, 1.0
                col_names.append(f"{support_names[i]}y")

            moment_arm = -cx * ry + cy * rx
            a_cols.append(np.array([cx, cy, moment_arm], dtype=float))

        a_mat = np.column_stack(a_cols)
        res = np.linalg.solve(a_mat, b)
        return {
            col_names[0]: float(res[0]),
            col_names[1]: float(res[1]),
            col_names[2]: float(res[2]),
        }

    # Case 3: 1 Fixed Wall Support
    if n_walls == 1 and n_pins == 0 and n_rollers == 0:
        wall = walls[0]
        wx, wy = float(wall["r"][0]), float(wall["r"][1])

        ax = float(b[0])
        ay = float(b[1])
        # Sum of moments about wall: b[2] - (-ax * wy + ay * wx)
        ma = float(b[2] - (-ax * wy + ay * wx))

        return {
            "Ax": ax,
            "Ay": ay,
            "MA": ma,
        }

    raise ValueError(
        f"Unsupported or indeterminate support configuration: "
        f"{n_pins} pins, {n_rollers} rollers, {n_walls} walls"
    )

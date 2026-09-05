"""2D Rigid Body static equilibrium physics solver.

This module ports the legacy MATLAB `+solverPkg` (`findSolutions.m`).
It sets up and solves the classical 3 equations of static equilibrium for a 2D planar body:

    1. Horizontal Force Equilibrium:
       sum(Fx) = 0  =>  sum(Fx_reactions) + sum(Fx_applied) = 0
       => sum(Fx_reactions) = -sum(Fx_applied)

    2. Vertical Force Equilibrium:
       sum(Fy) = 0  =>  sum(Fy_reactions) + sum(Fy_applied) = 0
       => sum(Fy_reactions) = -sum(Fy_applied)

    3. Moment Equilibrium about Origin (0, 0):
       sum(Mo) = 0  =>  sum(Mo_reactions) + sum(Mo_applied) = 0
       => sum(Mo_reactions) = -sum(Mo_applied)

Cross-Product Formulation for 2D Moment:
    For a force F = (fx, fy) applied at point P = (px, py), the moment about the origin is:
    Mo = r x F = px * fy - py * fx = -fx * py + fy * px
    Counterclockwise (CCW) is taken as positive (+), Clockwise (CW) is negative (-).
"""

from typing import Any

import numpy as np


def solve_rigid_body_reactions(
    supports: dict[str, list[dict[str, Any]]],
    loads: dict[str, list[dict[str, Any]]],
) -> dict[str, float]:
    """Solve for 2D external reactions under static equilibrium.

    Sets up the linear system A * x = b in R^3:
        - Vector b: Net negative applied forces and moments (-sum Fx, -sum Fy, -sum Mo).
        - Matrix A: Reaction force unit vectors and moment arms about the origin.
        - Vector x: Unknown support reaction forces and moments.

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

    # Step 1: Accumulate total external loads into the load vector b in R^3
    # b[0] = -sum(Fx_applied)
    # b[1] = -sum(Fy_applied)
    # b[2] = -sum(Mo_applied)
    b = np.zeros(3, dtype=float)

    for f in forces:
        fx, fy = float(f["F"][0]), float(f["F"][1])
        px, py = float(f["P"][0]), float(f["P"][1])
        b[0] -= fx
        b[1] -= fy
        # Moment about origin: r x F = px * fy - py * fx = -fx * py + fy * px
        b[2] -= -fx * py + fy * px

    for m in moments:
        # Couple moments add directly to the global moment equilibrium
        b[2] -= float(m["M"])

    n_walls = len(walls)
    n_pins = len(fixed_pins)
    n_rollers = len(rollers)

    # -------------------------------------------------------------------------
    # Case 2: 1 Fixed Pin at Joint A + 1 Roller at Joint B (Standard Statics Case)
    # Unknowns: Ax, Ay, and Roller Reaction B
    # -------------------------------------------------------------------------
    if n_pins == 1 and n_rollers == 1:
        pin = fixed_pins[0]
        roller = rollers[0]
        pin_x, pin_y = float(pin["r"][0]), float(pin["r"][1])
        roller_x, roller_y = float(roller["r"][0]), float(roller["r"][1])
        roller_rot = int(roller.get("rotation", 0))

        # A vertical roller (rot 0 or 180) provides vertical reaction By.
        # A horizontal roller (rot 90 or 270) provides horizontal reaction Bx.
        if roller_rot in (90, 270):
            roller_x_coeff, roller_y_coeff = 1.0, 0.0
            roller_name = "Bx"
        else:
            roller_x_coeff, roller_y_coeff = 0.0, 1.0
            roller_name = "By"

        # Construct 3x3 Equilibrium Coefficient Matrix A:
        # Row 0: Fx equilibrium -> 1*Ax + 0*Ay + (roller_x_coeff)*B = b[0]
        # Row 1: Fy equilibrium -> 0*Ax + 1*Ay + (roller_y_coeff)*B = b[1]
        # Row 2: Mo equilibrium -> (-pin_y)*Ax + (pin_x)*Ay + (-cx*ry + cy*rx)*B = b[2]
        moment_arm_roller = -roller_x_coeff * roller_y + roller_y_coeff * roller_x
        a_mat = np.array(
            [
                [1.0, 0.0, roller_x_coeff],
                [0.0, 1.0, roller_y_coeff],
                [-pin_y, pin_x, moment_arm_roller],
            ],
            dtype=float,
        )

        res = np.linalg.solve(a_mat, b)
        return {
            "Ax": float(res[0]),
            "Ay": float(res[1]),
            roller_name: float(res[2]),
        }

    # -------------------------------------------------------------------------
    # Case 1: 3 Independent Roller Supports at Joints A, B, and C
    # Unknowns: Reaction forces R_A, R_B, R_C normal to each roller surface
    # -------------------------------------------------------------------------
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

            # Moment arm of roller reaction about origin: -cx * ry + cy * rx
            moment_arm = -cx * ry + cy * rx
            a_cols.append(np.array([cx, cy, moment_arm], dtype=float))

        a_mat = np.column_stack(a_cols)
        res = np.linalg.solve(a_mat, b)
        return {
            col_names[0]: float(res[0]),
            col_names[1]: float(res[1]),
            col_names[2]: float(res[2]),
        }

    # -------------------------------------------------------------------------
    # Case 3: 1 Fixed Cantilever Wall Support at Joint A
    # Unknowns: Horizontal reaction Ax, vertical reaction Ay, reaction moment MA
    # -------------------------------------------------------------------------
    if n_walls == 1 and n_pins == 0 and n_rollers == 0:
        wall = walls[0]
        wx, wy = float(wall["r"][0]), float(wall["r"][1])

        # Ax and Ay balance net external horizontal and vertical forces directly
        ax = float(b[0])
        ay = float(b[1])
        # Sum of moments about wall: MA = b[2] - (-Ax * wy + Ay * wx) = b[2] + Ax*wy - Ay*wx
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

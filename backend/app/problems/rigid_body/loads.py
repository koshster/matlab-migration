"""2D Rigid Body external applied load generation (point forces and couple moments).

This module ports the legacy MATLAB `+loadPkg` (`getLoadProfile.m`, `generateLoads.m`,
`genForces.m`, and `genMoments.m`).

Applied Load Formulations:
1. Applied Point Loads (Concentrated Forces):
   - Applied at unsupported body nodes.
   - Vector format: F = [fx, fy] where forces act along cardinal axes:
     - Vertical loads:   +fy (pointing upward),   -fy (pointing downward)
     - Horizontal loads: +fx (pointing rightward), -fx (pointing leftward)
   - Magnitude: Integer kN values from 1 to max_magnitude (e.g. 1F, 2F, 3F, 4F, 5F).
2. Concentrated Couple Moments:
   - Applied at unsupported body nodes.
   - Magnitude: Integer values 1 to 5 (represented in problems as M * Fa).
   - Sign / Direction convention:
     - Direction = +1: Counterclockwise (CCW / positive moment around +z axis).
     - Direction = -1: Clockwise (CW / negative moment around +z axis).
   - Label & Arrow Offset: Dynamically offset away from connected members so the
     moment arc and text label do not collide with adjacent body segments.
"""

from typing import Any

import numpy as np


def generate_forces(
    free_nodes: np.ndarray,
    free_surroundings: np.ndarray,
    n_forces: int,
    rng: np.random.Generator,
    max_magnitude: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Generate external applied point loads on unconstrained rigid body nodes.

    Args:
        free_nodes: (K, 2) array of available unsupported nodes.
        free_surroundings: (K, 4) boolean surroundings of available nodes.
        n_forces: Number of point forces to generate.
        rng: Explicit NumPy random number generator instance.
        max_magnitude: Maximum load magnitude in kN (default: 5.0).

    Returns:
        tuple of (remaining_nodes, remaining_surroundings, forces_list):
            - remaining_nodes: free nodes remaining after force placement.
            - remaining_surroundings: surroundings flags for remaining nodes.
            - forces_list: list of force dictionaries with position P, vector F, and label.
    """
    if n_forces <= 0 or len(free_nodes) == 0:
        return free_nodes, free_surroundings, []

    count = min(n_forces, len(free_nodes))
    chosen_indices = rng.choice(len(free_nodes), size=count, replace=False)

    forces: list[dict[str, Any]] = []
    free_nodes_list = [free_nodes[i].copy() for i in range(len(free_nodes))]
    free_surroundings_list = [free_surroundings[i].copy() for i in range(len(free_surroundings))]

    for k, chosen_idx in enumerate(chosen_indices):
        pos = free_nodes[chosen_idx]
        surr = free_surroundings[chosen_idx]

        # Integer force magnitude 1..max_magnitude
        if k == 0 and count == 1:
            mag = float(rng.integers(1, int(max_magnitude) + 1))
        else:
            mag = float(rng.integers(1, int(max_magnitude) + 1))

        # 50% probability vertical load, 50% horizontal load
        if rng.random() <= 0.5:
            # Vertical load: 50% up (+y), 50% down (-y)
            fy = mag if rng.random() < 0.5 else -mag
            fx = 0.0
        else:
            # Horizontal load: 50% right (+x), 50% left (-x)
            fx = mag if rng.random() < 0.5 else -mag
            fy = 0.0

        label = "F" if mag == 1.0 else f"{int(mag)}F"

        forces.append(
            {
                "P": pos.tolist(),
                "F": [fx, fy],
                "magnitude": mag,
                "label": label,
                "surroundings": surr.tolist(),
            }
        )

    # Remove selected nodes from candidate list
    for idx in sorted(chosen_indices, reverse=True):
        free_nodes_list.pop(int(idx))
        free_surroundings_list.pop(int(idx))

    rem_nodes = (
        np.array(free_nodes_list, dtype=int) if free_nodes_list else np.empty((0, 2), dtype=int)
    )
    rem_surr = (
        np.array(free_surroundings_list, dtype=bool)
        if free_surroundings_list
        else np.empty((0, 4), dtype=bool)
    )

    return rem_nodes, rem_surr, forces


def generate_moments(
    free_nodes: np.ndarray,
    free_surroundings: np.ndarray,
    n_moments: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Generate concentrated external couple moments on unsupported rigid body nodes.

    Calculates drawing arc angles and label offsets to prevent collision with
    structural members connected at the node.

    Args:
        free_nodes: (K, 2) array of available unsupported nodes.
        free_surroundings: (K, 4) boolean surroundings of available nodes.
        n_moments: Number of concentrated moments to generate.
        rng: Explicit NumPy random number generator instance.

    Returns:
        tuple of (remaining_nodes, remaining_surroundings, moments_list).
    """
    if n_moments <= 0 or len(free_nodes) == 0:
        return free_nodes, free_surroundings, []

    count = min(n_moments, len(free_nodes))
    chosen_indices = rng.choice(len(free_nodes), size=count, replace=False)

    moments: list[dict[str, Any]] = []
    free_nodes_list = [free_nodes[i].copy() for i in range(len(free_nodes))]
    free_surroundings_list = [free_surroundings[i].copy() for i in range(len(free_surroundings))]

    for chosen_idx in chosen_indices:
        pos = free_nodes[chosen_idx]
        surr = free_surroundings[chosen_idx]

        # Integer moment magnitude 1..5 kN-m (matching MATLAB Fa units)
        mag = float(rng.integers(1, 6))

        # Direction: +1 (CCW / positive moment) or -1 (CW / negative moment)
        direction = 1 if rng.random() < 0.5 else -1
        signed_m = mag * direction

        # Determine non-overlapping arc arrow angle and label text offset
        surr_sum = int(np.sum(surr))
        arrow_angle = 0
        arc_angle = 200
        dx = 0.3
        dy = 0.45

        # Single attached member (terminal dead-end joint)
        if surr_sum == 1:
            if surr[0]:  # Member extends +x
                arrow_angle, dx, dy = 180, -0.6, 0.45
            elif surr[1]:  # Member extends +y
                arrow_angle, dx, dy = 270, 0.3, -0.45
            elif surr[2]:  # Member extends -x
                arrow_angle, dx, dy = 0, 0.3, 0.45
            else:  # Member extends -y
                arrow_angle, dx, dy = 90, 0.3, 0.45

        # Two attached members (corner or straight joint)
        elif surr_sum == 2:
            if surr[0] and surr[3]:  # +x and -y
                arrow_angle, dx, dy = 335, -0.6, 0.3
            elif surr[0] and surr[1]:  # +x and +y
                arrow_angle, dx, dy = 45, -0.6, -0.3
            elif surr[2] and surr[3]:  # -x and -y
                arrow_angle, dx, dy = 225, 0.3, 0.3
            elif surr[1] and surr[2]:  # +y and -x
                arrow_angle, dx, dy = 135, 0.3, 0.3
            elif surr[1] and surr[3]:  # Vertical line
                arrow_angle, dx, dy = 90, 0.3, -0.35
            elif surr[0] and surr[2]:  # Horizontal line
                arrow_angle, dx, dy = 0, 0.4, 0.4

        # Three attached members (T-junction)
        elif surr_sum == 3:
            if not surr[0]:  # Open on +x
                arrow_angle, dx, dy = 180, 0.4, 0.4
            elif not surr[1]:  # Open on +y
                arrow_angle, dx, dy = 270, 0.4, 0.4
            elif not surr[2]:  # Open on -x
                arrow_angle, dx, dy = 0, -0.5, -0.4
            else:  # Open on -y
                arrow_angle, dx, dy = 90, -0.4, -0.4

        # Four attached members (cross-junction)
        else:
            arc_angle = 300

        label = "Fa" if mag == 1.0 else f"{int(mag)}Fa"

        moments.append(
            {
                "P": pos.tolist(),
                "M": signed_m,
                "magnitude": mag,
                "direction": direction,
                "radius": 0.2,
                "arrow_angle": arrow_angle,
                "arc_angle": arc_angle,
                "label_offset": [dx, dy],
                "label": label,
            }
        )

    for idx in sorted(chosen_indices, reverse=True):
        free_nodes_list.pop(int(idx))
        free_surroundings_list.pop(int(idx))

    rem_nodes = (
        np.array(free_nodes_list, dtype=int) if free_nodes_list else np.empty((0, 2), dtype=int)
    )
    rem_surr = (
        np.array(free_surroundings_list, dtype=bool)
        if free_surroundings_list
        else np.empty((0, 4), dtype=bool)
    )

    return rem_nodes, rem_surr, moments


def generate_loads(
    free_nodes: np.ndarray,
    free_surroundings: np.ndarray,
    rng: np.random.Generator,
    n_forces: int = 2,
    n_moments: int = 0,
    max_force: float = 5.0,
) -> dict[str, list[dict[str, Any]]]:
    """Generate both applied point loads and concentrated moments for the rigid body.

    Args:
        free_nodes: (K, 2) array of available unsupported nodes.
        free_surroundings: (K, 4) boolean connectivity array.
        rng: Explicit NumPy random number generator instance.
        n_forces: Number of point forces to generate.
        n_moments: Number of concentrated moments to generate.
        max_force: Maximum load magnitude (kN).

    Returns:
        dict containing 'forces' list and 'moments' list.
    """
    nodes_after_forces, surr_after_forces, forces = generate_forces(
        free_nodes, free_surroundings, n_forces, rng, max_magnitude=max_force
    )
    _, _, moments = generate_moments(nodes_after_forces, surr_after_forces, n_moments, rng)
    return {"forces": forces, "moments": moments}

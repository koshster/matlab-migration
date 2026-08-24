"""2D Rigid Body external applied load generation (point forces and couple moments).

Generates applied point loads with Cartesian force vectors (+x, -x, +y, -y) and
concentrated external moments (CCW / CW) placed on unsupported body nodes.
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
        max_magnitude: Maximum load magnitude (kN).

    Returns:
        tuple of (remaining_nodes, remaining_surroundings, forces_list).
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

        # 50% vertical, 50% horizontal
        if rng.random() <= 0.5:
            # Vertical (+y or -y)
            fy = mag if rng.random() < 0.5 else -mag
            fx = 0.0
        else:
            # Horizontal (+x or -x)
            fx = mag if rng.random() < 0.5 else -mag
            fy = 0.0

        label = "F" if mag == 1.0 else f"{int(mag)}F"

        forces.append({
            "P": pos.tolist(),
            "F": [fx, fy],
            "magnitude": mag,
            "label": label,
            "surroundings": surr.tolist(),
        })

    # Remove selected nodes
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

        # Direction: +1 (CCW) or -1 (CW)
        direction = 1 if rng.random() < 0.5 else -1
        signed_m = mag * direction

        # Arrow placement angle and label offset based on surroundings
        surr_sum = int(np.sum(surr))
        arrow_angle = 0
        arc_angle = 200
        dx = 0.3
        dy = 0.45

        if surr_sum == 1:
            if surr[0]:  # +x
                arrow_angle, dx, dy = 180, -0.6, 0.45
            elif surr[1]:  # +y
                arrow_angle, dx, dy = 270, 0.3, -0.45
            elif surr[2]:  # -x
                arrow_angle, dx, dy = 0, 0.3, 0.45
            else:  # -y
                arrow_angle, dx, dy = 90, 0.3, 0.45
        elif surr_sum == 2:
            if surr[0] and surr[3]:
                arrow_angle, dx, dy = 335, -0.6, 0.3
            elif surr[0] and surr[1]:
                arrow_angle, dx, dy = 45, -0.6, -0.3
            elif surr[2] and surr[3]:
                arrow_angle, dx, dy = 225, 0.3, 0.3
            elif surr[1] and surr[2]:
                arrow_angle, dx, dy = 135, 0.3, 0.3
            elif surr[1] and surr[3]:
                arrow_angle, dx, dy = 90, 0.3, -0.35
            elif surr[0] and surr[2]:
                arrow_angle, dx, dy = 0, 0.4, 0.4
        elif surr_sum == 3:
            if not surr[0]:
                arrow_angle, dx, dy = 180, 0.4, 0.4
            elif not surr[1]:
                arrow_angle, dx, dy = 270, 0.4, 0.4
            elif not surr[2]:
                arrow_angle, dx, dy = 0, -0.5, -0.4
            else:
                arrow_angle, dx, dy = 90, -0.4, -0.4
        else:
            arc_angle = 300

        label = "Fa" if mag == 1.0 else f"{int(mag)}Fa"

        moments.append({
            "P": pos.tolist(),
            "M": signed_m,
            "magnitude": mag,
            "direction": direction,
            "radius": 0.2,
            "arrow_angle": arrow_angle,
            "arc_angle": arc_angle,
            "label_offset": [dx, dy],
            "label": label,
        })

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
    _, _, moments = generate_moments(
        nodes_after_forces, surr_after_forces, n_moments, rng
    )
    return {"forces": forces, "moments": moments}

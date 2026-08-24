"""2D Rigid Body support placement, rotation orientation, and static determinacy checks.

Supports three standard structural boundary conditions:
1. One Pin + One Roller (Standard 3-reaction statically determinate equilibrium)
2. Three Rollers (Non-parallel, non-collinear 3-reaction roller configuration)
3. One Fixed Cantilever Wall (3-reaction fixed base: Ax, Ay, and MA)
"""

from typing import Any

import numpy as np


def good_pin_support_orientation(node_surroundings: np.ndarray, rotation_angle: int) -> bool:
    """Check if support drawing orientation does not collide with rigid body segments.

    Args:
        node_surroundings: 4-boolean array [+x, +y, -x, -y] of connected body segments.
        rotation_angle: Candidate drawing angle in degrees (0, 90, 180, 270).

    Returns:
        True if the support base does not collide with a body segment.
    """
    # 0 deg: base placed below node (requires no downward segment: index 3)
    if rotation_angle == 0:
        return not bool(node_surroundings[3])
    # 90 deg: base placed to left of node (requires no rightward segment: index 0)
    elif rotation_angle == 90:
        return not bool(node_surroundings[0])
    # 180 deg: base placed above node (requires no upward segment: index 1)
    elif rotation_angle == 180:
        return not bool(node_surroundings[1])
    # 270 deg: base placed to right of node (requires no leftward segment: index 2)
    elif rotation_angle == 270:
        return not bool(node_surroundings[2])
    return False


def is_support_configuration_invalid(
    fixed_pins: list[dict[str, Any]],
    rollers: list[dict[str, Any]],
    walls: list[dict[str, Any]],
) -> bool:
    """Evaluate kinematic admissibility and static determinacy of support configuration.

    Rejects degenerate geometric configurations such as:
    - Collinear moment arms between pin and roller.
    - Fully parallel rollers unable to resist force in perpendicular axis.
    - Rollers sharing identical lines of action.
    """
    n_pins = len(fixed_pins)
    n_rollers = len(rollers)
    n_walls = len(walls)

    # Fixed wall configuration is always determinate for a single rigid body
    if n_walls == 1 and n_pins == 0 and n_rollers == 0:
        return False

    # 1 Pin + 1 Roller
    if n_pins == 1 and n_rollers == 1:
        pin_x, pin_y = fixed_pins[0]["r"][0], fixed_pins[0]["r"][1]
        roller_x, roller_y = rollers[0]["r"][0], rollers[0]["r"][1]
        roller_rot = rollers[0].get("rotation", 0)
        is_roller_horizontal = roller_rot in (90, 270)

        if not is_roller_horizontal:
            return bool(np.isclose(pin_x, roller_x, atol=1e-3))
        return bool(np.isclose(pin_y, roller_y, atol=1e-3))

    # 3 Rollers
    if n_rollers == 3 and n_pins == 0:
        is_horiz = [r.get("rotation", 0) in (90, 270) for r in rollers]
        # All rollers parallel (all horizontal or all vertical) -> kinematically unstable
        if all(is_horiz) or not any(is_horiz):
            return True

        # Check collinearity among parallel roller pairs
        for i in range(3):
            for j in range(i + 1, 3):
                r1, r2 = rollers[i], rollers[j]
                h1, h2 = is_horiz[i], is_horiz[j]
                if h1 == h2:
                    # Parallel vertical rollers sharing same X line of action
                    if not h1 and np.isclose(r1["r"][0], r2["r"][0], atol=1e-3):
                        return True
                    # Parallel horizontal rollers sharing same Y line of action
                    if h1 and np.isclose(r1["r"][1], r2["r"][1], atol=1e-3):
                        return True
        return False

    return True


def generate_supports(
    nodes: np.ndarray,
    node_surroundings: np.ndarray,
    support_case: int = 2,
    rng: np.random.Generator | None = None,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    np.ndarray,
    np.ndarray,
    bool,
]:
    """Generate supports and update remaining free unconstrained nodes.

    Args:
        nodes: (N, 2) array of rigid body joint coordinates.
        node_surroundings: (N, 4) boolean connectivity array.
        support_case: 1 for 3 Rollers, 2 for 1 Pin + 1 Roller (default), 3 for 1 Wall.
        rng: Explicit NumPy random number generator instance.

    Returns:
        tuple of (supports_dict, free_nodes, free_surroundings, is_invalid):
            - supports_dict: contains 'walls', 'fixed_pins', 'rollers'.
            - free_nodes: remaining unconstrained nodes available for load placement.
            - free_surroundings: surroundings for remaining free nodes.
            - is_invalid: True if no admissible determinate support configuration was found.
    """
    if rng is None:
        rng = np.random.default_rng()

    free_nodes_list = [nodes[i].copy() for i in range(len(nodes))]
    free_surroundings_list = [node_surroundings[i].copy() for i in range(len(node_surroundings))]

    walls: list[dict[str, Any]] = []
    fixed_pins: list[dict[str, Any]] = []
    rollers: list[dict[str, Any]] = []

    # Case 3: 1 Fixed Cantilever Wall
    if support_case == 3:
        # Find terminal dead-end nodes with exactly 1 connecting member
        extremum_indices = [
            i for i, s in enumerate(free_surroundings_list) if np.sum(s) == 1
        ]
        if not extremum_indices:
            return {"walls": [], "fixed_pins": [], "rollers": []}, nodes, node_surroundings, True

        chosen_idx = int(rng.choice(extremum_indices))
        wall_node = free_nodes_list[chosen_idx]
        surr = free_surroundings_list[chosen_idx]

        # Determine wall orientation perpendicular to outgoing member
        if surr[0]:
            rotation = 90
        elif surr[1]:
            rotation = 180
        elif surr[2]:
            rotation = 270
        else:
            rotation = 0

        walls.append({
            "r": wall_node.tolist(),
            "rotation": rotation,
            "label": "A",
        })
        free_nodes_list.pop(chosen_idx)
        free_surroundings_list.pop(chosen_idx)

    # Case 2: 1 Pin + 1 Roller
    elif support_case == 2:
        if len(free_nodes_list) < 2:
            return {"walls": [], "fixed_pins": [], "rollers": []}, nodes, node_surroundings, True

        # Randomly choose distinct nodes for pin and roller
        chosen_indices = rng.choice(len(free_nodes_list), size=2, replace=False)
        pin_node_idx = int(chosen_indices[0])
        roller_node_idx = int(chosen_indices[1])

        pin_coord = free_nodes_list[pin_node_idx]
        pin_surr = free_surroundings_list[pin_node_idx]
        roller_coord = free_nodes_list[roller_node_idx]
        roller_surr = free_surroundings_list[roller_node_idx]

        # Determine non-overlapping rotations
        rotations = [0, 90, 180, 270]
        rng.shuffle(rotations)
        pin_rot = 0
        for r in rotations:
            if good_pin_support_orientation(pin_surr, r):
                pin_rot = r
                break

        rng.shuffle(rotations)
        roller_rot = 0
        for r in rotations:
            if good_pin_support_orientation(roller_surr, r):
                roller_rot = r
                break

        fixed_pins.append({
            "r": pin_coord.tolist(),
            "rotation": pin_rot,
            "label": "A",
        })
        rollers.append({
            "r": roller_coord.tolist(),
            "rotation": roller_rot,
            "label": "B",
        })

        # Remove both nodes in descending index order to preserve list indices
        for idx in sorted([pin_node_idx, roller_node_idx], reverse=True):
            free_nodes_list.pop(idx)
            free_surroundings_list.pop(idx)

    # Case 1: 3 Rollers
    elif support_case == 1:
        if len(free_nodes_list) < 3:
            return {"walls": [], "fixed_pins": [], "rollers": []}, nodes, node_surroundings, True

        chosen_indices = rng.choice(len(free_nodes_list), size=3, replace=False)
        labels = ["A", "B", "C"]
        for k, node_idx in enumerate(chosen_indices):
            coord = free_nodes_list[int(node_idx)]
            surr = free_surroundings_list[int(node_idx)]
            rotations = [0, 90, 180, 270]
            rng.shuffle(rotations)
            roller_rot = 0
            for r in rotations:
                if good_pin_support_orientation(surr, r):
                    roller_rot = r
                    break
            rollers.append({
                "r": coord.tolist(),
                "rotation": roller_rot,
                "label": labels[k],
            })

        for idx in sorted(chosen_indices, reverse=True):
            free_nodes_list.pop(int(idx))
            free_surroundings_list.pop(int(idx))

    is_invalid = is_support_configuration_invalid(fixed_pins, rollers, walls)
    remaining_free_nodes = (
        np.array(free_nodes_list, dtype=int) if free_nodes_list else np.empty((0, 2), dtype=int)
    )
    remaining_free_surroundings = (
        np.array(free_surroundings_list, dtype=bool)
        if free_surroundings_list
        else np.empty((0, 4), dtype=bool)
    )

    return (
        {"walls": walls, "fixed_pins": fixed_pins, "rollers": rollers},
        remaining_free_nodes,
        remaining_free_surroundings,
        is_invalid,
    )

"""2D Rigid Body support placement, rotation orientation, and static determinacy checks.

This module ports the legacy MATLAB `+supptPkg` (`getSupportProfile.m`, `generateSupports.m`,
`genPinTypeSupports.m`, `genWall.m`, and `isSupportConfigurationInvalid.m`).

Structural Support Types & Boundary Conditions:
1. Case 1: Three Rollers (3 Reactions)
   - Three independent normal roller supports placed on distinct nodes.
   - Enforces non-parallel lines of action (cannot all be horizontal or vertical) and
     non-collinear lines of action so that equilibrium matrix rank is 3.
2. Case 2: One Pin + One Roller (3 Reactions - Default Standard)
   - Fixed pin support at joint A (provides reaction forces Ax and Ay).
   - Roller support at joint B (provides normal reaction force Bx if horizontal, or By if vertical).
   - Enforces a non-zero moment arm about the pin:
     - Vertical roller requires pin.x != roller.x (delta_x != 0).
     - Horizontal roller requires pin.y != roller.y (delta_y != 0).
3. Case 3: One Fixed Cantilever Wall (3 Reactions)
   - Fixed support placed on a terminal dead-end joint (degree 1).
   - Restrains horizontal displacement (Ax), vertical displacement (Ay), and rotation (MA).
"""

from typing import Any

import numpy as np


def good_pin_support_orientation(node_surroundings: np.ndarray, rotation_angle: int) -> bool:
    """Check if support drawing orientation does not collide with rigid body segments.

    Support Base Placement by Rotation Angle:
        - 0 degrees: Support base placed BELOW the node -> requires index 3 (down) to be False.
        - 90 degrees: Support base placed to the LEFT -> requires index 0 (right) to be False.
        - 180 degrees: Support base placed ABOVE the node -> requires index 1 (up) to be False.
        - 270 degrees: Support base placed to the RIGHT -> requires index 2 (left) to be False.

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

    Statics Principles Applied:
        1. Cantilever Wall: Statically determinate for any single rigid body (rank = 3).
        2. Pin + Roller: Line of action of the roller reaction MUST NOT pass directly
           through the pin support joint. If it passes through the pin, the moment of the
           roller reaction about the pin is identically zero, resulting in a singular
           equilibrium system (the body could freely rotate about the pin).
        3. Three Rollers:
           - Rollers cannot all be parallel (e.g. all vertical provides zero horizontal restraint).
           - Parallel roller pairs cannot lie on the same line of action (redundant reaction).

    Args:
        fixed_pins: List of fixed pin support dictionaries.
        rollers: List of roller support dictionaries.
        walls: List of fixed wall support dictionaries.

    Returns:
        True if the support configuration is kinematically unstable or singular.
    """
    n_pins = len(fixed_pins)
    n_rollers = len(rollers)
    n_walls = len(walls)

    # Fixed wall configuration is inherently determinate for a single rigid body
    if n_walls == 1 and n_pins == 0 and n_rollers == 0:
        return False

    # Case 2: 1 Pin + 1 Roller
    if n_pins == 1 and n_rollers == 1:
        pin_x, pin_y = fixed_pins[0]["r"][0], fixed_pins[0]["r"][1]
        roller_x, roller_y = rollers[0]["r"][0], rollers[0]["r"][1]
        roller_rot = rollers[0].get("rotation", 0)
        is_roller_horizontal = roller_rot in (90, 270)

        # If roller is vertical (resists in Y), pin_x must != roller_x for moment resistance
        if not is_roller_horizontal:
            return bool(np.isclose(pin_x, roller_x, atol=1e-3))
        # If roller is horizontal (resists in X), pin_y must != roller_y for moment resistance
        return bool(np.isclose(pin_y, roller_y, atol=1e-3))

    # Case 1: 3 Rollers
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
    """Generate boundary supports and compute remaining unconstrained joints for loading.

    Support Case Definitions:
        - Case 1: Three Rollers (3 Rollers on distinct non-parallel nodes)
        - Case 2: One Pin + One Roller (Standard 3-reaction support - Default)
        - Case 3: One Fixed Cantilever Wall (Wall attached to a degree-1 terminal node)

    Args:
        nodes: (N, 2) array of rigid body joint coordinates.
        node_surroundings: (N, 4) boolean connectivity array.
        support_case: Integer (1, 2, or 3).
        rng: Explicit NumPy random number generator instance.

    Returns:
        tuple of (supports_dict, free_nodes, free_surroundings, is_invalid):
            - supports_dict: dictionary containing 'walls', 'fixed_pins', and 'rollers'.
            - free_nodes: (K, 2) array of remaining joints available for external loads.
            - free_surroundings: (K, 4) boolean surroundings for remaining free nodes.
            - is_invalid: True if configuration is kinematically singular.
    """
    if rng is None:
        rng = np.random.default_rng()

    free_nodes_list = [nodes[i].copy() for i in range(len(nodes))]
    free_surroundings_list = [node_surroundings[i].copy() for i in range(len(node_surroundings))]

    walls: list[dict[str, Any]] = []
    fixed_pins: list[dict[str, Any]] = []
    rollers: list[dict[str, Any]] = []

    # Case 3: 1 Fixed Cantilever Wall Support
    if support_case == 3:
        # Find terminal dead-end nodes with exactly 1 connecting member (extremum joints)
        extremum_indices = [i for i, s in enumerate(free_surroundings_list) if np.sum(s) == 1]
        if not extremum_indices:
            return {"walls": [], "fixed_pins": [], "rollers": []}, nodes, node_surroundings, True

        chosen_idx = int(rng.choice(extremum_indices))
        wall_node = free_nodes_list[chosen_idx]
        surr = free_surroundings_list[chosen_idx]

        # Orient the wall base perpendicular to the connected structural member
        if surr[0]:  # Member goes +x -> wall on the left (rot 90)
            rotation = 90
        elif surr[1]:  # Member goes +y -> wall below (rot 180)
            rotation = 180
        elif surr[2]:  # Member goes -x -> wall on the right (rot 270)
            rotation = 270
        else:  # Member goes -y -> wall above (rot 0)
            rotation = 0

        walls.append(
            {
                "r": wall_node.tolist(),
                "rotation": rotation,
                "label": "A",
            }
        )
        free_nodes_list.pop(chosen_idx)
        free_surroundings_list.pop(chosen_idx)

    # Case 2: 1 Fixed Pin + 1 Roller Support (Standard Statics Case)
    elif support_case == 2:
        if len(free_nodes_list) < 2:
            return {"walls": [], "fixed_pins": [], "rollers": []}, nodes, node_surroundings, True

        # Randomly choose distinct joints for pin and roller placement
        chosen_indices = rng.choice(len(free_nodes_list), size=2, replace=False)
        pin_node_idx = int(chosen_indices[0])
        roller_node_idx = int(chosen_indices[1])

        pin_coord = free_nodes_list[pin_node_idx]
        pin_surr = free_surroundings_list[pin_node_idx]
        roller_coord = free_nodes_list[roller_node_idx]
        roller_surr = free_surroundings_list[roller_node_idx]

        # Determine collision-free drawing rotations
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

        fixed_pins.append(
            {
                "r": pin_coord.tolist(),
                "rotation": pin_rot,
                "label": "A",
            }
        )
        rollers.append(
            {
                "r": roller_coord.tolist(),
                "rotation": roller_rot,
                "label": "B",
            }
        )

        # Remove both nodes in descending order to avoid index shifting
        for idx in sorted([pin_node_idx, roller_node_idx], reverse=True):
            free_nodes_list.pop(idx)
            free_surroundings_list.pop(idx)

    # Case 1: 3 Roller Supports
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
            rollers.append(
                {
                    "r": coord.tolist(),
                    "rotation": roller_rot,
                    "label": labels[k],
                }
            )

        for idx in sorted(chosen_indices, reverse=True):
            free_nodes_list.pop(int(idx))
            free_surroundings_list.pop(int(idx))

    # Evaluate determinacy and assemble unconstrained node arrays
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

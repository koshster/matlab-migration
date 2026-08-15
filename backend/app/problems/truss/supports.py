from typing import Any
import numpy as np


def get_outward_rotation(node_pos: np.ndarray, centroid: np.ndarray) -> int:
    """Determine support rotation pointing outward away from the structure centroid.

    0 = downward (roller on bottom)
    90 = rightward (roller on right wall)
    180 = upward (roller on top)
    270 = leftward (roller on left wall)
    """
    dx = float(node_pos[0] - centroid[0])
    dy = float(node_pos[1] - centroid[1])

    # Choose primary outward direction
    if abs(dy) >= abs(dx):
        return 0 if dy <= 0 else 180
    else:
        return 90 if dx >= 0 else 270


def generate_supports(
    node_coords: np.ndarray, rng: np.random.Generator, max_attempts: int = 50
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Randomly generate fixed pin and roller supports for boundary nodes (matching MATLAB genPinTypeSupports).

    Ensures:
    1. Supports are placed on distinct exterior/boundary joints.
    2. Support orientations point outwards away from the structure.
    3. The configuration is statically determinate (non-singular).
    """
    n_nodes = len(node_coords)
    centroid = np.mean(node_coords, axis=0)

    for _ in range(max_attempts):
        # Randomly choose 2 distinct nodes for pin and roller
        chosen_indices = rng.choice(n_nodes, size=2, replace=False)
        pin_idx = int(chosen_indices[0])
        roller_idx = int(chosen_indices[1])

        p1 = node_coords[pin_idx]
        p2 = node_coords[roller_idx]

        # Determine outward rotation
        roller_rot = get_outward_rotation(p2, centroid)

        # Validate static determinacy (genEliminate check):
        # If roller is vertical (0 or 180), pin.x and roller.x must not be collinear
        # If roller is horizontal (90 or 270), pin.y and roller.y must not be collinear
        if roller_rot in (0, 180) and not np.isclose(p1[0], p2[0], atol=1e-3):
            pin_supports = [{"r": p1.tolist(), "node_index": pin_idx}]
            roller_supports = [
                {"r": p2.tolist(), "node_index": roller_idx, "rotation": roller_rot}
            ]
            return pin_supports, roller_supports
        elif roller_rot in (90, 270) and not np.isclose(p1[1], p2[1], atol=1e-3):
            pin_supports = [{"r": p1.tolist(), "node_index": pin_idx}]
            roller_supports = [
                {"r": p2.tolist(), "node_index": roller_idx, "rotation": roller_rot}
            ]
            return pin_supports, roller_supports

    # Fallback to bottom-most horizontally separated nodes
    lowest_y = float(np.min(node_coords[:, 1]))
    bottom_nodes = [
        i for i in range(n_nodes) if np.isclose(node_coords[i, 1], lowest_y, atol=1e-3)
    ]
    if len(bottom_nodes) >= 2:
        sorted_bottom = sorted(bottom_nodes, key=lambda idx: float(node_coords[idx, 0]))
        sup_1, sup_2 = sorted_bottom[0], sorted_bottom[-1]
    else:
        sup_1 = bottom_nodes[0]
        other_nodes = [
            i
            for i in range(n_nodes)
            if i != sup_1 and not np.isclose(node_coords[i, 0], node_coords[sup_1, 0], atol=1e-3)
        ]
        sup_2 = other_nodes[0] if other_nodes else (sup_1 + 1) % n_nodes

    p1 = node_coords[sup_1]
    p2 = node_coords[sup_2]
    roller_rot = 0 if not np.isclose(p1[0], p2[0], atol=1e-3) else 90

    return (
        [{"r": p1.tolist(), "node_index": int(sup_1)}],
        [{"r": p2.tolist(), "node_index": int(sup_2), "rotation": roller_rot}],
    )



from typing import Any
import numpy as np


def generate_supports(
    node_coords: np.ndarray, rng: np.random.Generator
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate fixed pin and roller supports for 2D truss boundary nodes.

    Returns:
        (pin_supports, roller_supports)
    """
    n_nodes = len(node_coords)
    # Pick lowest y coordinates for supports
    sorted_indices = np.argsort(node_coords[:, 1])
    sup_node_1 = sorted_indices[0]
    sup_node_2 = sorted_indices[1] if n_nodes > 3 else sorted_indices[-1]

    pin_supports = [{"r": node_coords[sup_node_1].tolist(), "node_index": int(sup_node_1)}]
    roller_supports = [
        {"r": node_coords[sup_node_2].tolist(), "node_index": int(sup_node_2), "rotation": 0}
    ]

    return pin_supports, roller_supports

from typing import Any
import numpy as np


def generate_loads(
    node_coords: np.ndarray,
    pin_supports: list[dict[str, Any]],
    roller_supports: list[dict[str, Any]],
    rng: np.random.Generator,
    max_magnitude: float = 5.0,
) -> list[dict[str, Any]]:
    """Generate external point loads applied to non-support nodes.

    Returns:
        List of load dicts containing force vector F [fx, fy] and position P [px, py].
    """
    n_nodes = len(node_coords)
    support_node_indices = {p["node_index"] for p in pin_supports} | {
        r["node_index"] for r in roller_supports
    }
    available_nodes = [i for i in range(n_nodes) if i not in support_node_indices]

    if not available_nodes:
        available_nodes = list(range(n_nodes))

    load_node_idx = rng.choice(available_nodes)
    pos = node_coords[load_node_idx].tolist()

    # Generate random force magnitude & direction
    mag = rng.uniform(1.0, max_magnitude)
    fy = -round(float(mag), 1)  # Downward vertical load
    fx = 0.0

    return [{"F": [fx, fy], "P": pos, "node_index": int(load_node_idx)}]

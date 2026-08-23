from typing import Any

import numpy as np


def generate_loads(
    node_coords: np.ndarray,
    pin_supports: list[dict[str, Any]],
    roller_supports: list[dict[str, Any]],
    rng: np.random.Generator,
    max_magnitude: float = 5.0,
    load_count: int = 1,
) -> list[dict[str, Any]]:
    """Generate external point loads applied to distinct non-support nodes.

    `load_count` follows the legacy `getLoadProfile.m`, which applied 1-2 loads
    (BUILD_SPEC §2); it is clamped to the number of loadable nodes so a small
    truss cannot be asked for more loads than it has free joints.

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

    count = max(1, min(int(load_count), len(available_nodes)))
    # Distinct nodes: two loads stacked on one joint would read as a single
    # larger load in the diagram.
    chosen = rng.choice(available_nodes, size=count, replace=False)

    loads: list[dict[str, Any]] = []
    for load_node_idx in np.atleast_1d(chosen):
        pos = node_coords[int(load_node_idx)].tolist()

        # Whole integer magnitude, 1..max_magnitude (matching MATLAB randi)
        mag = float(rng.integers(1, int(max_magnitude) + 1))

        # 50% vertical (up or down), 50% horizontal (left or right)
        if rng.random() <= 0.5:
            fy = -mag if rng.random() < 0.8 else mag  # Prefer downward loads
            fx = 0.0
        else:
            fx = -mag if rng.random() < 0.5 else mag
            fy = 0.0

        loads.append({"F": [fx, fy], "P": pos, "node_index": int(load_node_idx)})

    return loads

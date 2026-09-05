from typing import Any

import numpy as np

# Load directions in degrees, measured from +x. Downward and the two downward
# diagonals carry most of the weight because gravity loads are what students
# expect to see; the rest keep the problem set from becoming formulaic.
_DIRECTIONS = np.array([0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0])
_DIRECTION_WEIGHTS = np.array([0.06, 0.06, 0.04, 0.06, 0.06, 0.24, 0.24, 0.24])


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

        # Direction on a 45-degree rose, biased downward.
        #
        # Purely axis-aligned loads were the main reason so many answers came
        # out zero: node coordinates snap to an integer grid, so members are
        # frequently axis-aligned too, and a vertical load on a joint with a
        # vertical member runs straight into the support and leaves every other
        # member at zero force. Allowing diagonals gives the load somewhere to
        # resolve. Magnitudes stay integral, so answers stay clean to 2dp.
        angle_deg = float(rng.choice(_DIRECTIONS, p=_DIRECTION_WEIGHTS))
        radians = np.deg2rad(angle_deg)
        # Not rounded: a 45-degree component is irrational, and rounding it to
        # a few decimals perturbs the resulting magnitude by more than float
        # error would. The diagram formats the label itself.
        fx = float(mag * np.cos(radians))
        fy = float(mag * np.sin(radians))

        loads.append({"F": [fx, fy], "P": pos, "node_index": int(load_node_idx)})

    return loads

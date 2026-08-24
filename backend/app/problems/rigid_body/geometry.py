"""2D Rigid Body geometry synthesis and grid connectivity processing.

Generates a continuous 2D planar rigid body path along an integer Cartesian grid,
computes 4-directional Manhattan node surroundings (+x, +y, -x, -y), and collapses
overlapping nodes while preserving topological connectivity flags.
"""

import numpy as np


def generate_body_path(steps: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a 2D integer random-walk path starting from the origin (0, 0).

    Args:
        steps: Number of Manhattan steps to take (typically 4 to 10).
        rng: Explicit NumPy random number generator instance.

    Returns:
        (steps + 1) x 2 integer coordinate array representing the continuous body path.
    """
    path = np.zeros((steps + 1, 2), dtype=int)
    # Direction mappings: 0: +x (right), 1: +y (up), 2: -x (left), 3: -y (down)
    deltas = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=int)

    for i in range(steps):
        direction_idx = int(rng.integers(0, 4))
        path[i + 1] = path[i] + deltas[direction_idx]

    return path


def collapse_nodes(path_nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Calculate 4-way Manhattan neighborhood surroundings and collapse duplicate nodes.

    Surroundings convention:
        - Index 0: neighbor to the right (+x)
        - Index 1: neighbor above (+y)
        - Index 2: neighbor to the left (-x)
        - Index 3: neighbor below (-y)

    Args:
        path_nodes: Array of shape (N, 2) defining the ordered points along the path.

    Returns:
        tuple of (unique_nodes, node_surroundings):
            - unique_nodes: (M, 2) array of distinct node coordinates.
            - node_surroundings: (M, 4) boolean array of connectivity directions for each node.
    """
    n_pts = len(path_nodes)
    if n_pts == 0:
        return np.empty((0, 2), dtype=int), np.empty((0, 4), dtype=bool)

    # Temporary surroundings for each step in path_nodes
    surroundings_list = np.zeros((n_pts, 4), dtype=bool)

    for i in range(n_pts):
        neighbors = []
        if i > 0:
            neighbors.append(path_nodes[i - 1])
        if i < n_pts - 1:
            neighbors.append(path_nodes[i + 1])

        for neighbor in neighbors:
            diff = path_nodes[i] - neighbor
            # If path_nodes[i] - neighbor == [-1, 0], neighbor is at +x from node i
            if diff[0] < 0 and diff[1] == 0:
                surroundings_list[i, 0] = True  # +x
            elif diff[0] == 0 and diff[1] < 0:
                surroundings_list[i, 1] = True  # +y
            elif diff[0] > 0 and diff[1] == 0:
                surroundings_list[i, 2] = True  # -x
            elif diff[0] == 0 and diff[1] > 0:
                surroundings_list[i, 3] = True  # -y

    # Deduplicate nodes and merge surroundings using logical OR
    unique_coords: list[np.ndarray] = []
    merged_surroundings: list[np.ndarray] = []

    for i in range(n_pts):
        coord = path_nodes[i]
        matched_idx = -1
        for idx, existing in enumerate(unique_coords):
            if np.array_equal(existing, coord):
                matched_idx = idx
                break

        if matched_idx == -1:
            unique_coords.append(coord.copy())
            merged_surroundings.append(surroundings_list[i].copy())
        else:
            merged_surroundings[matched_idx] |= surroundings_list[i]

    return np.array(unique_coords, dtype=int), np.array(merged_surroundings, dtype=bool)


def generate_rigid_body_geometry(
    min_nodes: int = 5,
    rng: np.random.Generator | None = None,
    max_attempts: int = 100,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Synthesize a valid 2D rigid body geometry with at least `min_nodes` distinct grid joints.

    Args:
        min_nodes: Minimum number of unique collapsed nodes (default 5 matching MATLAB).
        rng: Explicit NumPy random number generator instance.
        max_attempts: Maximum generation attempts before fallback.

    Returns:
        tuple of (path_nodes, unique_nodes, node_surroundings):
            - path_nodes: (steps + 1, 2) array of the continuous path on the positive grid.
            - unique_nodes: (M, 2) array of distinct nodes on the positive grid.
            - node_surroundings: (M, 4) boolean array of Manhattan surroundings.
    """
    if rng is None:
        rng = np.random.default_rng()

    for _ in range(max_attempts):
        # Steps between 4 and 10 matching MATLAB randi([4, 10])
        steps = int(rng.integers(4, 11))
        path = generate_body_path(steps, rng)
        unique_nodes, surroundings = collapse_nodes(path)

        if len(unique_nodes) >= min_nodes:
            # Shift geometry so minimum coordinate is aligned to (0, 0)
            min_offset = np.min(unique_nodes, axis=0)
            shifted_path = path - min_offset
            shifted_nodes = unique_nodes - min_offset
            return shifted_path, shifted_nodes, surroundings

    # Fallback deterministic L-bracket with 5 nodes if max_attempts exceeded
    fallback_path = np.array([[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]], dtype=int)
    fallback_nodes, fallback_surroundings = collapse_nodes(fallback_path)
    return fallback_path, fallback_nodes, fallback_surroundings

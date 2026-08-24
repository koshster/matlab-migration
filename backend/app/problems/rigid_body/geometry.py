"""2D Rigid Body geometry synthesis and grid connectivity processing.

This module ports the legacy MATLAB `+bodyPkg` (`genBody.m` and `collapseNodes.m`).
It generates a continuous 2D planar rigid body made of connected integer segments
along the Cartesian grid (representing structural members like beams, brackets, and frames).

Key Mechanical & Algorithmic Concepts:
1. Manhattan Random Walk:
   - Starts at the origin (0, 0).
   - Generates a sequence of connected orthogonal steps (right, up, left, down).
2. Neighborhood Surroundings (Topology):
   - For every joint/node along the body, records which orthogonal directions have
     attached structural members (+x, +y, -x, -y).
   - This topological map is essential for collision detection, preventing boundary
     supports, force arrows, and moment arcs from drawing over physical body segments.
3. Node Collapse & Deduplication:
   - If the path crosses or touches the same grid coordinate multiple times, duplicate
     coordinates are merged, and their connectivity flags are combined using boolean OR.
"""

import numpy as np


def generate_body_path(steps: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a 2D integer random-walk path starting from the origin (0, 0).

    Takes `steps` orthogonal unit steps on an integer grid. At each step, moves
    one unit in one of the 4 Cartesian directions:
        0 -> +x (right: [ 1,  0])
        1 -> +y (up:    [ 0,  1])
        2 -> -x (left:  [-1,  0])
        3 -> -y (down:  [ 0, -1])

    Args:
        steps: Number of Manhattan steps to take (typically 4 to 10).
        rng: Explicit NumPy random number generator instance for seed reproducibility.

    Returns:
        (steps + 1) x 2 integer coordinate array representing the continuous body path.
    """
    path = np.zeros((steps + 1, 2), dtype=int)
    # Orthogonal unit step vectors on the Cartesian plane
    deltas = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=int)

    for i in range(steps):
        # Pick one of the 4 cardinal directions randomly
        direction_idx = int(rng.integers(0, 4))
        path[i + 1] = path[i] + deltas[direction_idx]

    return path


def collapse_nodes(path_nodes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Calculate 4-way Manhattan neighborhood surroundings and collapse duplicate nodes.

    Surroundings 4-boolean array convention:
        - Index 0: True if a connected member extends to the right (+x)
        - Index 1: True if a connected member extends upwards (+y)
        - Index 2: True if a connected member extends to the left (-x)
        - Index 3: True if a connected member extends downwards (-y)

    Algorithm:
        1. Examine each sequential point in the path and inspect its incoming/outgoing
           neighbors along the continuous curve to establish direction flags.
        2. Deduplicate repeated node coordinates (e.g. loops or self-intersections)
           and merge their direction flags with bitwise/logical OR.

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

    # Temporary surroundings array for each step in path_nodes
    surroundings_list = np.zeros((n_pts, 4), dtype=bool)

    for i in range(n_pts):
        # Identify preceding and succeeding neighbors along the physical path
        neighbors = []
        if i > 0:
            neighbors.append(path_nodes[i - 1])
        if i < n_pts - 1:
            neighbors.append(path_nodes[i + 1])

        for neighbor in neighbors:
            diff = path_nodes[i] - neighbor
            # If path_nodes[i] - neighbor == [-1, 0], neighbor is to the right (+x)
            if diff[0] < 0 and diff[1] == 0:
                surroundings_list[i, 0] = True  # +x neighbor
            # If path_nodes[i] - neighbor == [0, -1], neighbor is above (+y)
            elif diff[0] == 0 and diff[1] < 0:
                surroundings_list[i, 1] = True  # +y neighbor
            # If path_nodes[i] - neighbor == [1, 0], neighbor is to the left (-x)
            elif diff[0] > 0 and diff[1] == 0:
                surroundings_list[i, 2] = True  # -x neighbor
            # If path_nodes[i] - neighbor == [0, 1], neighbor is below (-y)
            elif diff[0] == 0 and diff[1] > 0:
                surroundings_list[i, 3] = True  # -y neighbor

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
            # Merge connectivity flags so all attached branches are recorded
            merged_surroundings[matched_idx] |= surroundings_list[i]

    return np.array(unique_coords, dtype=int), np.array(merged_surroundings, dtype=bool)


def generate_rigid_body_geometry(
    min_nodes: int = 5,
    rng: np.random.Generator | None = None,
    max_attempts: int = 100,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Synthesize a valid 2D rigid body geometry with at least `min_nodes` distinct grid joints.

    Ensures the synthesized body is large enough to attach 2-3 supports and 1-3 applied
    loads/moments on distinct joint locations without crowding.

    Coordinates are automatically normalized so that minimum x = 0 and minimum y = 0.

    Args:
        min_nodes: Minimum number of unique collapsed nodes (default 5, matching MATLAB).
        rng: Explicit NumPy random number generator instance.
        max_attempts: Maximum random generation attempts before using a guaranteed fallback.

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

        # Ensure the body has sufficient distinct nodes for supports and loads
        if len(unique_nodes) >= min_nodes:
            # Shift geometry so minimum coordinate is cleanly aligned to the origin (0, 0)
            min_offset = np.min(unique_nodes, axis=0)
            shifted_path = path - min_offset
            shifted_nodes = unique_nodes - min_offset
            return shifted_path, shifted_nodes, surroundings

    # Fallback deterministic L-bracket with 5 nodes if random attempts exceeded
    fallback_path = np.array([[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]], dtype=int)
    fallback_nodes, fallback_surroundings = collapse_nodes(fallback_path)
    return fallback_path, fallback_nodes, fallback_surroundings

import numpy as np
from scipy.spatial import Delaunay


def angle_between(u: np.ndarray, v: np.ndarray) -> float:
    """Calculate angle in degrees between two 2D vectors."""
    norm_u = np.linalg.norm(u)
    norm_v = np.linalg.norm(v)
    if norm_u == 0 or norm_v == 0:
        return 0.0
    cos_theta = np.dot(u, v) / (norm_u * norm_v)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_theta)))


def check_min_angle(nodes: np.ndarray, simplices: np.ndarray, min_angle: float = 30.0) -> bool:
    """Verify that all triangle internal angles are >= min_angle."""
    for tri in simplices:
        p1, p2, p3 = nodes[tri[0]], nodes[tri[1]], nodes[tri[2]]
        v1 = p2 - p1
        v2 = p3 - p1
        v3 = p3 - p2

        a1 = angle_between(v1, v2)
        a2 = angle_between(-v1, v3)
        a3 = angle_between(-v2, -v3)

        if min(a1, a2, a3) < min_angle:
            return False
    return True


def extract_unique_edges(simplices: np.ndarray) -> np.ndarray:
    """Extract sorted unique member edges from Delaunay simplices."""
    edges = []
    for tri in simplices:
        edges.append(sorted([tri[0], tri[1]]))
        edges.append(sorted([tri[0], tri[2]]))
        edges.append(sorted([tri[1], tri[2]]))
    unique_edges = np.unique(np.array(edges), axis=0)
    return unique_edges


def _generate_determinate_strip(
    n_nodes: int, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministically generate a 2D planar simple truss with exact node count and m = 2n - 3."""
    n_bottom = (n_nodes + 1) // 2
    n_top = n_nodes // 2

    # Integer height (1 or 2 grid units)
    h = int(rng.choice([1, 2]))
    bottom_x = np.arange(n_bottom) * 2
    bottom_y = np.zeros(n_bottom)

    top_x = np.arange(n_top) * 2 + 1
    top_y = np.full(n_top, h)

    # Optional pitch for symmetric peak when n_nodes >= 5
    if rng.random() > 0.5 and n_top >= 2:
        mid = (n_top - 1) / 2.0
        for i in range(n_top):
            top_y[i] += int(round(1.0 - abs(i - mid) / (mid + 0.5)))

    nodes = np.vstack(
        [
            np.column_stack([bottom_x, bottom_y]),
            np.column_stack([top_x, top_y]),
        ]
    ).astype(float)

    # Random reflections
    if rng.random() > 0.5:
        nodes[:, 0] = -nodes[:, 0]
    if rng.random() > 0.5:
        nodes[:, 1] = -nodes[:, 1]

    # Random 90-degree rotations
    rot_k = int(rng.integers(0, 4))
    if rot_k > 0:
        angle = np.pi / 2 * rot_k
        cos_a, sin_a = int(round(np.cos(angle))), int(round(np.sin(angle)))
        rot_mat = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
        nodes = nodes @ rot_mat.T

    # Shift so minimum coordinate is at (0, 0)
    nodes -= np.min(nodes, axis=0)
    nodes = np.round(nodes).astype(float)

    tri = Delaunay(nodes)
    members = extract_unique_edges(tri.simplices)
    return nodes, members, tri.simplices


def generate_truss_geometry(
    n_nodes: int, rng: np.random.Generator, min_angle: float = 35.0, max_attempts: int = 150
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate 2D planar truss node coordinates and member topology using Delaunay triangulation.

    Guarantees:
        - len(node_coords) == n_nodes
        - len(members) == 2 * n_nodes - 3
        - All node coordinates are whole integer grid points.

    Returns:
        (node_coords, members, simplices)
    """
    if n_nodes < 3:
        raise ValueError("Number of nodes must be at least 3.")

    starting_configs = [
        np.array([[0, 0], [2, 0], [1, 1]]),
        np.array([[0, 0], [1, 0], [0, 1]]),
        np.array([[0, 0], [0, 1], [-1, 0]]),
        np.array([[0, 0], [1, 0], [1, 1]]),
        np.array([[0, 0], [-1, 0], [-1, -1]]),
    ]

    for _attempt in range(max_attempts):
        cfg_idx = rng.integers(0, len(starting_configs))
        nodes = starting_configs[cfg_idx].copy().astype(float)

        growth_attempts = 0
        while len(nodes) < n_nodes and growth_attempts < 60:
            growth_attempts += 1
            base_idx = rng.integers(0, len(nodes))
            base_node = nodes[base_idx]
            offset = rng.choice([-2, -1, 0, 1, 2], size=2)
            if np.all(offset == 0):
                offset = np.array([1, 0])
            candidate = base_node + offset
            candidate = np.round(candidate).astype(float)

            if np.any(np.all(np.isclose(nodes, candidate), axis=1)):
                continue

            test_nodes = np.vstack([nodes, candidate])
            if len(test_nodes) >= 3:
                try:
                    tri = Delaunay(test_nodes)
                    if check_min_angle(test_nodes, tri.simplices, min_angle):
                        nodes = test_nodes
                except Exception:
                    continue

        if len(nodes) == n_nodes:
            try:
                tri = Delaunay(nodes)
                members = extract_unique_edges(tri.simplices)
                if len(members) == (2 * n_nodes - 3):
                    # Ensure coordinates are aligned to positive integer grid
                    nodes -= np.min(nodes, axis=0)
                    return np.round(nodes).astype(float), members, tri.simplices
            except Exception:
                continue

    # Guaranteed valid determinate planar truss fallback
    return _generate_determinate_strip(n_nodes, rng)

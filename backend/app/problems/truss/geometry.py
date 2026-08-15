from typing import Any
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


def check_min_angle(nodes: np.ndarray, simplices: np.ndarray, min_angle: float = 45.0) -> bool:
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


def generate_truss_geometry(
    n_nodes: int, rng: np.random.Generator, min_angle: float = 45.0, max_attempts: int = 100
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate 2D planar truss node coordinates and member topology using Delaunay triangulation.

    Returns:
        (node_coords, members, simplices)
    """
    if n_nodes < 3:
        raise ValueError("Number of nodes must be at least 3.")

    starting_configs = [
        np.array([[0, 0], [1, 0], [0, 1]]),
        np.array([[0, 0], [0, 1], [-1, 0]]),
        np.array([[0, 0], [1, 0], [1, 1]]),
        np.array([[0, 0], [-1, 0], [-1, -1]]),
    ]

    for attempt in range(max_attempts):
        cfg_idx = rng.integers(0, len(starting_configs))
        nodes = starting_configs[cfg_idx].copy().astype(float)

        # Grow node set up to n_nodes
        growth_attempts = 0
        while len(nodes) < n_nodes and growth_attempts < 50:
            growth_attempts += 1
            # Pick existing node and offset
            base_idx = rng.integers(0, len(nodes))
            base_node = nodes[base_idx]
            offset = rng.choice([-1, 0, 1], size=2)
            if np.all(offset == 0):
                offset = np.array([1, 0])
            candidate = base_node + offset
            candidate = np.round(candidate).astype(float)


            # Check if duplicate node
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
                # Check simple truss condition m = 2n - 3
                if len(members) == (2 * n_nodes - 3):
                    return nodes, members, tri.simplices
            except Exception:
                continue

    # Fallback default geometry for seed reliability
    grid_x, grid_y = np.meshgrid(np.arange(n_nodes // 2 + 1), np.arange(2))
    nodes = np.column_stack([grid_x.ravel(), grid_y.ravel()])[:n_nodes].astype(float)
    tri = Delaunay(nodes)
    members = extract_unique_edges(tri.simplices)
    return nodes, members, tri.simplices

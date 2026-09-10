"""Locks the wire shape of truss geometry to packages/contract.

The backend previously emitted `node1`/`node2`/`nodeId` while the contract and
the MSW fixtures used `from`/`to`/`node`, so the mock API and the real API
disagreed and the renderer could not be type-checked. These tests fail if that
drift returns.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.problem_display import (
    build_answer_schema_truss,
    build_truss_geometry,
    member_field_key,
)
from app.problems.truss.generator import truss_generator


def _find_fixture_dir() -> Path:
    """Resolve packages/contract/fixtures from a repo checkout or the container.

    Locally the tree is statics-platform/{backend,packages}; in the backend
    container, backend/ is mounted at /app and packages/ at /packages.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packages" / "contract" / "fixtures"
        if candidate.is_dir():
            return candidate
    raise AssertionError("could not locate packages/contract/fixtures")


FIXTURE_DIR = _find_fixture_dir()

MEMBER_KEYS = {"id", "from", "to", "label"}
SUPPORT_KEYS = {"node", "type", "angleDeg"}
FORCE_KEYS = {"node", "fx", "fy", "label"}
NODE_KEYS = {"id", "x", "y"}


def _geometry(seed: int, num_nodes: int) -> dict[str, Any]:
    display = truss_generator.generate(seed=seed, params={"num_nodes": num_nodes})
    return build_truss_geometry(display.visual_schema)


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_geometry_uses_contract_field_names(num_nodes: int) -> None:
    g = _geometry(seed=42, num_nodes=num_nodes)

    assert g["schemaVersion"] == 1
    assert set(g) == {"schemaVersion", "nodes", "members", "supports", "forces", "bounds"}

    for node in g["nodes"]:
        assert set(node) == NODE_KEYS
    for member in g["members"]:
        assert set(member) == MEMBER_KEYS
    for support in g["supports"]:
        assert set(support) == SUPPORT_KEYS
        assert support["type"] in ("pin", "roller")
    for force in g["forces"]:
        assert set(force) == FORCE_KEYS


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_node_ids_are_one_based_and_all_references_resolve(num_nodes: int) -> None:
    g = _geometry(seed=7, num_nodes=num_nodes)
    node_ids = [n["id"] for n in g["nodes"]]

    # 1-based and contiguous, matching the contract fixtures.
    assert node_ids == list(range(1, len(node_ids) + 1))

    valid = set(node_ids)
    for member in g["members"]:
        assert member["from"] in valid
        assert member["to"] in valid
        assert member["from"] != member["to"]
    for support in g["supports"]:
        assert support["node"] in valid
    for force in g["forces"]:
        assert force["node"] in valid


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_member_ids_are_one_based_and_labels_are_subscripted(num_nodes: int) -> None:
    g = _geometry(seed=13, num_nodes=num_nodes)
    members = g["members"]

    assert [m["id"] for m in members] == list(range(1, len(members) + 1))
    assert members[0]["label"] == "S₁"
    if len(members) >= 3:
        assert members[2]["label"] == "S₃"


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_answer_field_keys_stay_plain_ascii(num_nodes: int) -> None:
    """Field keys are persisted in draft_answers and submissions, so they must
    stay `S1`-style ASCII even though the displayed label is subscripted."""
    g = _geometry(seed=99, num_nodes=num_nodes)
    schema = build_answer_schema_truss(g["members"])

    assert len(schema["groups"]) == 1
    group = schema["groups"][0]
    # AnswerGroup.id is required by the contract and used as the React key.
    assert group["id"] == "member-forces"

    keys = [f["key"] for f in group["fields"]]
    assert keys == [f"S{i}" for i in range(1, len(g["members"]) + 1)]
    assert keys == [member_field_key(m["id"]) for m in g["members"]]


def test_roller_angle_is_carried_through() -> None:
    """Roller orientation is computed in supports.py but used to be dropped
    here, so every roller rendered base-down regardless of its real rotation."""
    seen: set[int] = set()
    for seed in range(60):
        g = _geometry(seed=seed, num_nodes=5)
        for support in g["supports"]:
            if support["type"] == "roller":
                seen.add(support["angleDeg"])

    assert seen, "no rollers generated"
    assert seen <= {0, 90, 180, 270}
    assert len(seen) > 1, f"roller angle looks hardcoded, only ever saw {seen}"


@pytest.mark.parametrize(
    "fixture_name", ["truss-3node.json", "truss-4node.json", "truss-6node.json"]
)
def test_live_geometry_shape_matches_msw_fixtures(fixture_name: str) -> None:
    """MSW serves these fixtures in dev; if their shape diverges from what the
    backend emits, the app behaves differently against mocks than production."""
    fixture = json.loads((FIXTURE_DIR / fixture_name).read_text(encoding="utf-8"))
    fixture_geometry = fixture["geometry"]

    g = _geometry(seed=5, num_nodes=4)

    assert set(g) == set(fixture_geometry)
    assert set(g["nodes"][0]) == set(fixture_geometry["nodes"][0])
    assert set(g["members"][0]) == set(fixture_geometry["members"][0])
    assert set(g["supports"][0]) == set(fixture_geometry["supports"][0])
    assert set(g["bounds"]) == set(fixture_geometry["bounds"])
    if fixture_geometry["forces"] and g["forces"]:
        assert set(g["forces"][0]) == set(fixture_geometry["forces"][0])

    fixture_group = fixture["answerSchema"]["groups"][0]
    live_group = build_answer_schema_truss(g["members"])["groups"][0]
    assert set(live_group) == set(fixture_group)
    assert set(live_group["fields"][0]) == set(fixture_group["fields"][0])

"""The generator declares its own configurable knobs.

The assignment builder renders its difficulty form from `params_schema`, so no
admin component needs to know what a truss is (CLAUDE.md registry invariant).
These tests guard the two things that would break that: a knob the UI can offer
but the generator ignores, and a knob that produces an unsolvable problem.
"""

from collections.abc import Mapping
from typing import Any

import pytest

from app.api.v1.assignments import _check_answers
from app.services.problem_display import build_truss_geometry, member_field_key
from app.problems.base import ParamFieldSpec
from app.problems.registry import problem_registry
from app.problems.truss.generator import truss_generator


def _geometry(seed: int, params: Mapping[str, object]) -> dict[str, Any]:
    generated = truss_generator.generate(seed=seed, params=dict(params))
    return build_truss_geometry(generated.visual_schema)


def test_every_registered_generator_declares_a_catalogue_entry() -> None:
    generators = problem_registry.all()
    assert generators, "no generators registered"
    for generator in generators:
        assert generator.problem_type
        assert generator.display_name
        for field in generator.params_schema:
            assert isinstance(field, ParamFieldSpec)
            assert field.name
            assert field.label
            assert field.value_type in ("integer", "number")


def test_choice_knobs_declare_options_the_generator_actually_accepts() -> None:
    """A knob with `options` renders as a select, so the builder can only ever
    submit one of those values -- they must all be in range and the default must
    be selectable, or the form opens showing a blank choice."""
    for generator in problem_registry.all():
        for field in generator.params_schema:
            if field.options is None:
                continue
            assert field.options, f"{generator.problem_type}.{field.name}: empty option list"
            values = [o.value for o in field.options]
            assert len(values) == len(set(values)), f"{field.name}: duplicate option values"
            assert field.default in values, f"{field.name}: default is not one of its options"
            for option in field.options:
                assert option.label
                if field.minimum is not None:
                    assert option.value >= field.minimum
                if field.maximum is not None:
                    assert option.value <= field.maximum


def test_every_declared_knob_has_a_default_so_an_untouched_form_works() -> None:
    """An instructor who ignores the difficulty form must still get a problem."""
    for generator in problem_registry.all():
        for field in generator.params_schema:
            assert field.default is not None
            if field.minimum is not None:
                assert field.default >= field.minimum
            if field.maximum is not None:
                assert field.default <= field.maximum


def test_declared_defaults_reproduce_the_generators_own_behaviour() -> None:
    defaults = {f.name: f.default for f in truss_generator.params_schema}
    explicit = _geometry(seed=11, params={"problem_id": 1, **defaults})
    implicit = _geometry(seed=11, params={"problem_id": 1})
    assert explicit == implicit


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6, 8])
def test_num_nodes_changes_the_problem_size(num_nodes: int) -> None:
    g = _geometry(seed=3, params={"problem_id": 1, "num_nodes": num_nodes})
    assert len(g["nodes"]) == num_nodes
    # Determinate planar truss: m = 2n - 3
    assert len(g["members"]) == 2 * num_nodes - 3


@pytest.mark.parametrize("max_force", [1, 5, 20])
def test_max_force_bounds_load_magnitudes(max_force: int) -> None:
    seen: set[float] = set()
    for seed in range(40):
        g = _geometry(seed=seed, params={"problem_id": 1, "num_nodes": 5, "max_force": max_force})
        for force in g["forces"]:
            seen.add(round((force["fx"] ** 2 + force["fy"] ** 2) ** 0.5))
    assert seen
    assert min(seen) >= 1
    assert max(seen) <= max_force


@pytest.mark.parametrize("load_count", [1, 2])
def test_load_count_controls_how_many_loads_are_applied(load_count: int) -> None:
    for seed in range(20):
        g = _geometry(seed=seed, params={"problem_id": 1, "num_nodes": 6, "load_count": load_count})
        assert len(g["forces"]) == load_count


def test_load_count_is_clamped_to_available_joints() -> None:
    """A 3-joint truss has one free joint once supports are placed, so asking
    for more loads must clamp rather than raise."""
    g = _geometry(seed=5, params={"problem_id": 1, "num_nodes": 3, "load_count": 5})
    forces = g["forces"]
    assert 1 <= len(forces) <= 3
    nodes = [f["node_index"] if "node_index" in f else f["node"] for f in forces]
    assert len(nodes) == len(set(nodes)), "loads must land on distinct joints"


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6, 8])
@pytest.mark.parametrize("load_count", [1, 2])
def test_every_offered_combination_is_solvable_and_gradable(
    num_nodes: int, load_count: int
) -> None:
    """The builder must not be able to save a configuration a student cannot
    complete — the whole point of not exposing support profile."""
    for seed in range(8):
        params: dict[str, object] = {
            "problem_id": 1,
            "num_nodes": num_nodes,
            "max_force": 5,
            "load_count": load_count,
        }
        geometry = _geometry(seed=seed, params=params)
        ground_truth = truss_generator.solve(seed=seed, params=params)
        keys = list(ground_truth["member_solutions"].keys())
        members: list[dict[str, Any]] = geometry["members"]

        submitted = {
            member_field_key(int(m["id"])): (
                ground_truth["member_solutions"][keys[i]]["signed_force"]
            )
            for i, m in enumerate(members)
        }
        per_field = _check_answers(submitted, ground_truth["member_solutions"], members, 0.01)
        assert per_field
        assert all(per_field.values()), f"n={num_nodes} loads={load_count} seed={seed}"


def test_support_profile_is_not_offered_as_a_knob() -> None:
    """solve_support_reactions raises for anything but one pin plus one roller,
    so offering this would let an instructor save an unsolvable problem."""
    names = {f.name for f in truss_generator.params_schema}
    assert "support_profile" not in names
    assert "num_pins" not in names
    assert "num_rollers" not in names

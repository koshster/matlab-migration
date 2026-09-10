"""Ensures `assignment_problems.params` is the source of truth for problem config.

The router used to pass a synthetic `{"problem_id": index + 1}` and ignore the
stored `params` column entirely, so the node-count schedule hardcoded in
truss/generator.py won regardless of what was in the database. An assignment
builder would have appeared to save difficulty settings that did nothing —
exactly what ADR 0015 exists to prevent.
"""

import uuid
from typing import Any

import pytest

from app.api.v1.assignments import _generator_params
from app.services.problem_display import build_truss_geometry, member_field_key
from app.db.models import AssignmentProblem
from app.problems.base import AnswerSubmission
from app.problems.truss.generator import truss_generator

# The legacy MATLAB schedule, keyed by 1-based problem index.
LEGACY_NODE_SCHEDULE = [3, 3, 4, 4, 5, 5, 6, 6]


def _slot(order_index: int, params: dict[str, Any] | None) -> AssignmentProblem:
    return AssignmentProblem(
        id=uuid.uuid4(),
        assignment_id=uuid.uuid4(),
        problem_type="truss",
        order_index=order_index,
        params=params,
    )


def _node_count(seed: int, params: dict[str, Any]) -> int:
    display = truss_generator.generate(seed=seed, params=params)
    return len(build_truss_geometry(display.visual_schema)["nodes"])


def test_stored_params_override_the_hardcoded_schedule() -> None:
    # Wire index 1 would default to 3 nodes under the legacy schedule.
    ap = _slot(order_index=0, params={"num_nodes": 6})
    params = _generator_params(ap, index=1)

    assert params["num_nodes"] == 6
    assert _node_count(seed=2024, params=params) == 6


def test_empty_params_fall_back_to_the_legacy_schedule() -> None:
    """Slots created before the params column was honoured must keep working."""
    stored_options: list[dict[str, object] | None] = [{}, None]
    for index, expected_nodes in enumerate(LEGACY_NODE_SCHEDULE, start=1):
        for stored in stored_options:
            ap = _slot(order_index=index - 1, params=stored)
            params = _generator_params(ap, index=index)
            assert params == {"problem_id": index}
            assert _node_count(seed=99, params=params) == expected_nodes


def test_seeded_params_agree_with_the_legacy_schedule() -> None:
    """The seed script stores exactly the legacy node counts, so switching to
    DB-driven params must not change any existing student's problems."""
    for index, n in enumerate(LEGACY_NODE_SCHEDULE, start=1):
        ap = _slot(order_index=index - 1, params={"num_nodes": n})
        from_db = _generator_params(ap, index=index)
        from_schedule = {"problem_id": index}

        assert _node_count(seed=7, params=from_db) == _node_count(seed=7, params=from_schedule)


@pytest.mark.parametrize("num_nodes", [3, 4, 5, 6])
def test_check_grades_against_the_configured_problem(num_nodes: int) -> None:
    """`check()` dropped `params` and always re-solved the default 3-node truss,
    so a configured problem was graded against the wrong structure."""
    seed = 4242
    params = {"problem_id": 1, "num_nodes": num_nodes}

    solution = truss_generator.solve(seed, params)
    answers: dict[str, Any] = {}
    for key, data in solution["member_solutions"].items():
        answers[key] = data["magnitude"]
        answers[f"{key}_state"] = data["state"]

    result = truss_generator.check(
        seed=seed, submission=AnswerSubmission(answers=answers), tolerance=0.01, params=params
    )
    assert result.is_passed is True
    assert result.score == 1.0


def test_router_grading_path_agrees_with_the_displayed_problem() -> None:
    """The signed-force answers a student reads off the rendered diagram must be
    the ones the router's grading path accepts."""
    seed = 31337
    ap = _slot(order_index=4, params={"num_nodes": 6})
    params = _generator_params(ap, index=5)

    display = truss_generator.generate(seed=seed, params=params)
    geometry = build_truss_geometry(display.visual_schema)
    ground_truth = truss_generator.solve(seed=seed, params=params)

    keys = list(ground_truth["member_solutions"].keys())
    members = geometry["members"]
    assert len(members) == len(keys)

    from app.api.v1.assignments import _check_answers

    submitted = {
        member_field_key(m["id"]): ground_truth["member_solutions"][keys[i]]["signed_force"]
        for i, m in enumerate(members)
    }
    per_field = _check_answers(submitted, ground_truth["member_solutions"], members, 0.01)

    assert per_field, "no fields graded"
    assert all(per_field.values()), f"correct answers rejected: {per_field}"

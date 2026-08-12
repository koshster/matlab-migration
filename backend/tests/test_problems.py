import pytest
from app.problems.base import AnswerSubmission
from app.problems.registry import problem_registry
from app.problems.truss.generator import truss_generator


def test_registry_contains_truss():
    assert "truss" in problem_registry.list_types()
    gen = problem_registry.get("truss")
    assert gen.problem_type == "truss"


def test_truss_generator_reproducibility():
    seed = 42
    data1 = truss_generator.generate(seed)
    data2 = truss_generator.generate(seed)

    assert data1.problem_type == "truss"
    assert data1.seed == seed
    assert len(data1.visual_schema) == len(data2.visual_schema)
    assert len(data1.answer_schema) == len(data2.answer_schema)


def test_truss_generator_zero_solution_leakage():
    seed = 12345
    display_data = truss_generator.generate(seed)
    serialized = display_data.model_dump_json()

    # Security rule: solution keys must never appear in client payload
    assert "member_solutions" not in serialized
    assert "reactions" not in serialized
    assert "signed_force" not in serialized


def test_truss_generator_solve_and_check():
    seed = 999
    solution = truss_generator.solve(seed)

    assert "reactions" in solution
    assert "member_solutions" in solution

    # Formulate correct student submission
    correct_answers = {}
    for member_key, mem_data in solution["member_solutions"].items():
        correct_answers[member_key] = mem_data["magnitude"]
        correct_answers[f"{member_key}_state"] = mem_data["state"]

    submission = AnswerSubmission(answers=correct_answers)
    result = truss_generator.check(seed, submission)

    assert result.is_passed is True
    assert result.score == 1.0

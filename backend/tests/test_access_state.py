"""Truth table for the assignment/problem access state machine.

Pure logic, no database. The naive-datetime cases matter: SQLite drops the
offset on read, so a deadline round-tripped through the test database comes
back naive and would raise TypeError on comparison without normalization.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.access import (
    CORRECT_DETAIL,
    LOCKED_DETAIL,
    as_utc,
    assert_writable,
    compute_access,
    effective_close_at,
    isoformat_utc,
    lock_reason_for_problem,
    problem_access,
    problem_status,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)
LATER = NOW + timedelta(days=7)


def assignment(**kw: object) -> SimpleNamespace:
    base = {
        "due_at": None,
        "hard_deadline_at": None,
        "allow_late": False,
        "reveal_solutions_after_close": False,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def session(submitted_at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(submitted_at=submitted_at)


def submission(passed: bool, attempt: int = 1) -> SimpleNamespace:
    return SimpleNamespace(is_passed=passed, attempt_number=attempt, answers={})


# --------------------------------------------------------------------------
# effective_close_at
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("due", "hard", "allow_late", "expected"),
    [
        (None, None, False, None),  # no dates -> never auto-closes
        (None, None, True, None),
        (FUTURE, None, False, FUTURE),  # due date closes it
        (FUTURE, None, True, FUTURE),  # late allowed, no hard cutoff -> due
        (FUTURE, LATER, False, FUTURE),  # no late work -> earliest boundary
        (FUTURE, LATER, True, LATER),  # late allowed -> hard deadline is real
        (None, LATER, False, LATER),
        (None, LATER, True, LATER),
        (LATER, FUTURE, False, FUTURE),  # misconfigured: earliest still wins
    ],
)
def test_effective_close_at(
    due: datetime | None, hard: datetime | None, allow_late: bool, expected: datetime | None
) -> None:
    a = assignment(due_at=due, hard_deadline_at=hard, allow_late=allow_late)
    assert effective_close_at(a) == expected


def test_effective_close_at_normalizes_naive_datetimes() -> None:
    """A deadline read back from SQLite is naive; it must still compare."""
    naive = datetime(2026, 12, 15, 23, 59)
    a = assignment(due_at=naive)
    assert effective_close_at(a) == naive.replace(tzinfo=UTC)
    # The comparison inside compute_access must not raise.
    assert compute_access(a, session(), now=NOW).access == "open"


# --------------------------------------------------------------------------
# compute_access
# --------------------------------------------------------------------------


def test_open_when_no_dates_and_not_submitted() -> None:
    state = compute_access(assignment(), session(), now=NOW)
    assert state.access == "open"
    assert state.closed is False
    assert state.close_reason is None
    assert state.closes_at is None


def test_closed_once_past_due() -> None:
    state = compute_access(assignment(due_at=PAST), session(), now=NOW)
    assert state.closed is True
    assert state.close_reason == "past_due"
    assert state.closes_at == PAST


def test_open_before_due() -> None:
    assert compute_access(assignment(due_at=FUTURE), session(), now=NOW).closed is False


def test_closed_on_submit_even_with_no_deadline() -> None:
    state = compute_access(assignment(), session(submitted_at=PAST), now=NOW)
    assert state.closed is True
    assert state.close_reason == "submitted"


def test_submitted_outranks_past_due() -> None:
    state = compute_access(assignment(due_at=PAST), session(submitted_at=PAST), now=NOW)
    assert state.close_reason == "submitted"


def test_late_work_stays_open_between_due_and_hard_deadline() -> None:
    a = assignment(due_at=PAST, hard_deadline_at=FUTURE, allow_late=True)
    assert compute_access(a, session(), now=NOW).closed is False


def test_late_work_closes_at_the_hard_deadline() -> None:
    a = assignment(due_at=PAST - timedelta(days=1), hard_deadline_at=PAST, allow_late=True)
    state = compute_access(a, session(), now=NOW)
    assert state.closed is True
    assert state.close_reason == "past_due"


def test_closes_exactly_at_the_boundary() -> None:
    """The deadline instant itself is closed, not the last open moment."""
    assert compute_access(assignment(due_at=NOW), session(), now=NOW).closed is True


# --------------------------------------------------------------------------
# reveal gate
# --------------------------------------------------------------------------


def test_reveal_requires_both_closed_and_opt_in() -> None:
    opted_in_open = assignment(due_at=FUTURE, reveal_solutions_after_close=True)
    assert compute_access(opted_in_open, session(), now=NOW).reveal_solutions is False

    closed_not_opted = assignment(due_at=PAST)
    assert compute_access(closed_not_opted, session(), now=NOW).reveal_solutions is False

    both = assignment(due_at=PAST, reveal_solutions_after_close=True)
    assert compute_access(both, session(), now=NOW).reveal_solutions is True


# --------------------------------------------------------------------------
# problem level
# --------------------------------------------------------------------------


def test_problem_editable_until_correct() -> None:
    state = compute_access(assignment(), session(), now=NOW)
    assert problem_access(state, []) == "editable"
    assert problem_access(state, [submission(False)]) == "editable"
    assert problem_access(state, [submission(False), submission(True, 2)]) == "locked_correct"


def test_closed_assignment_closes_every_problem() -> None:
    state = compute_access(assignment(due_at=PAST), session(), now=NOW)
    assert problem_access(state, []) == "closed"
    assert problem_access(state, [submission(True)]) == "closed"


def test_problem_status_vocabulary() -> None:
    assert problem_status([]) == "no_attempt"
    assert problem_status([submission(False)]) == "incorrect"
    assert problem_status([submission(False), submission(True, 2)]) == "correct"


def test_assert_writable_messages() -> None:
    assert assert_writable("editable") is None

    with pytest.raises(HTTPException) as closed:
        assert_writable("closed")
    assert closed.value.status_code == 403
    assert closed.value.detail == LOCKED_DETAIL

    with pytest.raises(HTTPException) as correct:
        assert_writable("locked_correct")
    assert correct.value.status_code == 403
    assert correct.value.detail == CORRECT_DETAIL


def test_lock_reason_wire_values() -> None:
    open_state = compute_access(assignment(), session(), now=NOW)
    assert lock_reason_for_problem(open_state, "editable") is None
    assert lock_reason_for_problem(open_state, "locked_correct") == "correct"

    due_state = compute_access(assignment(due_at=PAST), session(), now=NOW)
    assert lock_reason_for_problem(due_state, "closed") == "past_due"

    sub_state = compute_access(assignment(), session(submitted_at=PAST), now=NOW)
    assert lock_reason_for_problem(sub_state, "closed") == "submitted"


def test_isoformat_always_carries_an_offset() -> None:
    """A naive stored value must not serialize as ambiguous local time."""
    assert isoformat_utc(None) is None
    assert isoformat_utc(datetime(2026, 12, 15, 23, 59)).endswith("+00:00")
    assert as_utc(NOW) is NOW

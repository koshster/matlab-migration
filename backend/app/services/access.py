"""Single source of truth for assignment and problem access state.

Every comparison of a deadline against the clock in this codebase goes through
this module. Before it existed the predicate ``locked = bool(sa.submitted_at)``
was copy-pasted into three routers and the date columns were never read at all,
so ``due_at`` was decorative.

Two levels, resolved with strict precedence:

* the **assignment** is either ``open`` or ``closed`` -- closed once the student
  submits, or once the effective deadline passes under the late policy;
* each **problem** is ``editable``, ``locked_correct`` (already answered
  correctly, so the answer stands), or ``closed``.

Transitions are one-way. A passing submission is immutable audit history, and
an assignment that has closed does not reopen if an instructor later extends
the due date -- see docs/OPEN_QUESTIONS.md.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status

from app.db.models import Assignment, StudentAssignment, Submission

AssignmentAccess = Literal["open", "closed"]
ProblemAccess = Literal["editable", "locked_correct", "closed"]
CloseReason = Literal["submitted", "past_due"]
ProblemStatus = Literal["no_attempt", "incorrect", "correct"]

# Preserved verbatim: existing clients and tests match on this string.
LOCKED_DETAIL = "Assignment is locked"
CORRECT_DETAIL = "This problem is already correct and can no longer be changed"


def as_utc(value: datetime | None) -> datetime | None:
    """Normalize a stored datetime to an aware UTC value.

    Postgres hands back aware datetimes; SQLite -- which every test in this
    suite runs on -- drops the offset and returns naive ones. Comparing the two
    raises TypeError, so every deadline read passes through here first.
    """
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def effective_close_at(assignment: Assignment) -> datetime | None:
    """The instant this assignment stops accepting work, or None if it never does.

    ``allow_late`` is what makes ``hard_deadline_at`` meaningful: with late work
    permitted, the due date is advisory and the hard deadline is the real
    cutoff. With late work forbidden, the earliest configured boundary closes
    it -- taking the minimum rather than trusting ``due_at`` blindly keeps a
    misconfigured pair (hard deadline before due date) from silently extending
    the assignment.
    """
    due = as_utc(assignment.due_at)
    hard = as_utc(assignment.hard_deadline_at)
    if assignment.allow_late:
        return hard or due
    if due is not None and hard is not None:
        return min(due, hard)
    return due or hard


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(UTC)


@dataclass(frozen=True)
class AccessState:
    """Resolved access for one student against one assignment."""

    access: AssignmentAccess
    close_reason: CloseReason | None
    closes_at: datetime | None
    reveal_solutions: bool

    @property
    def closed(self) -> bool:
        return self.access == "closed"


def compute_access(
    assignment: Assignment,
    student_assignment: StudentAssignment,
    now: datetime | None = None,
) -> AccessState:
    """Resolve assignment-level access. The only place `closed` is decided."""
    closes_at = effective_close_at(assignment)

    reason: CloseReason | None = None
    if student_assignment.submitted_at is not None:
        # An explicit submit outranks the deadline even if both apply, because
        # it is the more specific fact about what the student did.
        reason = "submitted"
    elif closes_at is not None and _now(now) >= closes_at:
        reason = "past_due"

    return AccessState(
        access="closed" if reason is not None else "open",
        close_reason=reason,
        closes_at=closes_at,
        reveal_solutions=(reason is not None and bool(assignment.reveal_solutions_after_close)),
    )


def problem_access(state: AccessState, submissions: Sequence[Submission]) -> ProblemAccess:
    """Resolve access for a single problem within an assignment."""
    if state.closed:
        return "closed"
    if any(s.is_passed for s in submissions):
        return "locked_correct"
    return "editable"


def problem_status(submissions: Sequence[Submission]) -> ProblemStatus:
    if any(s.is_passed for s in submissions):
        return "correct"
    if submissions:
        return "incorrect"
    return "no_attempt"


def assert_writable(access: ProblemAccess) -> None:
    """Reject a write to a non-editable problem.

    The only place these 403 messages are written. Server-side enforcement is
    the real gate -- the read-only UI is an affordance, not a control.
    """
    if access == "closed":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=LOCKED_DETAIL)
    if access == "locked_correct":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=CORRECT_DETAIL)


def lock_reason_for_problem(state: AccessState, access: ProblemAccess) -> str | None:
    """Wire-facing explanation of why a problem is read-only."""
    if access == "locked_correct":
        return "correct"
    if access == "closed":
        return state.close_reason
    return None


def isoformat_utc(value: datetime | None) -> str | None:
    """Serialize a stored timestamp with an explicit offset.

    Without normalizing first, a value read back from a naive store serializes
    without an offset and a browser parses it as local time -- silently wrong
    by however many hours the user is from UTC.
    """
    normalized = as_utc(value)
    return normalized.isoformat() if normalized is not None else None

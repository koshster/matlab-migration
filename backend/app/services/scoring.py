"""Score computation and answer-recovery rules.

Scoring honours ``assignment_problems.points``. That column has existed since
the initial migration and was written by the assignment builder but read
nowhere -- every score was a count of solved problems. Weighting by points is
what the build spec asks for, and it is a no-op for existing data because every
seeded slot uses the default 1.0.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from app.db.models import AssignmentProblem, Submission
from app.services.access import ProblemAccess, ProblemStatus, problem_status

SubmissionsByProblem = Mapping[uuid.UUID, list[Submission]]


@dataclass(frozen=True)
class ProblemScore:
    index: int
    problem_type: str
    gradeable: bool
    status: ProblemStatus
    points: float
    earned: float
    attempt_count: int
    last_attempt_at: datetime | None


@dataclass(frozen=True)
class ScoreBreakdown:
    earned: float
    total: float
    problems: list[ProblemScore]


def _ordered(submissions: Sequence[Submission]) -> list[Submission]:
    return sorted(submissions, key=lambda s: s.attempt_number)


def compute_score(
    problems: Sequence[AssignmentProblem],
    subs_by_problem: SubmissionsByProblem,
    is_gradeable: "Mapping[str, bool] | None" = None,
) -> ScoreBreakdown:
    """Points-weighted score.

    Problems whose type has no server-side solver are excluded from both the
    numerator and the denominator, so an unimplemented slot cannot silently
    cost every student a point.
    """
    rows: list[ProblemScore] = []
    earned = 0.0
    total = 0.0

    for offset, ap in enumerate(sorted(problems, key=lambda p: p.order_index)):
        submissions = _ordered(subs_by_problem.get(ap.id, []))
        gradeable = True if is_gradeable is None else is_gradeable.get(ap.problem_type, False)
        status = problem_status(submissions)
        points = float(ap.points)
        got = points if (gradeable and status == "correct") else 0.0

        if gradeable:
            total += points
            earned += got

        rows.append(
            ProblemScore(
                index=offset + 1,
                problem_type=ap.problem_type,
                gradeable=gradeable,
                status=status,
                points=points,
                earned=got,
                attempt_count=len(submissions),
                last_attempt_at=submissions[-1].submitted_at if submissions else None,
            )
        )

    return ScoreBreakdown(earned=earned, total=total, problems=rows)


def resolve_saved_answers(
    slot: int,
    draft_answers: Mapping[str, object] | None,
    submissions: Sequence[Submission],
    access: ProblemAccess,
    field_keys: Sequence[str],
) -> dict[str, float | None]:
    """Which answers to show for a problem, by access state.

    * ``locked_correct`` -- the answers from the submission that passed. The
      fields are read-only, so they must show what actually earned the credit,
      not a later draft the student typed over the top.
    * ``closed`` -- the passing answers if any, else the newest attempt, else
      the draft. A student who typed but never checked still sees their work.
    * ``editable`` -- the draft, falling back to the newest attempt. The
      fallback repairs an older bug: ``check`` recorded answers on the
      submission but not the draft, so a checked-but-unsaved answer vanished on
      reload.

    Answers are filtered to the problem's own field keys and never padded --
    a missing key means "not answered", which is not the same as null.
    """
    ordered = _ordered(submissions)
    passing = next((s for s in ordered if s.is_passed), None)
    draft = (draft_answers or {}).get(str(slot))

    source: object | None
    if access == "locked_correct":
        source = passing.answers if passing is not None else draft
    elif access == "closed":
        if passing is not None:
            source = passing.answers
        elif ordered:
            source = ordered[-1].answers
        else:
            source = draft
    else:
        source = draft if draft else (ordered[-1].answers if ordered else None)

    if not isinstance(source, dict):
        return {}

    allowed = set(field_keys)
    return {k: v for k, v in source.items() if k in allowed}

# ADR 0017 — Assignment Close State: Deadline-Driven, One-Way, Lazily Finalized

**Status:** Accepted

## Decision
`locked` stops meaning "the student pressed Submit" and becomes a resolved close
state computed in `app/services/access.py`:

- **effective close** = `hard_deadline_at` when `allow_late` is on, otherwise the
  earliest of `due_at` and `hard_deadline_at`;
- an assignment is **closed** once submitted or once that instant passes;
- a **problem** is `editable`, `locked_correct` (already answered correctly), or
  `closed`.

A deadline-closed session is finalized lazily on read: `finalized_at` and
`final_score` are written by a guarded `UPDATE ... WHERE finalized_at IS NULL`,
stamped with the deadline instant rather than `now()`.

Scores are weighted by `assignment_problems.points`, which existed since the
initial migration and was read nowhere.

## Reason
`due_at`, `opens_at`, `hard_deadline_at`, `allow_late` and `late_penalty_rate`
were all persisted and never consulted, so the contract's own promise
(`locked: true once submitted or past a hard close`) was unimplemented.

`finalized_at` is deliberately separate from `submitted_at`: an assignment that
closed on its deadline is final, but the student never submitted, and recording
otherwise would report submissions to the instructor that never happened.

Finalization is lazy because there is no scheduler in the stack, and adding one
for a single row update would need a new dependency (standing rule 8). Because
the stamped value is derived from the deadline rather than the clock, two
concurrent finalizers compute an identical value, so the guarded UPDATE makes
the write single-shot without a lock.

## Consequences
- `AssignmentSummary.status` gains `closed`, distinct from `submitted`.
- Closure is **one-way**: extending `due_at` after a student was finalized does
  not reopen them. A reopen endpoint is deliberately out of scope.
- `opens_at` is carried on the wire but **not enforced** — enforcing it would
  mean raising inside the resolver that `tests/test_assignment_access.py`
  asserts performs no gating.
- Every deadline read goes through `as_utc()`. SQLite drops the offset, so a
  stored deadline comes back naive and comparing it to an aware `now()` raises.
- Points weighting is a no-op for existing data (every seeded slot uses 1.0).

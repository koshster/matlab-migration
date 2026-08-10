# ADR 0011 — Feedback Granularity: Per-Field, Configurable Per Assignment

**Status:** Accepted

## Decision
Default feedback mode is `per_field`: the check response identifies which specific members are wrong. Mode is configurable per assignment (`binary` | `per_field`). The frontend never computes correctness.

## Reason
Per-field feedback is better pedagogy — students know which members to revisit. `binary` mode matches the legacy MATLAB app behavior exactly and can be set by the instructor without a code change. Keeping the mode as a DB column (not hardcoded) means Prof. Marko can adjust it per assignment.

## Consequences
- `CheckResult.perField` is `Record<string, boolean> | null` — null when `feedbackMode='binary'`.
- The `FeedbackPanel` renders per-field data when present; it never derives correctness itself.
- `assignments.feedback_mode` column; default `'per_field'`.

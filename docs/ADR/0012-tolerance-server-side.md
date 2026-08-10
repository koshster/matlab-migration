# ADR 0012 — Tolerance: Server-Side, Per-Assignment, Default 0.01

**Status:** Accepted

## Decision
Grading tolerance is stored as `assignments.tolerance numeric default 0.01`. It is applied server-side during `POST /check`. The frontend must not know tolerance exists.

## Reason
The MATLAB app hardcoded `abs(user_ans - correct_ans) > 0.01` in the UI code. Moving tolerance to a DB column lets Prof. Marko tighten or loosen it per assignment without a code change.

## Consequences
- The frontend sends raw answer values and receives a verdict. It never sees the tolerance value.
- The seed-based regeneration in `POST /check` uses the same RNG as generation, so the comparison is exact.
- Default `0.01` preserves legacy behavior.

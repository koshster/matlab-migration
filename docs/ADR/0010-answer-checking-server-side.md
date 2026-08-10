# ADR 0010 — Answer Checking: Server-Side Only

**Status:** Accepted

## Decision
All answer checking and solution comparison happens on the backend. Solutions are never sent to the client.

## Reason
The legacy MATLAB app held solutions in client memory — a student could trivially extract the correct answers. The new system regenerates the problem from seed and compares answers within the configured tolerance entirely on the server. Solutions appear in exactly one place: the instructor `replay` endpoint.

## Consequences
- `POST /assignments/{slug}/problems/{index}/check` is the only grading endpoint.
- Every student response model must be audited for solution fields (automated test required).
- The frontend receives a `CheckResult` (correct/incorrect + optional per-field breakdown) but never the solution values.

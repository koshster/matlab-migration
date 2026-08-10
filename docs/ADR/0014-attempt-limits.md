# ADR 0014 — Attempt Limits: Unlimited by Default, Nullable max_attempts

**Status:** Accepted

## Decision
Attempt limits are unlimited by default. `assignments.max_attempts int null` — null means unlimited. The limit is enforced server-side in `POST /check`.

## Reason
Preserves the legacy MATLAB app behavior (no limit). The nullable column leaves the door open for future use without a schema migration.

## Consequences
- `POST /check` must reject attempts beyond `max_attempts` when set, returning a 409 or 403.
- `ProblemPayload.maxAttempts` is `number | null`; the frontend uses it only for display (e.g., "3 of 5 attempts used").
- The frontend never enforces the limit — it always sends the check request and handles a rejection response.

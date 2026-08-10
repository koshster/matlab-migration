# ADR 0008 — Student Auth: PID + Name Entry, Swappable AuthProvider

**Status:** Accepted

## Decision
Students authenticate by entering their PID, first name, and last name. No password. The auth logic is behind a swappable `AuthProvider` interface.

## Reason
Matches the existing MATLAB app UX. Students already know their PID. The `AuthProvider` seam means SSO (e.g., UCSD Shibboleth) can be added later without touching routes or components.

## Consequences
- `POST /auth/student/session` accepts `{ externalId, firstName, lastName, assignmentSlug }`.
- A 409 `ALREADY_SUBMITTED` response routes the student to a locked results screen.
- The `AuthProvider` is the only place that touches student identity; everything else uses the internal UUID.

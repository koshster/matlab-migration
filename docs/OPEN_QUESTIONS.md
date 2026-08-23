# Open Questions

Document ambiguities here, pick the conservative default, and revisit with Prof. Marko.

| # | Question | Conservative default | Status |
|---|---|---|---|
| 1 | Hosting target — UCSD infrastructure vs. cloud? | Containerized (deferrable to Phase 8) | Open |
| 2 | UCSD SSO integration? | PID+name entry via swappable `AuthProvider` | Open |
| 3 | Student identifier — PID or course-specific ID? | PID assumed | Open |
| 4 | FERPA retention/access requirements? | Confirm before pilot | Open |
| 5 | Second problem type for Phase 7 — which statics problem? | Single-beam reaction problem | Open |
| 6 | Feedback strictness default — `per_field` or `binary`? | `per_field` (better pedagogy; toggle per assignment) | Decided |
| 7 | CSRF tokens + login rate limiting (ADR 0009 promises both) | Deferred to Phase 8 hardening; same-site httpOnly cookie in the interim | Open |
| 8 | Strict email validation — worth the `pydantic[email]` dependency? | Structural check in `app/core/identity.py`; revisit if we send mail (roster invites) | Open |
| 9 | PID normalization (case/whitespace) for invite matching | Lands with Phase B's `pid_normalized` column + backfill; normalizing before then would break existing logins | Open |
| 10 | Support profile as a difficulty knob | Not exposed — `solve_support_reactions` raises for anything but 1 pin + 1 roller; the legacy 0-pin/3-roller branch is unported | Open |

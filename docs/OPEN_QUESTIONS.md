# Open Questions

Document ambiguities here, pick the conservative default, and revisit with Prof. Marko.

| # | Question | Conservative default | Status |
|---|---|---|---|
| 1 | Hosting target — UCSD infrastructure vs. cloud? | Containerized (deferrable to Phase 8) | Open |
| 2 | UCSD SSO integration? | PID+name entry via swappable `AuthProvider` | Open |
| 3 | Student identifier — PID or course-specific ID? | PID assumed | Open |
| 4 | FERPA retention/access requirements? | Confirm before pilot | Open |
| 5 | Second problem type for Phase 7 — which statics problem? | 2D rigid-body equilibrium (merged 2026-09-05); `beam` remains a stub | Decided |
| 6 | Feedback strictness default — `per_field` or `binary`? | `per_field` (better pedagogy; toggle per assignment) | Decided |
| 7 | CSRF tokens + login rate limiting (ADR 0009 promises both) | Deferred to Phase 8 hardening; same-site httpOnly cookie in the interim | Open |
| 8 | Strict email validation — worth the `pydantic[email]` dependency? | Structural check in `app/core/identity.py`; revisit if we send mail (roster invites) | Open |
| 9 | PID normalization (case/whitespace) for invite matching | Lands with Phase B's `pid_normalized` column + backfill; normalizing before then would break existing logins | Open |
| 10 | Support profile as a difficulty knob | Not exposed — `solve_support_reactions` raises for anything but 1 pin + 1 roller; the legacy 0-pin/3-roller branch is unported | Open |
| 11 | Should a closed assignment reopen if an instructor extends `due_at`? | No — closure is one-way; a reopen endpoint is deliberately out of scope | Open |
| 12 | Is `opens_at` enforced, or advisory? | Advisory — carried on the wire, never gates access, since the direct-slug route intentionally performs no gating | Open |
| 13 | Which denominator does per-problem "success rate" use? | Correct ÷ attempted; students who never attempted are excluded | Decided |
| 14 | Grading tolerance is relative (`tol × max(|true|, 1)`), not the absolute 0.01 the legacy app used | Left relative — it is strictly more lenient at the rounding precision students are asked for | Open |
| 15 | `good_pin_support_orientation`'s docstring and its guard disagree on what support `rotation` means — the prose says 90 is "base left", the code accepts 90 only when nothing extends to `+x` (i.e. base right) | Guard wins; the frontend draws 90 as base-right. Measured over 200 seeds: the docstring reading puts a support base through the body 392/1194 times vs 202 for the guard, and 55 vs 0 for pins alone | Open — Rushil to confirm and fix the prose |
| 16 | Some moment `arrow_angle` values in `loads.py` open the couple arc toward the body instead of the free side, so a couple next to a support renders crowded | Renderer draws the generator faithfully; the placement table is what needs adjusting | Open — cosmetic |
| 17 | Grading-vs-rendering are separate registries: a type can be gradeable server-side with no diagram, or vice versa. Should the assignment builder warn when it offers a type missing either half? | Not warned today; `beam` is currently offerable, ungradeable and unrendered | Open |
| 18 | Truss roller rotation comes from `get_outward_rotation` (centroid direction only, `truss/supports.py:6`), with no equivalent of rigid body's `good_pin_support_orientation` guard, so the glyph can be drawn straight through a member — e.g. seed 7 / 8 nodes puts the roller at (2,1) at rotation 270 along the top chord, and seed 42 / 8 nodes puts it at (0,1) at rotation 0 on top of a vertical | Renderer draws the generator faithfully; the orientation choice is what needs the surroundings check | Open — cosmetic, Rushil |

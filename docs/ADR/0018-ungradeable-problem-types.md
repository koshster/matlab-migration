# ADR 0018 — Unimplemented Problem Types Are Explicitly Ungradeable

**Status:** Accepted

## Decision
`app/api/v1/assignments.py` holds `GRADEABLE_TYPES`, currently
`frozenset({"truss", "rigid_body"})`. A
registered type outside that set is **displayable but not answerable**: `GET`
returns 200 with a null geometry, an empty answer schema and
`lockReason: "unavailable"`, while `PUT answers` and `POST check` return **501**.
An unregistered type is a **404**. Ungradeable slots are excluded from the score
denominator.

## Reason
`beam` and `rigid_body` were registered so the assignment builder could list
them, but their `solve()` returned no solution. The student route built every
problem's
geometry through the truss builder unconditionally, so a beam problem produced a
nonsense one-member "truss" and graded as wrong for any input — reproduced
against the seeded `hw1` assignment, where `check` returned
`perField: {"S1": false}` regardless of the answer. The same expression had a
vacuous-truth sibling: with no fields at all, `all({})` is `True`, so a
fieldless problem graded as fully correct.

Counting an unimplemented slot in the denominator would cost every student a
point they had no way to earn.

## Consequences
- 200-with-a-flag on `GET`, not 501, so one unimplemented slot cannot break the
  review page for a whole assignment. The frontend renderer registry already
  falls back for an unknown type.
- The gate lives in the API layer, not the generator Protocol. Moving grading
  knowledge down into the generators is the right long-term refactor and needs
  its own ADR; doing it here would also invalidate the generator-contract tests
  that assert the stubs' current behaviour.
- `GRADEABLE_TYPES` must gain an entry when a real solver lands for a type.

## Amendment — 2026-09-05 (merge of `Rigid_Body_Backend`)
`rigid_body` now has a real solver, so it joined `GRADEABLE_TYPES`. `beam` is
still a stub (`solve()` returns `{"Ay": 0.0, "By": 0.0}`) and stays out.

That merge also added the generic, non-truss path through `get_problem` and
`check_answers`, which is the first type served from the generator-declared
answer schema instead of the truss member builders. Two invariants this ADR
records had to be carried onto that path explicitly rather than inherited:

- **The vacuous-correct guard.** The generic arm grades via
  `GradingResult.is_passed`. A domain with no expected fields scores 0/0, so
  `len(per_field) > 0` is still checked here rather than trusting each
  generator to treat that as a failure.
- **The reveal gate.** `solve()` returns a whole ground-truth blob —
  rigid_body ships `supports` alongside `reactions` — so
  `_generic_solution_answers` projects it down to exactly the field keys the
  student was shown, the same second wall `_solution_answers` gives truss.

A type being gradeable does not make it renderable: the two are independent
registries. `rigid_body` gained its frontend renderer separately.

## Amendment — 2026-09-10 (feat/rigid-body-deck-styling)
`GET /admin/problem-types` now filters by `GRADEABLE_TYPES`, so `beam` is no
longer offered in the assignment builder UI. The old behaviour (all registered
types were offered) let the builder default to `beam` (import order alphabetic),
producing problems with `lockReason: "unavailable"` that students could never
solve. Open Question #17 is closed: the conservative default is to hide
unimplemented types from the builder entirely.

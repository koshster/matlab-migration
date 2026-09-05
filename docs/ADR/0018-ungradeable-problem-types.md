# ADR 0018 — Unimplemented Problem Types Are Explicitly Ungradeable

**Status:** Accepted

## Decision
`app/api/v1/assignments.py` holds `GRADEABLE_TYPES = frozenset({"truss"})`. A
registered type outside that set is **displayable but not answerable**: `GET`
returns 200 with a null geometry, an empty answer schema and
`lockReason: "unavailable"`, while `PUT answers` and `POST check` return **501**.
An unregistered type is a **404**. Ungradeable slots are excluded from the score
denominator.

## Reason
`beam` and `rigid_body` are registered so the assignment builder can list them,
but their `solve()` returns no solution. The student route built every problem's
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

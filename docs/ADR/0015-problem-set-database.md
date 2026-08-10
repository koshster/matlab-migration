# ADR 0015 — Problem Set Definition: Database Rows, Not Hardcoded Arrays

**Status:** Accepted

## Decision
Problem sets are defined as `assignment_problems` rows with `params jsonb`. The legacy `numNodes = [3,3,4,4,5,5,6,6]` array becomes 8 DB rows seeded via migration.

## Reason
Prof. Marko can build and modify assignments without a code deploy. The admin dashboard (Phase 6) exposes an assignment builder UI. Different courses or semesters can have different node count sequences without touching the backend code.

## Consequences
- The seed script inserts 8 `assignment_problems` rows: `params = {"numNodes": 3}` etc.
- The generator receives `params: dict` and reads `numNodes` from it.
- Adding a new problem type requires only a new generator class and a new `problem_type` slug — no router or schema changes.

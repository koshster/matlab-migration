# ADR 0007 — Student Identity: PID as external_id, UUID as PK

**Status:** Accepted

## Decision
Students are identified by their university PID (`external_id text unique`). The internal primary key is a UUID. PIDs never appear in URLs or as foreign keys.

## Reason
PID is the existing identifier in the MATLAB app. Separating it from the PK means the internal data model is stable even if the identifier scheme changes (e.g., switching to a course-specific ID).

## Consequences
- All URLs use the internal UUID or an assignment slug.
- PIDs must never appear in logs, error messages, or URLs (standing rule #7).
- If UCSD switches to a non-PID identifier, only `students.external_id` semantics change.

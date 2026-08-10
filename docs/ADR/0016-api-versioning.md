# ADR 0016 — API Versioning: URL Prefix /api/v1 + schemaVersion in Payloads

**Status:** Accepted

## Decision
All routes are prefixed `/api/v1`. Problem geometry payloads include a `schemaVersion: 1` field.

## Reason
Geometry schemas will evolve as new problem types are added (truss geometry ≠ beam geometry). The URL prefix allows a `v2` to coexist with `v1` during a rolling migration. `schemaVersion` inside the payload lets the frontend renderer registry detect and handle breaking geometry changes without a full API version bump.

## Consequences
- `ProblemPayload.schemaVersion` is always present and checked by the frontend before rendering.
- New routes go under `/api/v1` until a breaking change requires `/api/v2`.
- The OpenAPI `servers` block must include both versions during any migration window.

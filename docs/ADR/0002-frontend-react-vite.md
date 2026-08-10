# ADR 0002 — Frontend: React 18 + TypeScript + Vite

**Status:** Accepted

## Decision
Use React 18 with TypeScript, built and served via Vite.

## Reason
Typed client can be generated from the OpenAPI contract. React's component model maps naturally to the renderer-registry pattern needed for multiple problem types. Vite provides fast HMR for development.

## Consequences
- `tsc --noEmit` must pass in CI; no `as any`.
- All component props are typed against contract-generated types.
- A renderer registry (`problems/registry.ts`) maps `problemType` strings to React components — no shared component may hardcode problem-type names.

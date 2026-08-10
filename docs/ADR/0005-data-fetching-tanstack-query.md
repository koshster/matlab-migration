# ADR 0005 — Data Fetching: TanStack Query

**Status:** Accepted

## Decision
Use TanStack Query (React Query v5) for all server-state fetching and mutation.

## Reason
Per-problem caching avoids re-fetching unchanged problems during navigation. Mutation state (saving, checking answers) is managed without manual loading flags. Retry logic handles transient network failures gracefully.

## Consequences
- A `QueryClient` is provided at the app root.
- Each API hook corresponds to one route in the contract; no ad-hoc `fetch` calls in components.
- The MSW mock layer (Phase 1) intercepts at the network level, so hooks work identically against mocks and the real API.

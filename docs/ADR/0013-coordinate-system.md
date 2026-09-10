# ADR 0013 — Coordinate System: Backend Emits y-Up, Frontend Flips in SVG

**Status:** Accepted

## Decision
The backend emits engineering coordinates (y-up, origin bottom-left). The frontend applies a single SVG transform to flip the y-axis. This transform lives only in the renderer component.

## Reason
Physics solvers work in y-up. SVG uses y-down. Keeping the backend in the physics domain means the solver code is readable without mental coordinate flips. The flip is a one-liner in an SVG `<g transform="scale(1,-1)">` or equivalent.

## Consequences
- The frontend computes `viewBox` from the geometry coordinates via `plotWindow()` (floor(min)−1 to ceil(max)+1 per axis, snapped to the integer grid). `TrussGeometry.bounds` is emitted by the backend but not read by the renderer.
- The y-flip is the only place where coordinate systems are transformed. No other component touches it.
- Labels and arrowheads must be counter-rotated after the flip so they appear right-side up.

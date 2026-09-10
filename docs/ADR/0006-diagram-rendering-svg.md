# ADR 0006 — Diagram Rendering: Hand-written SVG Components

**Status:** Accepted

## Decision
Render problem diagrams as hand-written React SVG components, not via a third-party diagramming library.

## Reason
The MATLAB `figPkg` is small and well-understood (~5 files). A direct port to SVG gives pixel-perfect control over arrowheads, member labels, support symbols, and the coordinate-system flip (y-up engineering → y-down SVG). No library dependency needed; this avoids a large dependency for a narrow use case.

## Consequences
- `TrussDiagram.tsx` contains `Member`, `Node` subcomponents; support and force primitives live in `problems/shared/`.
- `viewBox` is computed by the frontend from the geometry coordinates via `plotWindow()` (floor/ceil ±1). The backend does not emit a `bounds` field that the frontend reads.
- The backend emits engineering coordinates (y-up); the SVG transform flips y. This is the only place the flip occurs.
- Visual primitives shared across renderers (`constants.ts`, `Axes`, `FlipText`, `PinSupport`, `RollerSupport`, `WallSupport`, `ForceArrow`, `SupportGlyph`, `plotWindow`, `labels`) live in `problems/shared/`. Problem-type-specific files (`Member`, `Node`, `TrussDiagram`, `RigidBodyDiagram`, `MomentArc`, `schema`) stay in their own directories.

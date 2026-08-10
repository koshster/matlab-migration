# ADR 0006 — Diagram Rendering: Hand-written SVG Components

**Status:** Accepted

## Decision
Render problem diagrams as hand-written React SVG components, not via a third-party diagramming library.

## Reason
The MATLAB `figPkg` is small and well-understood (~5 files). A direct port to SVG gives pixel-perfect control over arrowheads, member labels, support symbols, and the coordinate-system flip (y-up engineering → y-down SVG). No library dependency needed; this avoids a large dependency for a narrow use case.

## Consequences
- `TrussDiagram.tsx` contains `Member`, `Node`, `PinSupport`, `RollerSupport`, `ForceArrow` subcomponents.
- `viewBox` is computed from `bounds` emitted by the backend; the frontend hardcodes no geometry constants.
- The backend emits engineering coordinates (y-up); the SVG transform flips y. This is the only place the flip occurs.
- Future problem types add their own renderer; `TrussDiagram` is not shared.

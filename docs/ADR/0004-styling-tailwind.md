# ADR 0004 — Styling: Tailwind CSS

**Status:** Accepted

## Decision
Use Tailwind CSS for all styling.

## Reason
Fast iteration without a bespoke design system. Utility classes keep styles co-located with components, and Tailwind's responsive utilities handle the tablet-breakpoint sidebar collapse requirement without custom CSS.

## Consequences
- No CSS modules or styled-components; utility classes only.
- `tailwind.config.ts` content paths must include all `src/**/*.{ts,tsx}`.

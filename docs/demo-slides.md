---
marp: true
theme: default
paginate: true
style: |
  section {
    font-family: 'Inter', 'Segoe UI', sans-serif;
    background: #ffffff;
    color: #1a1a2e;
  }
  section.title {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    color: #ffffff;
    text-align: center;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }
  section.title h1 { font-size: 2.6rem; margin-bottom: 0.5rem; }
  section.title p  { font-size: 1.1rem; opacity: 0.85; }
  h2 { color: #1d4ed8; border-bottom: 2px solid #dbeafe; padding-bottom: 0.3rem; }
  pre { background: #f0f4ff; border-left: 4px solid #1d4ed8; padding: 1rem; font-size: 0.75rem; }
  .highlight { background: #dbeafe; border-radius: 0.4rem; padding: 0.2rem 0.6rem; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { background: #1d4ed8; color: white; padding: 0.5rem 0.8rem; text-align: left; }
  td { padding: 0.4rem 0.8rem; border-bottom: 1px solid #e2e8f0; }
  tr:nth-child(even) td { background: #f8faff; }
---

<!-- _class: title -->

# Statics Platform

**Replacing MATLAB Desktop → Browser-based Statics Grader**

Koshik Kumaravel · Rushil · August 2026

---

## The Problem

Students today open a MATLAB desktop app to complete statics homework.

| Pain Point | Impact |
|---|---|
| Every student must install MATLAB | Setup barrier; license issues |
| Problems graded manually by TAs | Hours of TA time per assignment |
| No audit trail — who changed what? | Academic integrity concerns |
| Single-machine execution | No concurrent use in class settings |
| New problem types require MATLAB expertise | Slow to iterate |

**Goal:** Replace it with a web platform that scales to a full class, grades automatically, and gives you real-time visibility into student progress.

---

## What We Built in 4 Days

A fully interactive demo running in the browser — no MATLAB, no backend running.

```
Student opens URL → enters PID + name → sees 8 truss problems
                 → works through each → gets instant feedback
                 → submits → sees score breakdown
```

**Every route already intercepted by mock API** — the real backend slots in without changing a line of frontend code.

Tech: **React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · MSW**

---

## Student Flow — Live Demo

```
 /                      → Login card (PID + first/last name)
    ↓ POST /auth/student/session
 /assignment/:slug      → Workspace (sidebar + diagram + answer panel)
    ↓ GET  /assignments/:slug/problems/:index  (per problem)
    ↓ POST /assignments/:slug/problems/:index/check
    ↓ POST /assignments/:slug/submit
 /assignment/:slug/submitted  → Score screen (X/8 + per-problem table)
```

All 7 routes are intercepted in dev mode by **Mock Service Worker** using the same JSON fixtures the backend will use — contract stays in sync automatically.

---

## Architecture — Contract First

```
packages/contract/openapi.yaml     ← source of truth (edit here first)
         │
         ├── openapi-typescript → frontend/src/contract/index.ts  (TS types)
         └── fixtures/           ← shared by MSW (frontend) + pytest (backend)
```

Neither side ships until the contract is agreed. When Rushil implements the backend, the frontend switches from MSW to the real API by changing **one environment variable**.

```bash
VITE_API_BASE_URL=https://api.statics-platform.com  # production
# (omit for dev — MSW intercepts automatically)
```

---

## Extensible Problem Renderer

The platform is **not a truss tool** — it is a statics grader. Every problem type lives in a registry:

```ts
// frontend/src/problems/registry.ts
const registry: Record<string, ComponentType<{ geometry: unknown }>> = {
  truss: lazy(() => import('./truss/TrussDiagram')),
  // beam:  lazy(() => import('./beam/BeamDiagram')),   ← Phase 7
  // frame: lazy(() => import('./frame/FrameDiagram')), ← Phase 7
}
```

Adding **beam diagrams** for next semester requires:
1. One new directory under `problems/`
2. One new line in `registry.ts`

Zero changes to `WorkspaceLayout`, `AnswerPanel`, `ProgressList`, or any shared component.

---

## Truss Diagram — Hand-written SVG

Replaced MATLAB's `figPkg` figure export with React SVG components.

- **Coordinate system**: physics y-up → single `scale(1,-1)` transform; all labels counter-rotated
- **Renders**: nodes, members with force labels, pin/roller supports, external force arrows
- **Three fixture sizes** already wired: 3-node, 4-node, 6-node trusses
- Scales to any viewport — works on tablet in class

```
Render order (painter's algorithm):
  Members → Supports → Force arrows → Nodes (on top)
```

Answer fields are **generated from `answerSchema`** in the problem payload — the frontend never hardcodes field names or units.

---

## What's Left (Phases 2–8)

| Phase | Owner | Description |
|---|---|---|
| **2 — Golden fixtures** | Rushil | Extract correct answers from MATLAB runs |
| **3 — Problem engine** | Rushil | Python geometry/solver porting MATLAB code |
| **4 — Backend API** | Rushil | FastAPI + PostgreSQL, real grading endpoints |
| **5 — Frontend polish** | Koshik | Loading skeletons, error handling, autosave |
| **6 — Instructor dashboard** | Both | Roster, score drill-down, CSV export, override |
| **7 — Second problem type** | Both | Validates extensibility promise |
| **8 — Harden & deploy** | Both | HTTPS, rate limits, FERPA audit, load test |

**Demo today covers Phase 0 through Phase 1 (frontend side of Phase 5).**

---

## Thank You

**What you can do today:**
→ Open `localhost:5173` and walk through a full student submission

**Questions we'd love your input on:**
- What grading tolerance is acceptable for truss member forces?
- Should students see a running score or only see the total after submit?
- Is the 8-problem per assignment structure fixed, or configurable by section?

**Repo:** `github.com/koshster/matlab-migration`
**Contact:** kkumaravel@fuelcycle.com

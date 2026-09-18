# Statics Platform

A web replacement for a MATLAB truss-homework app. Students solve randomly-generated statics problems (truss analysis) in the browser; the backend grades submissions server-side. An instructor dashboard lets Prof. Marko view scores, replay student problems, and export grades.

## What's included

- **Student flow** — PID + name login, problem workspace with an interactive truss diagram, answer panel with autosave, and instant feedback
- **Instructor dashboard** — roster view, per-student drill-down, problem replay, CSV grade export, and score overrides
- **Problem engine** — Python port of the MATLAB truss generator (geometry, supports, loads, solver)
- **Backend** — FastAPI + PostgreSQL; all grading logic lives server-side; solutions are never sent to student routes
- **Frontend** — React 18 + TypeScript + Tailwind; MSW mocks let the frontend run without the backend during development

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [pnpm](https://pnpm.io/installation) (`npm install -g pnpm`)

## Getting started

```bash
# 1. Clone the repo
git clone <repo-url>
cd statics-platform

# 2. Start all services (Postgres, backend, frontend)
make dev

# 3. In a separate terminal, run migrations and seed initial data
make migrate
make seed
```

| Service  | URL                        |
| -------- | -------------------------- |
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

Health check: `curl localhost:8000/api/v1/health` should return `{"status":"ok"}`.

The seed script creates one course, one 8-problem truss assignment, and one instructor account.

## Common commands

```bash
make dev      # start everything (postgres + backend hot-reload + vite dev server)
make test     # run pytest (backend) + vitest (frontend)
make lint     # ruff + mypy --strict + eslint + tsc --noEmit
make format   # ruff format + prettier
make migrate  # apply Alembic migrations
make seed     # insert demo data
make clean    # tear down containers and volumes
```

## Environment variables

Docker Compose supplies sane defaults for local development — no `.env` file required. For production, set:

| Variable            | Default                          | Notes                     |
| ------------------- | -------------------------------- | ------------------------- |
| `POSTGRES_DB`       | `statics`                        |                           |
| `POSTGRES_USER`     | `statics`                        |                           |
| `POSTGRES_PASSWORD` | `secret`                         | Change in production      |
| `SECRET_KEY`        | `dev-secret-change-in-production`| Change in production      |
| `ENVIRONMENT`       | `development`                    |                           |

## Hosting

The app is split into three pieces that need to be deployed: the **backend** (FastAPI), the **frontend** (static files), and a **PostgreSQL 16** database. Both Dockerfiles already have a hardened `prod` target (non-root user, no hot-reload, 4 workers for the backend, nginx for the frontend).

### What you need

| Piece | Requirement |
| ----- | ----------- |
| PostgreSQL 16 | Managed database — e.g. Supabase, Railway, Render Postgres, AWS RDS |
| Backend | A service that can run a Docker container and expose port 8000 — e.g. Railway, Render, Fly.io, AWS ECS |
| Frontend | A static host or CDN — e.g. Cloudflare Pages, Vercel, Netlify, or the nginx prod image on the same platform as the backend |
| HTTPS | Required for the httpOnly JWT cookie to work; most platforms provide this automatically |

### Build the production images

```bash
# Backend
docker build --target prod -t statics-backend ./backend

# Frontend (set VITE_API_BASE_URL to your backend's public URL at build time)
docker build \
  --target prod \
  --build-arg VITE_API_BASE_URL=https://api.yourdomain.com \
  -t statics-frontend .
```

### Checklist before going live

1. **Secrets** — set `SECRET_KEY` (long random string) and `POSTGRES_PASSWORD` via your platform's secret manager; never commit them.
2. **Migrations** — run `alembic upgrade head` once against the production database before starting the backend.
3. **CORS** — add your frontend domain to the backend's allowed origins (configured in `backend/app/core/config.py`).
4. **HTTPS** — terminate TLS in front of the backend (reverse proxy or platform-managed certificate).
5. **FERPA** — student PID and name data must stay within your institution's approved infrastructure; verify your chosen provider qualifies.

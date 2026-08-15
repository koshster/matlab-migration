FROM node:22-slim AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# --- dev target: mounts source at runtime for hot reload ---
FROM base AS dev

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json ./frontend/
COPY packages/ ./packages/
RUN pnpm install --filter @statics/frontend...

WORKDIR /app/frontend

EXPOSE 5173
CMD ["pnpm", "dev"]

# --- prod target: static build ---
FROM dev AS build

COPY frontend/ ./frontend/
RUN pnpm --filter @statics/frontend build

FROM nginx:alpine AS prod
COPY --from=build /app/frontend/dist /usr/share/nginx/html
EXPOSE 80

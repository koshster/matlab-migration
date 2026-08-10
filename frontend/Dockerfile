FROM node:20-slim AS base

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app

# --- dev target: mounts source at runtime for hot reload ---
FROM base AS dev

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

EXPOSE 5173
CMD ["pnpm", "dev"]

# --- prod target: static build ---
FROM base AS build

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM nginx:alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

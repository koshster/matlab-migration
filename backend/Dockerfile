FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"


WORKDIR /app

RUN pip install uv

# --- dev target: mounts source at runtime for hot reload ---
FROM base AS dev

COPY pyproject.toml .
RUN uv sync --all-extras --no-install-project

COPY . .
RUN uv sync --all-extras

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- prod target: baked image, non-root ---
FROM base AS prod

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev


RUN chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

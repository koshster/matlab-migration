.PHONY: dev test lint format migrate seed clean

dev:
	docker compose up --build

test:
	docker compose run --rm backend pytest
	pnpm --filter frontend test run

lint:
	docker compose run --rm backend ruff check app/ tests/
	docker compose run --rm backend mypy --strict app/
	pnpm --filter frontend lint
	pnpm --filter frontend typecheck

format:
	docker compose run --rm backend ruff format app/ tests/
	pnpm --filter frontend format

migrate:
	docker compose run --rm backend alembic upgrade head

seed:
	docker compose run --rm backend python -m app.scripts.seed

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

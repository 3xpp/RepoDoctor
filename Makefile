.PHONY: install dev test test-e2e lint typecheck format build

install:
	uv sync

dev:
	uv run repo-doctor scan .

test:
	uv run pytest tests/unit

test-e2e:
	uv run pytest tests/e2e

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

format:
	uv run ruff format . && uv run ruff check . --fix

build:
	uv build

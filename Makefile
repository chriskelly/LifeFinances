all: test lint

test:
	uv run pytest

ruff-check:
	uv run ruff check .

ruff-format-check:
	uv run ruff format --check .

pyright:
	uv run pyright

lint: ruff-check ruff-format-check pyright

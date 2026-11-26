.PHONY: all test browser-checks coverage ruff-check ruff-format-check pyright lint

all: test lint

test:
	uv run pytest

browser-checks:
	uv run playwright install chromium
	uv run pytest browser_tests

coverage:
	uv run pytest --cov

ruff-check:
	uv run ruff check .

ruff-format-check:
	uv run ruff format --check .

pyright:
	uv run pyright

lint: ruff-check ruff-format-check pyright

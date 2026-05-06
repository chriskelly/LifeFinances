all: test lint

test:
	uv run --project backend pytest backend/tests && cd frontend && npm run test:run

ruff-check:
	uv run --project backend ruff check backend

ruff-format-check:
	uv run --project backend ruff format --check backend

pyright:
	uv run --project backend pyright -p backend/pyrightconfig.json

lint: ruff-check ruff-format-check pyright

coverage:
	uv run --project backend pytest backend/tests --cov=backend/app --cov-report=term-missing --cov-report=html

profile:
	uv run --project backend python -m cProfile -o backend/tests/profiling/results/gen_trials.prof backend/tests/profiling/gen_trials.py
	uv run --project backend snakeviz backend/tests/profiling/results/gen_trials.prof

# these will speed up builds, for docker compose >= 1.25
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1

# Detect if we're in a devcontainer or docker isn't available
DOCKER_COMPOSE := $(shell command -v docker-compose 2> /dev/null || command -v docker 2> /dev/null | xargs -I {} sh -c '{} compose version > /dev/null 2>&1 && echo "docker compose" || echo ""')
IN_DEVCONTAINER := $(shell [ -f /.dockerenv ] && [ -d .devcontainer ] && echo "true" || echo "")
COMPOSE_SERVICE ?= backend

# Use direct commands if docker compose is not available or we're in devcontainer
ifeq ($(DOCKER_COMPOSE),)
  USE_DIRECT := true
else ifeq ($(IN_DEVCONTAINER),true)
  USE_DIRECT := true
else
  USE_DIRECT := false
endif

all: down build up test lint

build:
ifeq ($(USE_DIRECT),true)
	@echo "Skipping build (running directly in devcontainer)"
else
	docker compose build
endif

up:
ifeq ($(USE_DIRECT),true)
	@echo "Skipping up (running directly in devcontainer)"
else
	docker compose up -d
endif

down:
ifeq ($(USE_DIRECT),true)
	@echo "Skipping down (running directly in devcontainer)"
else
	docker compose down --remove-orphans
endif

test: up
ifeq ($(USE_DIRECT),true)
	uv run --project backend pytest backend/tests
else
	docker compose run --rm --no-deps -e GITHUB_JOB=$(GITHUB_JOB) --entrypoint=pytest $(COMPOSE_SERVICE) tests
endif

ruff-check: build
ifeq ($(USE_DIRECT),true)
	uv run --project backend ruff check backend
else
	docker compose run --rm --no-deps --entrypoint=ruff $(COMPOSE_SERVICE) check .
endif

ruff-format-check: build
ifeq ($(USE_DIRECT),true)
	uv run --project backend ruff format --check backend
else
	docker compose run --rm --no-deps --entrypoint=ruff $(COMPOSE_SERVICE) format --check .
endif

pyright: build
ifeq ($(USE_DIRECT),true)
	uv run --project backend pyright -p backend/pyrightconfig.json
else
	docker compose run --rm --no-deps --entrypoint=pyright $(COMPOSE_SERVICE)
endif

lint: ruff-check ruff-format-check pyright

coverage:
ifeq ($(USE_DIRECT),true)
	uv run --project backend pytest backend/tests --cov=backend/app --cov-report=term-missing --cov-report=html
else
	docker compose run --rm --no-deps -e GITHUB_JOB=$(GITHUB_JOB) --entrypoint=pytest $(COMPOSE_SERVICE) tests --cov=app --cov-report=term-missing --cov-report=html
endif

profile:
	uv run --project backend python -m cProfile -o backend/tests/profiling/results/gen_trials.prof backend/tests/profiling/gen_trials.py
	uv run --project backend snakeviz backend/tests/profiling/results/gen_trials.prof
# Backend Agent Guide (Python / Flask)

This file applies to everything under `backend/`. Read [/AGENTS.md](../AGENTS.md) first for repo-wide policy and the documentation/commit conventions.

## Stack

- Python 3.10+ (`requires-python = ">=3.10"` in [pyproject.toml](pyproject.toml))
- Flask 3.1, Pydantic 2.4, NumPy 1.26, pandas 2.1, PyYAML 6, numpy-financial
- Tests: pytest 9, pytest-cov, pytest-flask, pytest-mock
- Tooling: uv (env + deps), ruff 0.14 (lint + format), pyright 1.1 (types), snakeviz (profile viewer)

Versions are pinned in [pyproject.toml](pyproject.toml). Don't drift from them in test code or examples.

## Commands

Run from the **repo root**, not from inside `backend/`. The Makefile and uv expect that.

| Action                  | Command                                                                       |
| ----------------------- | ----------------------------------------------------------------------------- |
| Run backend tests       | `uv run --project backend pytest backend/tests`                               |
| Lint (style)            | `uv run --project backend ruff check backend`                                 |
| Lint (formatting check) | `uv run --project backend ruff format --check backend`                        |
| Type check              | `uv run --project backend pyright -p backend/pyrightconfig.json`              |
| Format in place         | `uv run --project backend ruff format backend`                                |
| Auto-fix lint           | `uv run --project backend ruff check --fix backend`                           |
| Coverage report         | `make coverage`                                                               |
| Run app (dev)           | `uv run --project backend python backend/run.py` (or `python backend/run.py` in devcontainer) |
| Sync deps after edit    | `uv sync --project backend`                                                   |
| Profile simulator       | `make profile`                                                                |

`make test` and `make lint` (defined in the root [Makefile](../Makefile)) wrap these. Prefer the `make` form for parity with CI.

## Backend layout

```
backend/
├── app/
│   ├── __init__.py            # Flask factory: create_app(); mounts /api, redirects / → SPA
│   ├── routes/
│   │   ├── api.py             # /api blueprint
│   │   └── api_json.py
│   ├── models/
│   │   ├── config/            # Pydantic config models (User, Income, Spending, …)
│   │   ├── controllers/       # Allocation, Annuity, EconomicData, Pension, Spending, …
│   │   ├── financial/         # Interval, State, StateChange, Taxes
│   │   └── simulator.py       # core simulation engine
│   ├── data/
│   │   ├── constants.py / constants/
│   │   ├── historic_data/
│   │   └── variable_statistics.csv   # SOURCE OF TRUTH; do not regenerate casually
│   └── util.py
├── tests/                     # mirrors app/ layout
├── standalone_tools/          # *.ipynb tools NOT imported by app code (testing-exempt)
├── pyproject.toml
├── pyrightconfig.json
└── run.py
```

`backend/tests/` MUST mirror the `backend/app/` tree. A new module `backend/app/models/foo.py` gets tests at `backend/tests/models/test_foo.py`.

## Code style — Do / Don't

### Type hints on every public function/method

```python
def project_balance(*, user: User, year: int) -> Money: ...
```

NOT:

```python
def project_balance(user, year): ...
```

### Named arguments when there are 2+ args

Reason: positional ambiguity bites refactors and is hard to read in the simulator pipelines.

Do:

```python
controller = SpendingController(user=user, strategy=strategy)
result = simulate(user=user, trials=1000, seed=42)
```

Don't:

```python
controller = SpendingController(user, strategy)
result = simulate(user, 1000, 42)
```

A single obvious argument may be passed positionally (`len(items)`, `Path("x.yml")`).

### Object models over dicts

Use Pydantic models, dataclasses, `TypedDict`, or named classes. Plain `dict[str, Any]` should only appear at external API boundaries (incoming JSON, YAML loads) before being parsed into a typed model.

Do:

```python
from pydantic import BaseModel

class TrialResult(BaseModel):
    success: bool
    final_balance: float
    year: int
```

Don't:

```python
def run() -> dict:
    return {"success": True, "final_balance": 1234.56, "year": 2055}
```

### Docstrings on modules, classes, and public functions

Module-level docstrings on every file in `backend/app/`. Google or NumPy style on public classes and functions. Skip docstrings only on trivial private helpers where the name and signature say everything.

```python
"""Spending controllers: convert user spending strategies into per-year flows."""

class SpendingController:
    """Apply a `SpendingStrategy` to a user's projected timeline.

    Args:
        user: The user whose spending is being projected.
        strategy: The strategy that maps projected income to spending.
    """
```

### Errors must say something useful

User-facing code paths handle expected error conditions and surface meaningful messages. Critical errors are logged.

Don't swallow `Exception` blindly:

```python
try:
    ...
except Exception:
    pass
```

If a broad catch is genuinely needed (e.g. boundary handlers), comment why:

```python
try:
    ...
except Exception as exc:
    # API boundary: convert any failure into a 500 with a structured payload.
    logger.exception("Simulation failed")
    return jsonify(error=str(exc)), 500
```

### Avoid circular imports

Group code by feature/domain. If `app.models.controllers.X` needs `app.models.financial.Y`, that's fine; circular edges aren't. The Flask factory in [app/\_\_init\_\_.py](app/__init__.py) defers blueprint imports to dodge factory-time cycles — keep that pattern when adding new blueprints.

## API conventions

- All HTTP routes live under `/api` (mounted in [app/\_\_init\_\_.py](app/__init__.py)).
- Python identifiers: `snake_case`. URL paths: `kebab-case` (e.g. `/api/simulation/run`, not `/api/simulation_run`).
- Request and response bodies are JSON. Document new endpoints in the existing OpenAPI contract under `docs/features/react-flask-migration/Development/contracts/openapi.yaml`.
- Validate request bodies against Pydantic config models. Don't re-validate by hand once a typed model exists.
- Error responses MUST include an HTTP status code that matches the error class and a JSON body with at least an `error` (or equivalent) field. Validation errors MUST identify the offending field.
- Interactive endpoints SHOULD respond within ~2s under normal load. Long-running operations need progress indicators or async status endpoints.
- The backend reads/writes `./config.yml` against the **process working directory**. Always run from repo root. The fallback for `GET /api/config` when no file exists is `backend/tests/sample_configs/min_config_income.yml`; `PUT` always targets `./config.yml`.

## Testing — TDD is mandatory for application code

The simulator and Flask app are application code; tests come first.

### Cycle

1. Write a failing test that names the user-visible behavior.
2. Implement the minimum needed to make it pass.
3. Refactor with the test as your safety net.

### Structure

- pytest only.
- Mirror source layout under `backend/tests/`.
- Shared setup goes in `conftest.py` fixtures. New fixtures should be typed and reusable across the file/package they serve.
- Test names describe domain behavior, not implementation: `test_spending_controller_falls_back_to_floor_when_income_drops`, not `test_method_returns_value`.

### Quality bars

- **Independence**: tests must run in any order.
- **Explicit wiring**: when a test needs a `User`, `Controller`, or other collaborator, build it via a fixture or factory that takes the relevant inputs. Don't rely on hidden module-level globals.
- **Reusable fixtures over copy-paste**: if a complex scenario shows up in 3+ tests, factor it into a fixture or helper. Mirror production model shapes (e.g. typed `User` fixtures, dataclasses) instead of ad-hoc dicts.
- **No magic numbers**: derive expectations from shared sources (fixtures, canonical CSVs, domain objects). When the underlying data changes, tests should adapt mechanically.
- **Both success and failure paths**: every public function gets at least one happy-path and one failure/edge-case test.
- **Integration coverage**: API endpoints get integration tests asserting status code, response shape, and error handling. The simulator gets multi-scenario coverage.

### Speed budgets

- Unit test: < 1 second.
- Integration test: < 10 seconds.
- Whole suite: < 5 minutes.

### Coverage targets

- All new application code: ≥ 80% line coverage.
- Critical paths — simulator core, financial calculations, state transitions, controllers: ≥ 95% or equivalent confidence via focused integration tests.

### What's exempt from testing

The TDD/coverage rules apply to all *application* code. Standalone tools and notebooks are exempt **only if** they are:

- under `backend/standalone_tools/` (e.g. `disability_insurance_calculator.ipynb`, `tpaw_planner.ipynb`),
- not imported, executed, or referenced by anything in `backend/app/`,
- explicitly one-off / exploratory.

If a script or notebook becomes a dependency of the app (imported, executed at startup, fed by a route), it MUST get tests like everything else.

## Performance

- Single simulation trial target: < 100ms for standard configs.
- Profile with `make profile` (writes a `.prof` file and opens snakeviz). Review the profile before merging anything that touches the simulator hot path.
- Memory usage MUST be bounded; no unbounded `list.append` in trial loops.

## Backend-specific guardrails

- NEVER delete, regenerate, or manually edit `backend/app/data/variable_statistics.csv` or files under `backend/app/data/historic_data/` without explicit confirmation. They are statistical inputs, not derived outputs.
- NEVER add a runtime dependency by hand-editing `pyproject.toml`. Use `uv add <pkg> --project backend` so the lockfile stays consistent, then re-run `uv sync --project backend`.
- NEVER widen `except` handlers to silence flaky tests. Fix the test or the code.
- NEVER `print()` for logging in app code; use `logging` (the existing controllers and simulator follow this pattern).
- NEVER introduce a Flask blueprint without registering it in [app/\_\_init\_\_.py](app/__init__.py) inside `create_app()`.

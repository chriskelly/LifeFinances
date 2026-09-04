# Tools — Agent Guide

Marimo standalone apps live here. They consume shared packages; they are not the web UI.

## Run

From the repository root:

```bash
uv run marimo edit tools/disability_insurance.py
```

Optional: `uv run marimo run tools/disability_insurance.py` for view-only.

Working directory must be the repo root so `core.paths.default_db_path()` resolves `data/data.db`. Override with `LIFE_FINANCES_DB_PATH`.

## Rules

- Import `core` and `domain` only (plus `marimo` as the host). **Never** import `web` or `simulation`.
- Load plans with `PlanRepository.list` / `get_by_id` and `SettingsRepository.get`. **Never** `save`, `create`, `ensure_bootstrap`, or `get_or_create_default`.
- Coverage and other tool knobs live in gitignored `tools/<name>.local.toml` (committed `*.local.toml.example`). Do not add fields to `Plan` for a tool unless a later spec says so. Never commit `tools/*.local.toml`.

## Tests

Standalone Marimo apps are **not** imported by `packages/` and are exempt from pytest. `make test` must not execute notebooks. Keep `make` green for the rest of the repo.

## Adding a tool

1. Create `tools/<name>.py` as a Marimo app (`import marimo` + `app = marimo.App()` + `@app.cell`).
2. Follow the import and read-only DB rules above.
3. Document the run command in this file’s Run section.
4. If the tool has personal knobs, add `tools/<name>.local.toml.example` and load `tools/<name>.local.toml` (ignored by `tools/*.local.toml`).

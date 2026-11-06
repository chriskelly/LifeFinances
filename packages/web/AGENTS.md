# Web — Agent Guide

FastAPI + Jinja2 + HTMX + Pico.css split-pane UI for plan editing and simulation results.

## Prerequisites

Run from the **repository root**. Initialize the database before starting the dev server:

```bash
uv run python scripts/init_db.py
```

If `data/data.db` is missing, the app serves an error page with the same instruction.

## Dev server

```bash
uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The module exposes `app = create_app()` at the bottom of `web/app.py`. Same working-directory and `LIFE_FINANCES_DB_PATH` contract as root `AGENTS.md`.

## Rules

- Plan-editor, results, and section requests use the **`plan` query parameter** (`?plan={id}`); plan-management routes for an existing plan take the id in the path. There is no session or cookie state; unknown or missing plan ids return `404`.
- API keys live on `AppSettings` and are injected at the web boundary. **Never** store keys in plan JSON, plan export, or git.
- Web tests live in `packages/web/tests/`; use the package `client` fixture (layout: `docs/testing.md`).

## Reference

- Plan resolution, header menu, settings → `packages/web/docs/routes.md`
- Template layout, form DTOs, editor sections, HTMX → `packages/web/docs/templates.md`
- Results charts, simulation cache, Plotly → `packages/web/docs/charts.md`
- Explain JSON HTTP semantics → `packages/web/docs/json-api.md`
- Explain JSON field names → `packages/web/docs/json-payloads.md`
- Styling and palette → `packages/web/docs/styling.md`

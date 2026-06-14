# Web — Agent Guide

FastAPI + Jinja2 + HTMX split-pane UI for plan editing and simulation results.

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

Open `http://127.0.0.1:8000/`. The module exposes `app = create_app()` at the bottom of `web/app.py`.

Override the database path with `LIFE_FINANCES_DB_PATH` (see root `AGENTS.md`).

## Template layout conventions

- **Path and title constants** live in `web/routes.py` and `web/sections.py`. Templates reference them as Jinja globals (`{{ routes.HOME }}`, `{{ sections.HOUSEHOLD_TITLE }}`), registered in `create_app()` via `templates.env.globals`.
- **Form field names** live in `web/forms.py` as module-level constants (e.g. `forms.PERSON1_BIRTH_YEAR`) alongside per-section Pydantic form DTOs (`HouseholdForm`, `PortfolioForm`). HTML `name` attributes must use these constants — never hardcode field strings in templates.
- **Section-scoped forms:** each editor partial (`editor_household.html`, `editor_portfolio.html`) is a self-contained `<form>` that `PATCH`es its own route (`routes.PLAN_HOUSEHOLD`, `routes.PLAN_PORTFOLIO`). FastAPI binds flat `Form()` parameters to the matching DTO; the DTO's `apply_to(plan)` merges into the full `Plan` before `repo.save`.
- **Partials:** `index.html` includes both editor sections and the initial results stub. Section GET routes return individual partials for HTMX swaps if needed later.

## HTMX debounce pattern

Editor forms auto-save on change with a 750ms debounce:

```html
hx-patch="{{ routes.PLAN_HOUSEHOLD }}"
hx-trigger="change delay:750ms from:input,select"
hx-swap="none"
```

After a successful section `PATCH`, `index.html` listens for `htmx:afterRequest` and dispatches a `planUpdated` custom event on `document.body`. The results panel refreshes via:

```html
hx-get="{{ routes.RESULTS }}"
hx-trigger="planUpdated from:body"
hx-swap="innerHTML"
```

This decouples save (debounced per form) from results refresh (once per successful save).

## Tests

Web tests live in `packages/web/tests/`. Use the `client` fixture from package `conftest.py`; shared `db_path` / `repo` fixtures come from repo-root `conftest.py`.

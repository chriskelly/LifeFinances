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

## Active plan resolution

Every plan-scoped request uses the **`plan` query parameter** (`?plan={id}`). There is no session or cookie state.

- **`GET /`** without `plan` → `302` redirect to `/?plan={AppSettings.default_plan_id}` (user-marked default).
- **`GET /?plan=2`**, editor GETs, **`GET /results?plan=2`**, and section **`PATCH`** routes operate on that plan id.
- Unknown or missing plan id on a plan-scoped route → `404`.
- Empty DB bootstrap creates one plan and sets `default_plan_id`.

Route constants for plan management live in `web/routes.py` (`PLAN_CREATE`, `PLAN_DUPLICATE`, etc.). Switching plans is a normal link to `/?plan={id}` (full page reload).

### Header plan menu

`plan_menu.html` (included from `index.html`) exposes:

| Action | Route | Notes |
| ------ | ----- | ----- |
| Switch | `GET /?plan={id}` | Link per plan in the list |
| New | `POST /plans` | Blank `default_plan()`; redirect to new id |
| Duplicate | `POST /plans/{id}/duplicate` | Deep copy; redirect to new id |
| Rename | `POST /plans/{id}/rename` | `forms.PLAN_NAME`; redirect to same id |
| Set default | `POST /plans/{id}/set-default` | Updates `AppSettings.default_plan_id` |
| Delete | `POST /plans/{id}/delete` | Confirm in UI; optional `forms.RETURN_PLAN` keeps active plan when deleting a sibling; blocked when only one *loadable* plan remains; works by row id (no Plan JSON load); falls back to default when active was deleted |

### Settings (API keys)

`fred_api_key` and `eod_api_key` live on **`AppSettings`** (singleton DB row), edited via `editor_settings.html` / `AppSettingsForm`. They are injected at the web boundary into `run_simulation(..., allow_refresh=True)`. **Never** store keys in plan JSON, plan export, or git.

## Template layout conventions

- **Path and title constants** live in `web/routes.py` and `web/sections.py`. Templates reference them as Jinja globals (`{{ routes.HOME }}`, `{{ sections.HOUSEHOLD_TITLE }}`), registered in `create_app()` via `templates.env.globals`.
- **Form field names** live in `web/forms.py` as module-level constants (e.g. `forms.PERSON1_BIRTH_YEAR`) alongside per-section Pydantic form DTOs (`HouseholdForm`, `PortfolioForm`). HTML `name` attributes must use these constants — never hardcode field strings in templates.
- **Validation:** form DTOs are flat transport shapes only (no `Field` constraints). Domain validation lives on `core.models`; `apply_to()` constructs core models and Pydantic validates there. Do not duplicate `ge`/`le`/defaults on form DTOs.
- **Future (Phase 4c+):** when many editor sections exist, investigate generating flat form DTO fields from `core.models` via `create_model` + `model_fields` introspection so prefixes and constraints stay in sync automatically. See rebuild index Phase 4 notes.
- **Section-scoped forms:** each editor partial (`editor_household.html`, `editor_portfolio.html`, `editor_settings.html`) is a self-contained `<form>` that `PATCH`es its own route with **`?plan={{ plan_id }}`** on the HTMX URL so saves target the active plan. FastAPI binds flat `Form()` parameters to the matching DTO; the DTO's `apply_to(plan)` merges into the full `Plan` before `repo.save`.
- **Partials:** `index.html` includes both editor sections and the initial results stub. Section GET routes return individual partials for HTMX swaps if needed later.

### Results charts

`GET /results?plan={id}&chart={type}` renders `results.html`. Valid `chart` values are the constants in `web/charts.py` (`CHART_TYPES`); unknown values fall back to `DEFAULT_CHART` (`spending-total`). Figures are built server-side as Plotly JSON (`web.charts.build_figure`); plotly.js loads once from CDN in `base.html`. The shell calls `Plotly.react` on load and on every `htmx:afterSwap` targeting `#results-panel`, and mirrors the selected chart onto the panel's `hx-get` so `planUpdated` refreshes keep the selection.

## HTMX debounce pattern

Editor forms auto-save on change with a 750ms debounce:

```html
hx-patch="{{ routes.PLAN_HOUSEHOLD }}?plan={{ plan_id }}"
hx-trigger="input changed delay:750ms"
hx-swap="none"
```

After a successful section `PATCH`, `index.html` listens for `htmx:afterRequest` and dispatches a `planUpdated` custom event on `document.body`. The results panel refreshes via:

```html
hx-get="{{ routes.RESULTS }}?plan={{ plan_id }}"
hx-trigger="planUpdated from:body"
hx-swap="innerHTML"
```

This decouples save (debounced per form) from results refresh (once per successful save).

## Tests

Web tests live in `packages/web/tests/`. Use the `client` fixture from package `conftest.py`; shared `db_path` / `repo` fixtures come from repo-root `conftest.py`.

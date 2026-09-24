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
- **Form DTOs:** hand-written flat DTOs + shared helpers in `web/boundaries.py`. We rejected `create_model`-generated DTOs because list sections (jobs, sabbaticals, manual income) use indexed/nested field names (`jobs[0].sabbaticals[1].start_kind`) that FastAPI `Form()` cannot bind; those routes read `await request.form()` and parse with `boundaries.collect_indexed_rows` / `row_boundary`. Boundary controls use a `{prefix}_kind` selector plus `{prefix}_year/_month/_person/_age_years/_age_months`. "Now" stamps a `CalendarMonthBoundary` at save; "max age" persists a `PersonMaxAgeBoundary`.
- **Section-scoped forms:** each editor partial (`editor_household.html`, `editor_portfolio.html`, `editor_settings.html`) is a self-contained `<form>` that `PATCH`es its own route with **`?plan={{ plan_id }}`** on the HTMX URL so saves target the active plan. FastAPI binds flat `Form()` parameters to the matching DTO; the DTO's `apply_to(plan)` merges into the full `Plan` before `repo.save`.
- **Partials:** `index.html` includes both editor sections and the live `results.html` charts partial. Section GET routes return individual partials for HTMX swaps if needed later.

### Spending & simulation config editors

Four sections own these plan fields:

| Section | Owned fields |
| ------- | ------------ |
| Spending goals | `extra_essential_spending`, `extra_discretionary_spending`, `legacy_target` |
| Risk | `risk` (`RiskConfig`) |
| Market assumptions | `inflation`, `planning_returns` |
| Simulation details | `sampling`, `advanced` (percentiles) |

`editor_conditional.js` only controls visibility and `required`/`disabled` transport state for conditional fields (inflation mode, planning-return presets). It does not invent defaults or write plan fields.

### Results charts

`GET /results?plan={id}&chart={type}` renders `results.html`. Valid `chart` values are the constants in `web/charts.py` (`CHART_TYPES`); unknown values fall back to `DEFAULT_CHART` (`spending-total`). Home and results both go through `web.simulation_cache.get_or_run_simulation` (process-local LRU on `app.state`, keyed by plan id + plan JSON hash excluding `name` + API keys + calendar date) so chart switches reuse the same `SimulationResult` until the plan economics, settings keys, or day change. Cache hits skip `allow_refresh` until the next miss — mid-day market-data updates are invisible until then. The cache is single-process and not thread-safe (fine for typical single-worker local use). Every `SimulationResult` carries a required `resolved_assumptions` snapshot (exact inflation/returns/volatility values plus source labels and observation dates used by that run). Charts and the Market assumptions resolved-assumptions summary share that one cached result: home and direct Market assumptions GET render `#resolved-assumptions-summary` from it; `/results` refreshes the same container via HTMX OOB (`hx-swap-oob="innerHTML"`). If the simulation raises, the results panel shows a generic `Simulation failed…` alert (exception is logged server-side with stack trace; raw exception text is not shown), keeps a hidden `#chart-select` so `planUpdated` can preserve the chart query, omits the Plotly mount (`#chart-config` / `#results-chart`), and replaces the resolved summary with **Unavailable for current settings** (no stale numeric values). Figures are built server-side as Plotly JSON (`web.charts.build_figure`); band charts with ≥2 percentiles include a translucent fill between the outer percentile rows. Figure JSON escapes `<` before `| safe` injection into the config script tag. plotly.js loads once from CDN in `base.html`. The shell calls `Plotly.react` on load and on every `htmx:afterSettle` targeting `#results-panel`. The panel’s `hx-vals` reads `#chart-select` at request time so `planUpdated` refreshes keep the selection.

Chart figures use `hovermode="x unified"` and `legend.traceorder="reversed"` so unified hover lists all series with the lowest percentile last. Wealth-composition traces set `hoveron="points"` because unified hover does not reliably hit filled areas.

**Gotcha:** render charts on `htmx:afterSettle`, not `afterSwap`. Settle re-applies server attributes to id-matched elements and strips Plotly's `js-plotly-plot` class, which breaks absolute SVG positioning and pushes tooltips off-screen. Always re-render after settle for HTMX-swapped Plotly divs.

**Gotcha:** `#results-chart` has a CSS `min-height` (`static/style.css`) matching Plotly's default figure height. Without it the empty chart div collapses during the HTMX swap (before `Plotly.react` runs on settle), so the summary line jumps up and back down — a flicker on every chart change. Keep the `min-height` in sync if you set an explicit figure height in `build_figure`.

## Explain JSON routes

Read-only GET handlers in `web/explain_routes.py` (registered from `create_app()`). Path constants in `web/routes.py`:

| Constant | Path |
| -------- | ---- |
| `API_PLANS` | `/api/plans` |
| `API_PLAN` | `/api/plan` |
| `API_RESULT_SUMMARY` | `/api/result/summary` |
| `API_RESULT_DIAGNOSTICS` | `/api/result/diagnostics` |
| `API_RESULT_SERIES` | `/api/result/series` |

Each plan-scoped route accepts exactly one of query params `plan_id` or `name` (not both, not neither). Resolution and simulation reuse `web.simulation_cache.get_or_run_simulation` — the same process-local cache as Home and Results — via `web.explain.load_cached_result`. Do not spawn a separate simulation process for these routes.

Unloadable plan JSON returns JSON `422` with code `plan_unloadable` and a `message` (see `web.explain.resolve_plan`). That path intentionally does not use `require_plan`, which returns JSON `404` `{"detail": "Plan not found"}` and drops the validation message.

On `/api/result/series`, Monte Carlo spending and allocation series are percentile-major; `wealth_job`, `wealth_social_security`, `wealth_pension`, and `wealth_manual` are single vectors (no percentile axis — sending `percentile` yields `percentile_not_applicable`). Agent-facing usage is documented in root `.agents/skills/explain-results/SKILL.md`.

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
hx-vals="js:{chart: document.getElementById('chart-select')?.value}"
hx-trigger="planUpdated from:body"
hx-swap="innerHTML"
```

This decouples save (debounced per form) from results refresh (once per successful save). The panel reads the current chart from `#chart-select` via `hx-vals` so the selection survives the refresh.

## Styling and color palette

- Pico.css **2.1.1** fluid classless, pinned in `web.theme.PICO_STYLESHEET_HREF`. Load Pico, then `theme.pico_root_css()`, then `static/style.css`.
- `<html data-theme="light">` is required in v1 so OS dark mode cannot restyle the shell while Plotly stays on its default light look.
- **Retint UI** by editing constants in `web/theme.py` only. Do not add `--color-*` tokens. Do not put hex in templates or `style.css`.
- **Charts** use stock Plotly series colors. The percentile band fill (`BAND_FILLCOLOR` in `web/charts.py`) is the only explicit chart color we set; do not wire chart colors through `theme.py`.
- **Density** (overall size): edit `FONT_SIZE`, `LINE_HEIGHT`, `SPACING`, `FORM_SPACING_VERTICAL`, and `FORM_SPACING_HORIZONTAL` in `theme.py`. Shell gaps in `static/style.css` (layout/`editor-pane` padding) are separate if the page still feels roomy.
- Live emitted Pico roles: surfaces, primary family, invalid/del, plus density tokens above. To add secondary/contrast, copy names from https://picocss.com/docs/css-variables into `PICO_LIGHT` — do not comment-dump Pico's full theme.
- Custom CSS is for split-pane shell, plan-menu positioning, Plotly `#results-chart` min-height, HTMX error-banner layout, and JS-driven show/hide. Prefer stock Pico for forms.
- If Pico makes plan-menu × or boundary rows unusable: try a structural HTML tweak first; then **one** named hatch (`.compact-controls`) that only changes spacing and still uses `--pico-*` for color. No ad-hoc per-widget override pile-up.

## Tests

Web tests live in `packages/web/tests/`. Use the `client` fixture from package `conftest.py`; shared `db_path` / `repo` fixtures come from repo-root `conftest.py`.

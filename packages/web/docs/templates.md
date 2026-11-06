# Web templates and forms

Scope: template layout, form DTOs, editor sections, and the HTMX save pattern.
Read before changing a template, a form DTO, or an editor partial.

## Template layout conventions

- **Path and title constants** live in `../web/routes.py` and `../web/sections.py`. Templates reference them as Jinja globals (`{{ routes.HOME }}`, `{{ sections.HOUSEHOLD_TITLE }}`), registered in `create_app()` via `templates.env.globals`.
- **Form field names** live in `../web/forms.py` as module-level constants (e.g. `forms.PERSON1_BIRTH_YEAR`) alongside per-section Pydantic form DTOs (`HouseholdForm`, `PortfolioForm`). HTML `name` attributes must use these constants — never hardcode field strings in templates.
- **Validation:** form DTOs are flat transport shapes only (no `Field` constraints). Domain validation lives on `core.models`; `apply_to()` constructs core models and Pydantic validates there. Do not duplicate `ge`/`le`/defaults on form DTOs.
- **Form DTOs:** hand-written flat DTOs + shared helpers in `../web/boundaries.py`. We rejected `create_model`-generated DTOs because list sections (jobs, sabbaticals, manual income) use indexed/nested field names (`jobs[0].sabbaticals[1].start_kind`) that FastAPI `Form()` cannot bind; those routes read `await request.form()` and parse with `boundaries.collect_indexed_rows` / `row_boundary`. Boundary controls use a `{prefix}_kind` selector plus `{prefix}_year/_month/_person/_age_years/_age_months`. "Now" stamps a `CalendarMonthBoundary` at save; "max age" persists a `PersonMaxAgeBoundary`.
- **Section-scoped forms:** each editor partial (`../web/templates/editor_household.html`, `../web/templates/editor_portfolio.html`, `../web/templates/editor_settings.html`) is a self-contained `<form>` that `PATCH`es its own route with **`?plan={{ plan_id }}`** on the HTMX URL so saves target the active plan. FastAPI binds flat `Form()` parameters to the matching DTO; the DTO's `apply_to(plan)` merges into the full `Plan` before `repo.save`.
- **Partials:** `../web/templates/index.html` includes both editor sections and the live `../web/templates/results.html` charts partial. Section GET routes return individual partials for HTMX swaps if needed later.

## Spending & simulation config editors

Four sections own these plan fields:

| Section | Owned fields |
| ------- | ------------ |
| Spending goals | `extra_essential_spending`, `extra_discretionary_spending`, `legacy_target` |
| Risk | `risk` (`RiskConfig`) |
| Market assumptions | `inflation`, `planning_returns` |
| Simulation details | `sampling`, `advanced` (percentiles) |

`editor_conditional.js` only controls visibility and `required`/`disabled`
transport state for conditional fields (inflation mode, planning-return
presets). It does not invent defaults or write plan fields.

## HTMX debounce pattern

Editor forms auto-save on change with a 750ms debounce:

```html
hx-patch="{{ routes.PLAN_HOUSEHOLD }}?plan={{ plan_id }}"
hx-trigger="input changed delay:750ms"
hx-swap="none"
```

After a successful section `PATCH`, `../web/templates/index.html` listens for `htmx:afterRequest`
and dispatches a `planUpdated` custom event on `document.body`. The results
panel refreshes via:

```html
hx-get="{{ routes.RESULTS }}?plan={{ plan_id }}"
hx-vals="js:{chart: document.getElementById('chart-select')?.value}"
hx-trigger="planUpdated from:body"
hx-swap="innerHTML"
```

This decouples save (debounced per form) from results refresh (once per
successful save). The panel reads the current chart from `#chart-select` via
`hx-vals` so the selection survives the refresh.

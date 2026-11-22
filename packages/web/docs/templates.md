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

## Editor disclosures and pane rail

Each editor partial root is a native `<details class="editor-section" id="editor-...">`
with a `<summary class="editor-section-summary"><h2>...</h2></summary>`.
All sections start collapsed; multiple may be open. Section bodies stay direct
children of the `<details>`; CSS supplies the card padding and a negative-margin
summary so the whole header row is clickable. Nested advanced disclosures use
`class="editor-subsection"`.

### Collapsible list rows

Repeated items in Jobs, Spending goals, and Manual income are native
`<details class="row ...">` elements whose `<summary class="row-summary">`
contains one `<span data-summary-label>`, with the controls in a `.row-fields`
body. Existing rows start collapsed; a row added with `data-add-row` opens and
focuses its label, or its first visible field for a sabbatical. The `.row`
class stays on the outer element because `editor_lists.js` discovers, removes,
and reindexes rows by that class.

Label inputs carry `data-summary-source`; `editor_lists.js` copies the trimmed
value into the row's `[data-summary-label]`, falling back to the row's
`data-empty-label`. Rows deliberately show labels only; amount and date
previews are not rendered. Row open state is not persisted, so a reload
collapses every row. When a new row's first save succeeds,
`editor_lists.js` adds its `existing_index` hidden input inside `.row-fields`
so it never precedes `<summary>`.

Sabbaticals are `.row` details nested inside an open job's `.row-fields`; the
nested `.rows` is indented and bordered. Other row classes are `job-row` and
`stream-row`.

The Social Security upload response always carries `open` (success or error);
Market assumptions carries it when `simulation_error` is set. The Social
Security section GET and the initial page include stay collapsed. The inline
script at the top of the home body applies `editor-hidden` before `.layout`
paints; if localStorage is unavailable or its value is not the expected object,
the editor stays visible and the toggle still works for the session.

`index.html` places a 1.5rem `.pane-rail` as the middle track of `.layout`,
between the editor and results. Its `#toggle-editor` button toggles
`editor-hidden` on `<html>`, which hides `.editor-pane` and changes the grid to
`rail | results`. The button comes before the editor in DOM order so keyboard
users reach it before the section summaries. Pane visibility persists in
localStorage under `lifeFinances.panes` as `{"editorHidden": true|false}`;
section open state is not persisted. After a toggle, call
`Plotly.Plots.resize` because Plotly's responsive config listens to window
resize only; skip a `#results-chart` that is not yet a `js-plotly-plot`. The
future chat pane adds a mirrored rail on the right; editor section markup does
not change.

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

Any successful form clears `#form-error` in the same `htmx:afterRequest`
listener; only forms whose `hx-patch` starts with `PLAN_PREFIX` dispatch
`planUpdated`.

## Results summary

`../web/templates/results.html` wraps `../web/templates/_spending_summary.html`
in `#spending-summary`; home includes `results.html`, so both surfaces share the
partial. It has two columns: the level metrics (initial, lowest-percentile year,
median final year) and the threshold odds (the form, then the share of runs and
months below it). A blank threshold shows the input plus a muted prompt.

Labels and tooltip copy come from `../web/spending_summary.py` constants, so the
screen and the explain JSON share one source. Each label is a
`tabindex="0"` trigger for a CSS bubble (`.metric-help-bubble`) revealed on
`:hover` and `:focus-visible`, so it works without a mouse; the bubble is
anchored below the label, not over the `?` marker.

The form `hx-post`s `POST /results/summary-threshold?plan={id}` and swaps the
partial into `#spending-summary` (innerHTML). The route returns the partial only
and deliberately lives outside `PLAN_PREFIX`, so the shell does not dispatch
`planUpdated` and the chart is not re-rendered for a display-only change. A
blank field clears the stored threshold; invalid or negative input returns
`422` with the shared error text.

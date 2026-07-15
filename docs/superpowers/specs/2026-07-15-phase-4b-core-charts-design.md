# Phase 4b — Web: Core Charts Design

**Date:** 2026-07-15  
**Status:** Approved

**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)  
**Builds on:** [Phase 3d results data layer](./2026-07-10-phase-3d-simulation-results-design.md); [Phase 4a plan shell](./2026-07-14-phase-4a-plan-shell-design.md)  
**Phase plan:** [`2026-06-12-phase-4b-core-charts.md`](../plans/2026-06-12-phase-4b-core-charts.md)  
**Index:** Phase 4b in [2026-06-12-rebuild-index.md](../plans/2026-06-12-rebuild-index.md)

---

## 1. Goal & scope

Replace `results_stub.html` with **Plotly charts** in the results panel, driven by the existing percentile-major `SimulationResult`, plus a **chart-type selector** that survives HTMX debounced refreshes.

### In scope

- Plotly.js CDN once in the shell; server builds figure JSON; `Plotly.react` after load / HTMX swap
- Chart builders in `packages/web` (`web/charts.py` or equivalent)
- `GET /results?plan={id}&chart={type}`
- Core chart types:
  - `portfolio`
  - `spending-total`
  - `asset-allocation-savings-portfolio`
  - `wealth-composition-low` / `wealth-composition-mid` / `wealth-composition-high`
- Selector UI + preserve `chart` on `#results-panel` `hx-get` across `planUpdated`
- Tests for figure builders and results route/chart fallback
- Index / `web/AGENTS.md` corrections for inaccurate 4b chart naming

### Out of scope

- `withdrawal` chart (would duplicate `spending-total`; withdrawal-*rate* series not planned)
- tpaw-style `spending-total-funding-sources-*` (spending breakdown by income streams — different from wealth composition; needs data we do not expose that way)
- Per-stream essential/discretionary charts, `spending-general`, total-portfolio allocation (4e)
- Income / spending / sim-config editors (4c / 4d)
- Changing `SimulationResult` or simulation package chart APIs
- Browser E2E / visual regression

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Plotly embed** (not Altair / custom SVG) | Interactive hover/zoom; fits financial percentile bands |
| 2 | **Full core set** in this PR (not thin-only) | Match a corrected 4b deliverable in one merge |
| 3 | **`?chart=` query param** (not client-only / cookies) | Least complex with HTMX `innerHTML` swaps; mirrors `?plan=` |
| 4 | **CDN once + JSON config + `Plotly.react`** | Avoid re-shipping plotly.js on every debounce; reliable under swaps |
| 5 | **Web-owned figure builders** (Approach 1) | One consumer today; `simulation` stays chart-agnostic |
| 6 | **Omit `withdrawal`** | Duplicate of `spending-total`; no withdrawal-rate series planned |
| 7 | **`wealth-composition-*` instead of tpaw funding-sources** | Index conflated two charts; 3d ships deterministic wealth NPV + percentile savings |
| 8 | **Defer true spending funding-sources** | tpaw’s chart breaks down spending vs income streams; not our wealth stack |
| 9 | **Commit spec with plan** | User: do not commit design until implementation plan is approved |

### Correction vs rebuild index (pre-4b wording)

The index listed `spending-total-funding-sources-{low,mid,high}` as “wealth composition + savings allocation.” That is inaccurate:

- **Phase 3d `wealth_*` fields** are deterministic `(months,)` NPV bands — no per-percentile income variants. Only `balance_start[p, :]` varies by percentile.
- **tpaw `spending-total-funding-sources-*`** is a *spending* breakdown (selected percentile of `withdrawals.total` plus scheduled income-stream parts), not the wealth NPV stack.

4b ships **wealth composition** (savings at low/mid/high + deterministic income NPV layers). tpaw-style spending funding-sources stays deferred (4e or later if desired).

---

## 3. Architecture

```
Editor PATCH → planUpdated
       ↓
GET /results?plan={id}&chart={type}
       ↓
run_simulation(plan) → SimulationResult
       ↓
web.charts.build_figure(result, chart_type) → Plotly figure dict
       ↓
results.html: selector + #results-chart + JSON config
       ↓
shell JS: Plotly.react after first paint / htmx:afterSwap on #results-panel
```

| Piece | Owns |
| ----- | ---- |
| `simulation` | Unchanged public `SimulationResult` (no chart APIs) |
| `web/charts.py` | Chart-type constants, resolve/fallback, series → Plotly figure JSON |
| `GET /results` | Resolve plan + `chart`; render `results.html` |
| Shell (`base` / `index`) | Plotly.js CDN once; init / re-init helper |
| Templates | Replace `results_stub.html` with `results.html` |

**Package deps:** `web` → `simulation`, `core` (unchanged direction). Add `plotly` to the web package via `uv add`.

---

## 4. Chart types & series mapping

**Default:** `spending-total` (tpaw default). Missing or invalid `chart` → fall back to default (never blank the panel).

| `chart` | Y series | Style |
| ------- | -------- | ----- |
| `portfolio` | `balance_start` rows for each `result.percentiles` | One line per percentile; if ≥2 percentiles, also a translucent band from lowest to highest |
| `spending-total` | `withdrawals_total` percentile rows | Same |
| `asset-allocation-savings-portfolio` | `savings_stock_allocation` (display as %) | Same |
| `wealth-composition-low` | Stacked: `balance_start[p_low]` + `wealth_job` + `wealth_social_security` + `wealth_pension` + `wealth_manual` | Stacked area |
| `wealth-composition-mid` | Same with `p_mid` | Stacked area |
| `wealth-composition-high` | Same with `p_high` | Stacked area |

**X-axis:** month indices `0 … horizon_months-1`, labeled from `result.start_month` `(year, month)`.

**Percentile indices for wealth composition:** when `len(percentiles) == 3`, map low/mid/high → indices `0`, `1`, `2`. Otherwise map to `0`, `len // 2`, `-1`. Selector labels should show the actual percentile numbers (e.g. “Wealth · 5th”) when available.

**Shared chrome:** chart `<select>` (or equivalent), `ran_at`, `num_runs_insufficient` / `num_runs`. Drop the stub disclaimer.

**Explicitly not in 4b:** `withdrawal`; tpaw `spending-total-funding-sources-*`.

---

## 5. Routing, selector & Plotly re-init

**URL:** `GET /results?plan={id}&chart={type}` with types listed in §4.

**`#results-panel`:** keep `hx-swap="innerHTML"`. Home’s first paint and the panel’s initial `hx-get` both use the default chart (`spending-total`). When the user changes chart, HTMX re-fetches `/results` with the new `chart` and JS (or HTMX hooks) updates `#results-panel`’s `hx-get` so the next `planUpdated` refresh keeps the selection. Preferred mechanism: update the panel’s `hx-get` attribute on chart change (do not rely on state that only lives inside swapped innerHTML).

**Selector:** one control listing conceptual charts; wealth composition as three explicit `chart` values (no extra client-only percentile state).

**Plotly delivery:**

1. Load plotly.js once from CDN in `base.html`.
2. Partial returns empty `#results-chart` plus JSON config (e.g. `<script type="application/json" id="chart-config">`).
3. On first load and on `htmx:afterSwap` targeting `#results-panel`, call `Plotly.react('results-chart', data, layout, config)`.
4. Server uses the `plotly` Python package only to build the figure dict (`to_plotly_json()` or equivalent).

---

## 6. Error handling & edge cases

| Case | Behavior |
| ---- | -------- |
| Missing / invalid `chart` | Fall back to `spending-total` |
| Unknown `plan` | Unchanged `404` |
| Simulation failure | Message in results panel; no empty Plotly mount pretending success |
| Plotly.js not yet loaded | Defer first `Plotly.react` until CDN `onload` / readiness check |

Editor PATCH / debounce behavior unchanged.

---

## 7. Testing

**`web/charts` (unit)**

- Each chart type yields a figure with expected trace structure (e.g. wealth-composition has savings + four income layers; band charts have one series per percentile).
- Shared fixture `SimulationResult`; bind values once — no fragile duplicated literals.
- Invalid type resolution falls back to default.

**Web routes**

- `/results?plan=&chart=` returns 200; selected chart reflected in markup.
- Invalid `chart` falls back; panel markup / `hx-get` carries the resolved chart for refresh.
- Update existing stub-oriented results tests.

TestClient + fixtures only; no browser E2E; no network. Figure build must not require CDN.

`make` must pass.

---

## 8. Package boundaries

```
web  →  simulation (run_simulation, SimulationResult)
     →  core (plan load via existing deps)
     →  plotly (figure JSON only)
```

`tools` / `simulation` never import `web`. No new simulation chart helpers in 4b.

---

## 9. Documentation updates (same PR)

- Rebuild index Phase 4b deliverable / exit criteria: drop `withdrawal` and false funding-sources wording; list §4 chart types.
- Note deferred: tpaw-style spending funding-sources / per-stream charts → 4e (or later).
- `web/AGENTS.md`: brief note on `?chart=`, Plotly CDN, and `Plotly.react` after HTMX swap.

---

## 10. Exit criteria

- [x] Results panel renders Plotly charts for portfolio, spending-total, savings allocation, and wealth-composition (low/mid/high)
- [x] Chart selector switches via `?chart=`; selection survives `planUpdated` refresh
- [x] X-axis uses `SimulationResult.start_month` + horizon
- [x] Percentile bands use `result.percentiles` (default `[5, 50, 95]`)
- [x] Rebuild index / AGENTS wording corrected for wealth-composition vs funding-sources
- [x] `make` passes; debounced results refresh still works

---

## 11. Implementation notes for the phase plan

- Prefer a small `ChartType` / constant set + `resolve_chart_type(raw: str | None) -> str` in `web/charts.py`
- Keep figure builders pure functions of `SimulationResult` + chart type (easy unit tests)
- Do not expand into 4c/4d editors or 4e per-stream charts in this PR
- Spec commit deferred until the implementation plan is approved (per brainstorming session)
)

# Phase 4d — Web: Editor — Spending & Simulation Config Design

**Date:** 2026-08-21  
**Status:** Approved

**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)  
**Builds on:** Phase 3a–3d simulation configuration and results; [Phase 4a plan shell](./2026-07-14-phase-4a-plan-shell-design.md); [Phase 4c household and income editor](./2026-07-19-phase-4c-editor-income-design.md)  
**Phase plan:** [`2026-06-12-phase-4d-editor-sim-config.md`](../plans/2026-06-12-phase-4d-editor-sim-config.md) *(to write)*  
**Index:** Phase 4d in [2026-06-12-rebuild-index.md](../plans/2026-06-12-rebuild-index.md)

---

## 1. Goal & scope

Make the spending side and all persisted simulation controls editable from the split-pane web editor. Organize controls around user decisions, use progressive disclosure for technical settings, and show the exact market assumptions used by the current simulation.

### In scope

- Essential and discretionary `TimedStream` list editors
- Correct simulation handling of each spending stream's real/nominal basis
- Scalar `legacy_target`
- `RiskConfig`
- Suggested/manual `InflationConfig`
- Full seven-option `PlanningReturnsConfig` preset menu with conditional fields
- `SamplingConfig`
- Arbitrary user-configurable `AdvancedConfig.percentiles`
- A simulation-owned resolved-assumptions snapshot, including values, source types, and observation dates where applicable
- Automatic refresh of the resolved summary from the same cached run that refreshes the charts

### Out of scope

- Base spending input; base/general spending remains a simulation output
- Spending floor or ceiling
- Rich tpaw legacy sources; Phase 4d exposes only the existing scalar target
- Historical sequential sampling; the engine remains Monte Carlo block bootstrap
- Per-run bootstrapped inflation ([#186](https://github.com/chriskelly/LifeFinances/issues/186))
- Stable IDs for `TimedStream`; Phase 4e must resolve stream identity before adding per-stream chart URLs
- Extended spending charts (Phase 4e)
- New market-data acquisition; existing cache, live-refresh, and vendored-fallback paths remain authoritative

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Progressive disclosure** | Keep common financial decisions visible without making the editor a wall of technical fields |
| 2 | **Four user-facing sections:** Spending goals, Risk, Market assumptions, Simulation details | Organizes by user intent while preserving section-scoped forms and saves |
| 3 | **Persisted spending-stream IDs deferred to 4e** | The user chose not to expand 4d's core-model scope; 4e must not silently use unstable list positions without revisiting identity |
| 4 | **Risk tolerance and spending tilt visible; remaining risk fields collapsed** | Exposes normal controls while retaining full `RiskConfig` editability |
| 5 | **Arbitrary percentile list** | Matches `AdvancedConfig`; wealth charts continue to map first/middle/last |
| 6 | **Expose all sampling fields under collapsed Simulation details** | Supports reproducibility and performance tuning without cluttering the main editor |
| 7 | **Show resolved values and data dates; refresh automatically** | Users should see the assumptions the run actually used, not only the selected preset names |
| 8 | **Simulation-owned resolved snapshot** | One authoritative resolution path; no duplicate market math or resolver calls in `web` |
| 9 | **Scalar legacy target only** | Matches the current model and Phase 4d index scope |
| 10 | **Section-scoped full replacement** | Reuses Phase 4c's proven HTMX, form, list, and error patterns |
| 11 | **Honor `TimedStream.is_nominal` per spending stream** | The editor exposes this existing contract, so simulation must not continue deflating real streams as though every stream were nominal |

---

## 3. Editor architecture

Phase 4d adds four stacked sections to the existing left editor pane:

1. **Spending goals**
2. **Risk**
3. **Market assumptions**
4. **Simulation details** (collapsed by default)

Each section owns one form and one plan-scoped PATCH route. Its transport object merges only the fields owned by that section before saving the complete `Plan`.

| Section | Owned `Plan` fields |
| ------- | ------------------- |
| Spending goals | `extra_essential_spending`, `extra_discretionary_spending`, `legacy_target` |
| Risk | `risk` |
| Market assumptions | `inflation`, `planning_returns` |
| Simulation details | `sampling`, `advanced` |

The design follows existing web boundaries:

- Paths and titles live in `web.routes` and `web.sections`.
- Field-name constants and hand-written transport DTOs live in `web.forms`.
- Domain constraints remain in `core.models`.
- List forms read `request.form()` and use the existing indexed-row and boundary helpers.
- Successful PATCH requests use `hx-swap="none"` and trigger the existing `planUpdated` event.
- Each apply operation uses `model_copy(update=...)` and preserves unrelated plan fields.

Collapsing a section or advanced group is presentational only. Hidden fields retain their values; opening or closing a disclosure does not itself save.

---

## 4. Spending goals

### 4.1 Timed spending lists

Essential and discretionary spending are separate lists in one section. Each row edits the full existing `TimedStream` shape:

- label
- monthly amount
- nominal/real basis
- annual growth rate
- start boundary
- end boundary

The controls reuse the Phase 4c manual-income patterns:

- full-list replacement, not row-level endpoints
- distinct indexed prefixes for essential and discretionary rows
- shared boundary partial
- Add clones a blank client-side row
- Remove deletes the row after confirmation and dispatches one form change
- sparse wire indexes are accepted and sorted numerically
- existing-item matching preserves exact cents after display formatting and deletion

Starts support Now, calendar month, and person age. Ends support calendar month, person age, person max age, and plan horizon. A max-age start is not offered because a recurring spending stream beginning at the person's terminal month has no useful normal case.

New rows do not save until their required fields are complete, matching the Phase 4c list behavior.

The simulation must honor each row's existing basis contract:

- real (`is_nominal=False`): `monthly_amount` and growth are in today's dollars; do not divide the projected series by inflation;
- nominal (`is_nominal=True`): divide the projected nominal series by the inflation deflator to obtain real engine inputs.

The current preprocessing path sums a category before dividing the entire total by the deflator, which incorrectly erodes real streams. Phase 4d replaces that with per-stream conversion before summation. This is required for the newly exposed basis control to be truthful and also supports mixed real and nominal streams in one category.

### 4.2 Legacy target

`legacy_target` is a non-negative currency field in the same section.

The help text must state:

> Target at the plan horizon, in today's dollars.

This distinction matters because the engine treats `legacy_target` as already real and does not inflation-adjust it before discounting. Phase 4d does not add external legacy sources or a remainder calculator.

---

## 5. Risk

The always-visible controls are:

- `risk_tolerance_at_20`
- `additional_annual_spending_tilt`

Risk tolerance uses the existing tpaw-compatible 25-point scale, from conservative to aggressive. UI labels and range values derive from the core risk constants; tests do not copy them.

An **Advanced risk settings** disclosure contains:

- `delta_at_max_age`
- `legacy_delta_from_at_20`
- `time_preference`

Percent-like values use the existing percent parser and formatter. The form constructs a complete `RiskConfig`; the core model remains the validation authority.

---

## 6. Market assumptions

### 6.1 Inflation

The mode selector offers:

- Suggested
- Manual

Manual mode reveals a required annual-rate input. When a plan has no prior manual value, changing to Manual reveals the empty required field but does not submit an invalid intermediate form. The next valid input saves both mode and rate together.

Switching back to Suggested preserves the stored manual rate so switching to Manual again restores the user's prior entry.

### 6.2 Planning returns

The preset selector covers every `PlanningPreset`:

1. Regression prediction + 20-year TIPS
2. Conservative estimate + 20-year TIPS
3. 1/CAPE + 20-year TIPS
4. Historical
5. Fixed equity premium
6. Custom
7. Fixed

Conditional fields:

| Preset | Visible fields |
| ------ | -------------- |
| Regression prediction | none |
| Conservative estimate | none |
| 1/CAPE | none |
| Historical | none |
| Fixed equity premium | equity premium |
| Custom | stock base, stock delta, bond base, bond delta |
| Fixed | expected annual stock return, expected annual bond return |

Stock volatility scale is editable under a **Customize** disclosure for every preset.

Mode-specific values are retained when inactive and restored when the user returns to that mode. Existing model defaults seed Fixed values. Fixed-equity-premium and Custom controls receive valid UI defaults when no prior values exist, so selecting those modes does not produce an avoidable intermediate 422.

### 6.3 Resolved-assumptions summary

The section shows values used by the current successful simulation:

- annual inflation
- annual expected stock return
- annual expected bond return
- annual stock log-volatility, displayed as `sqrt(annual_stock_log_variance)`
- selected planning preset
- market source type and observation date for FRED inflation, S&P 500, and Treasury inputs when that input was used

Manual, Fixed, Historical, and vendored values receive explicit source labels. A date is shown only when the underlying source has a meaningful observation/effective date.

The summary is not independently resolved by the web layer. It comes from the simulation-owned snapshot described in §8.

---

## 7. Simulation details

This section is collapsed by default and exposes all persisted technical controls.

### 7.1 Sampling

- block size in months
- number of runs
- stagger run starts
- seed

Only Monte Carlo block-bootstrap controls are shown. Phase 4d does not imply support for tpaw's historical sequential sampling mode.

### 7.2 Percentiles

Percentiles use a comma-separated integer list.

Rules:

- non-empty
- every item is an integer from 0 through 100
- duplicates are rejected
- stored in ascending order

`normalize_percentiles` remains the shared core source of truth and gains duplicate rejection. The form parser handles transport syntax only.

Charts continue to render one trace per configured percentile. Wealth-composition Low, Middle, and High map to the first, middle-index, and last configured percentiles. The UI states this mapping next to the field.

---

## 8. Resolved-assumptions data flow

### 8.1 Simulation metadata

The existing resolvers already compute the numeric assumptions. Phase 4d extends their result metadata rather than resolving a second time:

- `InflationResolved` gains the observation date and market-data source when Suggested mode uses a market series; Manual uses a manual source with no observation date.
- `PlanningReturns` carries the S&P and Treasury source/observation metadata actually consumed by the selected preset. Unused sources remain absent.
- Historical and fixed inputs are labeled without pretending they have live observation dates.

A new public `ResolvedAssumptions` value is attached to `SimulationResult`. It contains display-ready numeric values plus typed source metadata. `preprocess` retains the resolver outputs needed to construct this snapshot; `run_simulation` passes it into public-result assembly. Resolver logic remains in `simulation`, and secrets remain injected at the web boundary.

### 8.2 Initial render

The home route already obtains the current `SimulationResult`. It passes `result.resolved_assumptions` to the Market assumptions template, which includes one shared summary partial.

### 8.3 Automatic refresh

After a successful section save:

1. Existing code dispatches `planUpdated`.
2. The results panel requests the current chart.
3. The plan hash changes, causing one cache miss and one new simulation.
4. The returned results fragment refreshes the chart normally.
5. The same response includes the shared assumptions-summary partial as an HTMX out-of-band replacement.

This keeps charts and the summary on the same run and avoids a second resolver or simulation request.

If the simulation fails after a valid save, the result fragment replaces the prior summary with **Unavailable for current settings**. It must not leave a stale successful summary visible.

---

## 9. Routes, forms, and client behavior

All routes require `?plan={id}` and return 404 for a missing or unknown plan.

| Method | Purpose |
| ------ | ------- |
| `GET` / `PATCH` | Spending goals |
| `GET` / `PATCH` | Risk |
| `GET` / `PATCH` | Market assumptions |
| `GET` / `PATCH` | Simulation details |

Flat sections bind hand-written transport DTOs. Spending goals use `FormData` parsing because they contain two indexed lists.

Conditional-field JavaScript has three responsibilities:

1. show only fields for the selected inflation/return mode;
2. make active conditional fields required and inactive fields non-blocking;
3. preserve inactive field values.

The existing list script gains support for the two spending prefixes without coupling reminting to hard-coded prefix names.

No new client-side business validation is introduced. Browser-required state prevents incomplete intermediate submissions; the server and core models remain authoritative.

---

## 10. Error handling

### Save errors

- Parsing, `ValidationError`, `ValueError`, and arithmetic errors return 422 with a short plain-text message.
- The saved plan is unchanged.
- The existing global form-error banner displays the message.
- No `planUpdated` event fires, so charts and the resolved summary remain aligned with the last saved plan.

### Simulation and market-data errors

- Existing live-fetch failures continue to use cache or vendored fallback.
- A failure that survives fallback is logged server-side with its stack trace.
- The results panel shows the existing generic simulation error.
- The assumptions OOB partial shows **Unavailable for current settings** and no stale values.
- Raw exception text, API keys, and internal paths are never rendered.

### Conditional transitions

The UI must not submit a knowingly incomplete mode transition. In particular:

- Manual inflation waits for a rate.
- Fixed equity premium has a valid default before selection is saved.
- Custom has valid stock and bond base defaults.
- Fixed uses the persisted/default fixed stock and bond values.

---

## 11. Testing

All feature and bug-fix work follows repository TDD policy: scaffold first, observe a logical red failure, then implement and verify green.

| Area | Coverage |
| ---- | -------- |
| Core | duplicate percentile rejection; existing sort/range behavior retained |
| Simulation | inflation and planning-return source metadata for manual, live/cache, vendored, historical, custom, and fixed paths |
| Simulation | `ResolvedAssumptions` values match the exact resolver outputs consumed by preprocessing |
| Simulation | annual displayed stock volatility is derived from the resolved variance |
| Simulation | mixed real and nominal spending streams are converted independently before category summation |
| Web spending | essential/discretionary add, edit, remove, category separation, boundaries, cents preservation, scalar legacy |
| Web merge safety | each PATCH changes only its owned plan fields |
| Web risk | visible and advanced fields round-trip |
| Web inflation | Suggested/Manual round-trip; incomplete Manual transition does not save |
| Web returns | all seven presets; every conditional branch; inactive values preserved |
| Web sampling | block size, runs, stagger, and seed round-trip |
| Web percentiles | arbitrary unique list, sorting, malformed input, duplicates, out-of-range input |
| Web summary | initial render, OOB refresh from the same result, source labels/dates, unavailable state on simulation failure |
| Templates/JS | disclosures and conditional required-state hooks are present; spending prefixes remain generic |

Tests inject dates, fetchers, and repositories. No test performs a real network request. Defaults and constraints come from production code rather than copied literals.

`make` must pass before completion.

---

## 12. PR sizing

Prefer one Phase 4d implementation if the detailed plan remains within the rebuild-index guidance. If the estimate exceeds roughly 2,000 changed lines, split into:

| Subphase | Contents |
| -------- | -------- |
| **4d-1** | Spending goals: essential/discretionary lists and scalar legacy target |
| **4d-2** | Risk, Market assumptions, Simulation details, resolved-assumptions snapshot and OOB refresh |

Each subphase must leave `main` green. The design remains one coherent phase even if delivered as two PRs.

---

## 13. Expected touch map

```text
packages/core/core/models.py
packages/core/tests/test_advanced_config.py

packages/simulation/simulation/market_data/inflation.py
packages/simulation/simulation/planning_returns.py
packages/simulation/simulation/preprocess.py
packages/simulation/simulation/result.py
packages/simulation/simulation/stub.py
packages/simulation/tests/

packages/web/web/forms.py
packages/web/web/routes.py
packages/web/web/sections.py
packages/web/web/app.py
packages/web/web/static/editor_lists.js
packages/web/web/templates/editor_spending.html
packages/web/web/templates/editor_risk.html
packages/web/web/templates/editor_market_assumptions.html
packages/web/web/templates/editor_simulation_details.html
packages/web/web/templates/_resolved_assumptions.html
packages/web/web/templates/index.html
packages/web/web/templates/results.html
packages/web/tests/
```

No package dependency direction changes: `web → simulation, domain, core`; `simulation → domain, core`.

---

## 14. Exit criteria

- [ ] Extra essential and discretionary timed-spending editors
- [ ] Real spending streams preserve purchasing power; nominal streams are deflated independently
- [ ] Scalar real-dollar legacy target
- [ ] Progressive Risk editor covering every `RiskConfig` field
- [ ] Suggested/manual Inflation editor
- [ ] Planning-return editor covering every `PlanningPreset` and conditional field
- [ ] Sampling editor covering block size, runs, stagger, and seed
- [ ] Arbitrary unique percentile editor with documented wealth-chart mapping
- [ ] Resolved inflation, stock, bond, and volatility summary with applicable source dates
- [ ] Summary and charts refresh from the same cached simulation result
- [ ] Failed simulation replaces stale summary with an unavailable state
- [ ] Stream identity remains explicitly deferred to Phase 4e
- [ ] `make` passes

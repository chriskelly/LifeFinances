# Phase 3d — Simulation: Results Data Layer Design

**Date:** 2026-07-10
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md](./2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md),
[2026-07-05-phase-3c-2-simulation-planning-returns-presets-design.md](./2026-07-05-phase-3c-2-simulation-planning-returns-presets-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3d-simulation-results.md` *(to write after spec approval)*
**Commit:** Deferred until implementation (spec lands uncommitted / with the implementation PR).

---

## 1. Goal & scope

Turn the Phase 3b raw per-run engine output into a **chart-ready public result
contract**: percentile-reduced time series plus a deterministic **total-portfolio
wealth composition** (savings vs income sources) for stacked visualization.

Phase 4 renders charts; this phase owns only the simulation/core data layer.

### In scope

- Split today’s `SimulationResult` into a private raw type and a public
  percentile-reduced `SimulationResult`.
- Percentile aggregation over the run axis via `numpy.percentile`.
- `plan.advanced.percentiles` (default `[5, 50, 95]`) with kwarg override on
  `run_simulation`.
- Deterministic wealth-composition series: savings + tax-prorated remaining-income
  NPV by source (`job` / `social_security` / `pension` / `manual`).
- `start_month` metadata on the public result for Phase 4 x-axis labeling.
- Document/test that horizon already starts from `today` and respects per-person
  end age (`Timeline` — parity items 30–31).
- Update `packages/simulation/OVERVIEW.md` (+ brief README note).

### Out of scope

- Web chart rendering / HTMX chart payloads → Phase 4.
- Deferred tpaw major series: withdrawal rate from savings, total-portfolio
  **stock** allocation, spending-tilt series, ending-balance percentile scalars.
- tpaw NPV-for-balance-sheet blob.
- Per-run bootstrapped inflation ([#186](https://github.com/chriskelly/LifeFinances/issues/186)).
- Advanced-options editor UI → Phase 4.

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Simulation package only** | Charts stay Phase 4; 3d ships the data contract. |
| 2 | **Public result = percentile-reduced; raw is private** | Matches tpaw’s wire shape; keeps web memory down; engine tests keep raw arrays. |
| 3 | **Percentiles on `plan.advanced`** | Rarely adjusted; doesn’t belong under sampling (Monte Carlo) or a display-only nest. |
| 4 | **Default `[5, 50, 95]`** | tpaw UI default (`low` / `mid` / `high`). |
| 5 | **Percentile-reduce existing engine series only** | Defer withdrawal-rate / total-portfolio stock allocation / spending-tilt / ending-balance scalars. |
| 6 | **Add wealth composition (wealth view)** | Stacked chart: savings + NPV of remaining income by domain source. |
| 7 | **Income slices = cashflow aggregates** | `job` / `social_security` / `pension` / `manual`. |
| 8 | **Tax proration across sources** | `net_s = gross_s + taxes.stored_total × share` (taxes are non-positive); no separate tax band. |
| 9 | **Post-process aggregator (Approach 1)** | `simulate → raw → aggregate + composition → public`; composition stays out of the Monte Carlo loop. |
| 10 | **`numpy.percentile` (not tpaw pick-from-sorted)** | Simpler; speed is a wash at our sizes. Accepts linear interpolation vs tpaw’s order-statistic pick. |
| 11 | **Do not commit the spec until implementation** | Spec may land with the implementation PR. |

---

## 3. Architecture

```
Plan (+ today)
  → preprocess (cashflows, inflation, planning returns, risk/Merton, NPV)
  → simulate_monthly → RawSimulationResult   # num_runs × months; private
  → aggregate_percentiles(raw, percentiles)
  → attach wealth composition (deterministic)
  → SimulationResult                         # public; percentile × months
```

| Piece | Role |
| ----- | ---- |
| `engine.simulate_monthly` | Emits `RawSimulationResult` (today’s array fields, renamed type). |
| `result.py` | `RawSimulationResult` (private) + public `SimulationResult`. |
| `aggregate.py` (new) | Percentile reduction over the run axis. |
| Composition helper (new module or preprocess) | Tax-prorated per-source remaining-income NPV. |
| `core.models.AdvancedConfig` | `percentiles: list[int]`; nested on `Plan.advanced`. |
| `run_simulation` | Resolve percentiles (kwarg → plan → default); return public result. |

**Package dependency direction unchanged:** `simulation` → `domain`, `core`.

---

## 4. Plan config — `AdvancedConfig`

```python
DEFAULT_PERCENTILES = [5, 50, 95]

class AdvancedConfig(BaseModel):
    percentiles: list[int] = Field(default_factory=lambda: list(DEFAULT_PERCENTILES))

    @field_validator("percentiles")
    @classmethod
    def _validate_percentiles(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("percentiles must be non-empty")
        if any(p < 0 or p > 100 for p in value):
            raise ValueError("each percentile must be in 0..100")
        return sorted(value)

class Plan(BaseModel):
    ...
    advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)
```

`advanced` holds options that are rarely adjusted and do not group cleanly elsewhere.
Percentiles are the first field; later phases may add more.

**Resolution in `run_simulation`:**

1. If `percentiles` kwarg is not `None`, use it (after the same validation rules).
2. Else use `plan.advanced.percentiles`.

---

## 5. Result types

### 5.1 `RawSimulationResult` (private)

Same fields the engine emits today — shape `(num_runs, months)`:

- `balance_start`
- `withdrawals_essential` / `withdrawals_discretionary` / `withdrawals_general` /
  `withdrawals_total`
- `savings_stock_allocation`
- plus `ran_at`, `horizon_months`, `num_runs`, `num_runs_insufficient`,
  `engine_version`

Not part of the public `simulation` package API (may live in `result.py` but not
re-exported from `simulation.__init__` as the primary result type).

### 5.2 Public `SimulationResult`

**Percentile series** — shape `(num_percentiles, months)`, float64, percentile-major
(row `i` corresponds to `percentiles[i]`):

| Field | Source |
| ----- | ------ |
| `balance_start` | raw → percentile |
| `withdrawals_essential` | raw → percentile |
| `withdrawals_discretionary` | raw → percentile |
| `withdrawals_general` | raw → percentile |
| `withdrawals_total` | raw → percentile |
| `savings_stock_allocation` | raw → percentile |

**Wealth composition** (stacked total-portfolio chart):

| Field | Shape | Nature |
| ----- | ----- | ------ |
| `wealth_job` | `(months,)` | deterministic remaining-income NPV (tax-prorated) |
| `wealth_social_security` | `(months,)` | deterministic |
| `wealth_pension` | `(months,)` | deterministic |
| `wealth_manual` | `(months,)` | deterministic |

Savings band for charts is `balance_start[percentile_index, :]` — no duplicate
`wealth_savings` array.

At percentile `p` and month `m`:

```
balance_start[p, m]
  + wealth_job[m] + wealth_social_security[m]
  + wealth_pension[m] + wealth_manual[m]
```

≈ engine total wealth for that savings path
(`balance + npv_income_without_current + income`).

**Metadata:**

- `ran_at`, `horizon_months`, `num_runs`, `num_runs_insufficient`
- `percentiles: list[int]` — resolved list used for this run
- `start_month: tuple[int, int]` — `(year, month)` of month index 0 (`today`)
- `engine_version`

---

## 6. Percentile aggregation

Use NumPy’s stock percentile along the run axis (default linear interpolation):

```python
np.percentile(raw_array, percentiles, axis=0)
# → shape (num_percentiles, months)
```

Apply independently to each raw array field listed in §5.2.

**Note:** This differs from tpaw’s `pickPercentilesFromSorted` (order-statistic index
pick). At typical `num_runs` the visual difference is negligible; we prefer the simpler
API over bit-level chart parity.

---

## 7. Wealth composition (tax-prorated NPV)

**Display-only** — does not change withdrawal / allocation engine math.

### 7.1 Tax proration (per month)

Sources `s ∈ {job, social_security, pension, manual}`.

Domain stores taxes as **non-positive** amounts on `TaxBreakdown.stored_total`
(`net_cashflow[m] = total_gross[m] + taxes.stored_total[m]`). Proration must use
that same signed total:

When `total_gross[m] > 0`:

```
share_s = gross_s[m] / total_gross[m]
net_s[m] = gross_s[m] + taxes.stored_total[m] * share_s
```

When `total_gross[m] == 0`: all `net_s[m] = 0` (any residual taxes that month are
omitted from composition; the engine still uses `net_cashflow`).

Invariant when `total_gross[m] > 0`: `Σ net_s[m] == net_cashflow[m]` (float tolerance).

### 7.2 Real dollars + NPV

Deflate each `net_s` with the same inflation deflator preprocess uses for income.
Backward NPV at the planning **bond** rate, same recurrence as combined income NPV.

At month `m`, `wealth_s[m]` is the NPV of `net_s[m:]` **including** the current month,
so:

```
Σ wealth_s[m] == npv_income_without_current[m] + income_real[m]
```

(within float tolerance), when composition and preprocess share the same discount path
and the same net income total.

### 7.3 Determinism

Composition arrays do not vary by run or percentile. Phase 4 stacks percentile
`balance_start` under the four fixed income bands.

---

## 8. Horizon (parity items 30–31)

Already implemented via `core.timeline.Timeline`:

- Month 0 = current calendar month of injected/`date.today()` `today`.
- Horizon ends at the later present person’s end date (`birth + max_age_years`).

Phase 3d does **not** change timeline logic. It:

- Sets `start_month` from the same `today` used for the run.
- Adds a regression test that public `horizon_months` / `start_month` match `Timeline`.

---

## 9. Testing strategy

TDD throughout; confirm logical (not structural) red before implementing.

1. **Percentile aggregation** — known raw column; output matches `np.percentile(..., axis=0)`
   and shape `(P, M)`.
2. **Tax proration** — known gross/tax month → nets sum to `net_cashflow`; zero-gross → zeros.
3. **Composition NPV** — short horizon, constant bond rate; `Σ wealth_s` matches combined
   income wealth; savings + income wealth matches hand total at month 0.
4. **`run_simulation` public contract** — percentile shapes (not `num_runs × months`);
   `result.percentiles` echoes resolved list; kwarg overrides `plan.advanced.percentiles`.
5. **Horizon** — injected `today` + distinct end ages → `horizon_months` / `start_month`
   match `Timeline`.
6. **Plan validation** — empty / out-of-range percentiles rejected.

No chart-rendering or HTMX tests in this phase.

---

## 10. Error handling

- Invalid percentiles on `Plan` fail Pydantic validation at save/load.
- Kwarg percentiles validated with the same rules before aggregation.
- Aggregation requires `num_runs ≥ 1` (already guaranteed by `SamplingConfig`).
- Composition introduces no new failure modes beyond existing preprocess / cashflow errors.

---

## 11. Documentation & index updates

- `packages/simulation/OVERVIEW.md` — mark percentile aggregation + wealth composition
  as ported in 3d; list deferred tpaw series explicitly.
- `packages/simulation/README.md` — short note: public result is percentile-reduced;
  raw arrays are an internal engine artifact.
- `docs/superpowers/plans/2026-06-12-rebuild-index.md` — Phase 3d exit criteria aligned
  to this spec (public percentile series + composition + `advanced.percentiles` +
  horizon verification).

---

## 12. Explicitly deferred (not 3d)

| Item | Destination |
| ---- | ----------- |
| Chart UI / results panel series wiring | Phase 4 |
| Withdrawal rate from savings | Later / if Phase 4 needs it |
| Total-portfolio stock allocation series | Later |
| Spending-tilt result series | Later (tilt already drives engine) |
| Ending-balance percentile scalars | Later |
| NPV balance-sheet approx blob | Later / skip unless needed |
| Bootstrapped inflation paths | [#186](https://github.com/chriskelly/LifeFinances/issues/186) |
| Advanced percentiles editor UI | Phase 4 |

---

## 13. Exit criteria

- [ ] `RawSimulationResult` is private; `run_simulation` returns public
      `SimulationResult` with percentile-major series for balance, withdrawals, and
      savings stock allocation.
- [ ] Aggregation uses `numpy.percentile` along the run axis (§6).
- [ ] `plan.advanced.percentiles` defaults to `[5, 50, 95]`; kwarg overrides.
- [ ] Wealth composition fields present and reconcile with combined income NPV under
      tax proration (§7).
- [ ] `start_month` + horizon tests document dated start / per-person end age.
- [ ] `OVERVIEW.md` / README / rebuild-index updated.
- [ ] `make` passes.

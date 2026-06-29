# Phase 3b — Simulation: TPAW Monthly Withdrawal Engine Design

**Date:** 2026-06-29
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-25-phase-3a-simulation-market-data-design.md](./2026-06-25-phase-3a-simulation-market-data-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3b-simulation-tpaw-withdrawals.md` *(to write after spec approval)*
**Follow-up:** Phase 3c — planning-returns presets (re-scoped, see §10); Phase 3d — results data layer

---

## 1. Goal & scope

Implement the **full TPAW monthly withdrawal engine** in `packages/simulation`: a
vectorized NumPy forward simulation that turns a `Plan` plus the Phase 3a stochastic
inputs (block-bootstrapped return paths + resolved inflation) into per-run, per-month
portfolio balances and withdrawal splits.

This engine is a Python port of tpaw's TPAW strategy. The authoritative reference is
the tpaw `simulator-cuda` source — chiefly `run_tpaw.cu`,
`cuda_process_tpaw_run_x_mfn_simulated_x_mfn.cu`, `mertons_formula.h`,
`run_common.cu`, and `process_risk.rs`. The withdrawal math in tpaw is **not
separable** from total-portfolio allocation, present-value (PV) discounting, and the
risk model (RRA / Merton's formula): the base ("general") withdrawal is an
amortization of the PV of the total portfolio, discounted at the portfolio's expected
return, and both that discount rate and the spending tilt come from Merton's formula,
which needs RRA. Phase 3b therefore implements all of these together.

The one clean seam is the **source of planning expected returns and volatility**.
Phase 3b uses fixed/manual planning returns (a vendored default on the `Plan`) plus a
stock log-variance computed deterministically from the vendored v7 historical series.
Phase 3c later swaps in live CAPE/EOD-driven presets behind the same interface.

Phase 3b includes:

1. **Risk model** — port tpaw's risk-tolerance → RRA conversion (at-20, delta-to-max-age,
   legacy delta), time preference, and additional spending tilt, as a persisted
   `RiskConfig` on the `Plan` (tpaw defaults; no UI this phase).
2. **Planning returns config** — manual expected annual stock/bond returns (vendored
   defaults) as `PlanningReturnsConfig` on the `Plan`; stock log-variance derived from
   the vendored v7 series.
3. **Spending inputs** — extra **essential** and **discretionary** timed-stream lists
   and a scalar **legacy target** on the `Plan` (no UI this phase).
4. **Merton's formula** — per-month stock allocation + spending tilt from effective RRA
   and planning returns, with the equity-premium/variance clamp and the
   infinite-RRA (0% stocks) case.
5. **Backward NPV precompute pass** — per month, the approximate PV of future income,
   essential expenses, discretionary expenses, and legacy, plus the
   `cumulative_1_plus_g_over_1_plus_r` amortization factor; all vectorized across runs.
6. **Forward monthly loop** — vectorized across runs, sequential over months:
   wealth assembly, essential/discretionary/legacy/general withdrawal split, the
   "expected run" + elasticity scaling of discretionary/legacy goals, contributions and
   withdrawals, savings-portfolio stock allocation, monthly rebalancing, and applying
   bootstrapped returns.
7. **Raw per-run result arrays** — `SimulationResult` carrying `num_runs × months`
   arrays for starting balance, the withdrawal splits, savings-portfolio stock
   allocation, and an insufficient-funds count.
8. **Documentation** — `packages/simulation/README.md` (human-readable flow) and
   `packages/simulation/OVERVIEW.md` (parity backlog + GPU-parity caveat).

Phase 3b does **not** include:

- Percentile aggregation or chart-ready result series (Phase 3d). The engine emits raw
  per-run arrays; `run_simulation`'s `percentiles` argument stays accepted-but-unused.
- Spending **ceiling/floor** — permanently removed per rebuild-design item 3 (spending
  tilt only). The tpaw ceiling/floor branch is intentionally not ported.
- Live/networked planning returns: CAPE regression, EOD equity data, empirical
  stats-by-block-size, or a stock-allocation glide path (all Phase 3c).
- Bootstrapped (per-run) inflation paths — still scalar per Phase 3a ([#186]).
- Tax-advantaged account buckets; withdrawal/capital-gains taxes (income-side only).
- Any editor UI for the new config (Phase 4).
- Bit-identical parity with tpaw's CUDA float32 streams (see §8).

[#186]: https://github.com/chriskelly/LifeFinances/issues/186

---

## 2. Decisions captured from brainstorming

| #   | Decision | Rationale |
| --- | -------- | --------- |
| 1 | **3b = full TPAW engine; re-scope 3c to "planning-returns presets"** | tpaw's withdrawal math is inseparable from Merton/RRA/PV. The only real seam is where planning returns/vol come from, so that becomes 3c. The rebuild index 3c entry is rewritten to match (see §10). |
| 2 | **Fixed/manual planning returns in 3b** | Lets the full engine land now with deterministic, offline inputs; live presets slot in behind the same interface in 3c. |
| 3 | **Stock log-variance derived from vendored v7 series** | Deterministic and offline; avoids a hand-entered field that could drift. Empirical-stats-by-block-size refinement deferred to 3c. |
| 4 | **Single vectorized NumPy engine (no scalar oracle shipped)** | Fast enough for the debounced live results panel (~500 runs × ~900 months). Confidence comes from unit-testing the pure math primitives against tpaw's own doctest values rather than from a second engine. |
| 5 | **Math primitives are pure functions, unit-tested against tpaw doctests** | Merton, RRA, NPV discounting, contributions/withdrawals, and allocation are factored out and pinned to the exact expected values embedded in tpaw's CUDA/Rust tests. |
| 6 | **No external golden file** | tpaw's engine is CUDA and will not run on the dev machine. We reuse the hardcoded expected values already in tpaw's doctests as unit goldens, plus a looser deterministic end-to-end sanity test. True full-path parity validation is deferred to a later issue. |
| 7 | **Raw per-run output arrays; percentiles in 3d** | Keeps the 3b surface small and gives 3d full ownership of reduction. |
| 8 | **General (base) withdrawal starts at month 0** | Matches the "retirement is implicit" philosophy: results show sustainable *current and expected* spending from today. No retirement-date / `withdrawal_start_month` input (fixed at 0). Income during working years still flows in as contributions, so the portfolio grows via surplus. |
| 9 | **numpy float64** | Consistent with Phase 3a market-data code; `Decimal` stays for money in `core`/`domain` and converts to float at the engine boundary. |
| 10 | **New config persisted on the `Plan` in `core`, UI deferred** | Same pattern Phase 3a used for `SamplingConfig`/`InflationConfig`. tpaw-sourced defaults; Phase 4 adds editors. |
| 11 | **Spending ceiling/floor permanently dropped** | rebuild-design item 3. Not ported. |

---

## 3. Plan schema additions (`packages/core`)

All new blocks are optional with tpaw-sourced defaults so existing plans keep working,
and none get editor UI this phase (Phase 4). Default *numbers* are pulled from tpaw's
default/test plan params during implementation, not invented; the pinned RRA constants
match tpaw exactly and are not user-editable.

### `RiskConfig`

| Field | Default (tpaw) | Feeds |
| ----- | -------------- | ----- |
| `risk_tolerance_at_20` | `12` | per-month risk tolerance → RRA |
| `delta_at_max_age` | `0` | age glide of risk tolerance |
| `legacy_delta_from_at_20` | `0` | separate legacy RRA |
| `time_preference` | `0` | Merton spending tilt |
| `additional_annual_spending_tilt` | `0` | extra spending tilt |

Pinned constants (module-level in `core`, not on the editable model):
`RISK_TOLERANCE_NUM_VALUES = 25`, `RISK_TOLERANCE_START_RRA = 16.0`,
`RISK_TOLERANCE_END_RRA = 0.5`.

### `PlanningReturnsConfig`

| Field | Default | Notes |
| ----- | ------- | ----- |
| `expected_annual_return_stocks` | vendored | manual planning return |
| `expected_annual_return_bonds` | vendored | manual planning return |

Stock log-variance is **computed** from the vendored v7 historical series at load
(deterministic, offline), not stored as a field. Phase 3c may override the
expected-return source with live presets.

### Spending inputs (on `Plan`)

| Field | Type | Default |
| ----- | ---- | ------- |
| `extra_essential_spending` | `list[TimedStream]` | `[]` |
| `extra_discretionary_spending` | `list[TimedStream]` | `[]` |
| `legacy_target` | `Decimal` | `0` |

Reuses the existing `TimedStream` type and month-indexing from Phase 2a. There is no
user "base spending target": the **general** withdrawal is the computed amortized
output of the engine.

---

## 4. Engine architecture (`packages/simulation`)

The public entry point is unchanged:

```python
def run_simulation(plan: Plan, *, percentiles: list[int]) -> SimulationResult: ...
```

Data flow:

```
domain.build_monthly_cashflows(plan)        # Decimal net income/taxes per month
        │  (→ float64 at the boundary)
        ▼
preprocess(plan, cashflows)                 # NEW
  ├─ resolve_inflation(plan)                # Phase 3a (scalar monthly rate)
  ├─ build_return_paths(plan, months)       # Phase 3a (per-run monthly returns)
  ├─ risk:    RRA-by-month + legacy RRA     # NEW  (risk.py)
  ├─ mertons: stock-alloc + spending-tilt   # NEW  (mertons.py)
  └─ npv:     backward PV pass + cumulative  # NEW  (npv.py, vectorized)
        ▼
simulate_monthly(processed)                 # NEW vectorized forward loop (engine.py)
        ▼
SimulationResult  (raw per-run arrays)      # expanded result.py
```

New modules, mirroring tpaw's separation of concerns:

| Module | Responsibility | tpaw reference |
| ------ | -------------- | -------------- |
| `simulation/risk.py` | risk-tolerance → RRA (at-20, age glide, legacy), pinned constants | `process_risk.rs` |
| `simulation/mertons.py` | Merton's formula: stock allocation + spending tilt; equity-premium/variance clamp; ∞-RRA case | `mertons_formula.h` |
| `simulation/npv.py` | backward PV precompute pass; `cumulative_1_plus_g_over_1_plus_r` | `cuda_process_tpaw_run_x_mfn_simulated_x_mfn.cu` |
| `simulation/engine.py` | vectorized forward monthly loop; wealth, withdrawal split, expected-run elasticity, contributions/withdrawals, allocation, rebalancing | `run_tpaw.cu`, `run_common.cu` |
| `simulation/result.py` | expanded `SimulationResult` (raw per-run arrays) | `simulation_result.rs` |
| `simulation/preprocess.py` | assemble processed inputs from plan + 3a outputs | `process_plan_params_server.rs` |

Inflation use: domain cashflows are nominal; the engine works in **real** terms
(matching tpaw's real historical returns), converting nominal cashflows to real with
the resolved scalar monthly inflation rate at the boundary.

Vectorization: **runs are the array axis**; the month loop is sequential (each month
depends on the previous month's ending balance). The backward NPV pass is likewise
vectorized across runs. Target ~tens of milliseconds for ~500 runs × ~900 months.

---

## 5. The monthly math (parity with tpaw)

Per month, computed for all runs at once, mirroring `run_tpaw.cu::_single_month`.

**Backward precompute** (before the forward loop), per `cuda_process_tpaw_...cu`:
- Discount future income & essential at the bond rate; discretionary & general at the
  portfolio rate (which depends on that month's Merton stock allocation).
- Accumulate `cumulative_1_plus_g_over_1_plus_r`, where `g` is the Merton spending tilt
  — this is the amortization factor that spreads the general pool across remaining
  months with the intended spending growth.
- Compute legacy NPV using the separate legacy RRA's portfolio rate.

**Forward step**, per month:
1. **Wealth** = savings balance + NPV(future income, excl. current month) + current-month income.
2. Withdraw NPV(essential), then NPV(discretionary × scale), then NPV(legacy × scale)
   from wealth; the remainder is the **general** pool. (`AccountForWithdrawal`
   semantics: each draw is clamped to the running balance.)
3. **Expected run + elasticity** (tpaw's mechanism): an "expected run" using planning
   returns establishes scheduled wealth and the elasticities of discretionary/legacy
   goals w.r.t. wealth; normal runs scale those goals up/down by how their wealth
   compares to scheduled wealth.
4. **Target withdrawals**: essential = current essential; discretionary = scaled
   current discretionary; general = general pool ÷ `cumulative_1_plus_g_over_1_plus_r`.
   (No ceiling/floor.)
5. **Contributions & withdrawals**: add current income (contribution), subtract
   withdrawals; clamp general to available funds and flag insufficient funds when the
   portfolio cannot cover the target.
6. **Stock allocation** on the savings portfolio derived from the total-portfolio
   target (`_get_stock_allocation`): stocks target across general/discretionary/legacy
   pools ÷ savings-portfolio balance, saturated to [0, 1].
7. **Apply allocation & returns**: split the post-withdrawal balance by stock
   allocation, apply that run/month's bootstrapped stock & bond real returns (monthly
   rebalancing), producing the ending balance carried to the next month.

`withdrawal_start_month = 0` for all months (general spending active from today).

---

## 6. Result shape

`SimulationResult` carries **raw per-run arrays** (shape `num_runs × months`, float64):

| Field | Meaning |
| ----- | ------- |
| `balance_start` | savings-portfolio balance at the start of each month |
| `withdrawals_essential` | essential withdrawal |
| `withdrawals_discretionary` | discretionary withdrawal |
| `withdrawals_general` | general (base) withdrawal |
| `withdrawals_total` | sum of the three |
| `savings_stock_allocation` | stock fraction of the savings portfolio after withdrawals |
| `num_runs_insufficient` | count of runs that hit insufficient funds at any month |

Plus existing metadata (`ran_at`, `horizon_months`). Percentile reduction and the full
tpaw chart catalog (total-portfolio allocation, spending-tilt series, ending-balance
percentiles, etc.) are Phase 3d. The `percentiles` parameter on `run_simulation` stays
accepted but unused this phase.

---

## 7. Testing strategy (TDD throughout)

**Unit goldens — math primitives pinned to tpaw doctest values** (tolerance-based;
literals are intentionally pinned contract values, comment-marked as sourced from the
named tpaw test):

- `mertons.py`: cases from `plain_mertons_formula` / `effective_mertons_formula`
  (RRA range incl. ∞, no/negative equity premium, min-RRA clamp, time preference,
  additional spending tilt).
- `risk.py`: `get_rra_for_all_stocks` and risk-tolerance → RRA endpoints/midpoints.
- `npv.py`: `_get_precomputation_at_start` (expected run, more-wealth, less-wealth
  elasticity), `_get_target_withdrawals_assuming_no_ceiling_or_floor`,
  `_get_stock_allocation`.
- `engine.py` helpers: `apply_contributions_and_withdrawals` (sufficient/insufficient),
  `apply_allocation`.

**End-to-end sanity** (deterministic, no network): constant-return scenario with
money-conservation checks, zero-income behavior, a couple of hand-verified months, and
monotonicity spot-checks (e.g. higher starting balance ⇒ higher general withdrawal).

Per repo policy: confirm each new test first fails on a logical/assertion error (not a
structural import error) before implementing, and pull constants from source rather
than duplicating literals — except the tpaw doctest goldens, which are deliberately
pinned with comments.

---

## 8. Numerical parity caveat

tpaw runs on CUDA with mixed float32/float64 and ChaCha8 RNG streams. This port uses
NumPy float64 and the Phase 3a seeded RNG. We target **algorithmic** parity (same
formulas, same sequencing) validated against tpaw's published doctest values, **not**
bit-identical output. This caveat is recorded in `OVERVIEW.md`.

---

## 9. Documentation deliverables

- **`packages/simulation/README.md`** — human-readable walkthrough of the simulation
  flow: the journey from `Plan` → domain cashflows → preprocess (inflation, return
  paths, risk/RRA, Merton, NPV) → forward monthly loop → raw result arrays, with the
  intuition for wealth, the essential/discretionary/general/legacy split, spending
  tilt, and total-portfolio allocation. Written for a human reader, not a parity spec.
- **`packages/simulation/OVERVIEW.md`** — the parity backlog the rebuild index
  references from "3b onward": what is ported vs deferred, the doctest-golden approach,
  and the float64/GPU-parity caveat from §8.

---

## 10. Rebuild index updates

On approval, update `docs/superpowers/plans/2026-06-12-rebuild-index.md`:

- **Active phase** table → Phase 3b active, plan file to write.
- **Phase 3b** exit criteria refined to match this spec (full engine; raw per-run
  arrays; doctest goldens; spending tilt; month-0 withdrawal start).
- **Phase 3c** entry rewritten from "allocation + PV" to **"planning-returns presets"**:
  live CAPE/EOD-driven expected returns, empirical-variance refinement, and any
  stock-allocation glide path — RRA/Merton/PV/total-portfolio allocation now land in 3b.
- Mark this spec as the Phase 3b design reference.

---

## 11. Open items / deferred

- Per-run bootstrapped inflation paths — [#186] (still scalar).
- Full chart-series result catalog + percentiles — Phase 3d.
- Live planning-returns presets (CAPE/EOD) + glide path — Phase 3c.
- Tax-advantaged buckets, withdrawal taxes — later phase.
- True full-path parity validation against a captured tpaw export — later issue.

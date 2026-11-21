# TPAW parity and numerical validation

Scope: how the engine maps to TPAW, what is deferred, and how correctness is
validated. Read before changing engine math, planning-return presets, or parity
goldens.

This package is a Python port of [TPAW](https://tpawplanner.com/)'s withdrawal
engine (formerly CUDA/Rust: `run_tpaw.cu`, `run_common.cu`,
`mertons_formula.h`, `process_risk.rs`, `simulation_result.rs`,
`process_plan_params_server.rs`). This document tracks which TPAW features have
been ported so far, which are intentionally deferred, and how we validate
numerical correctness without a runnable TPAW binary to diff against.

## Feature parity table

| Feature | Status | Where |
| --- | --- | --- |
| Risk-tolerance → RRA conversion (age glide, legacy delta) | Ported | `../simulation/risk.py` |
| Time-preference sign convention (both UIs show −TPR as "Preference for the Future") | Ported | Input and sign mapping |
| Merton's formula (stock allocation + spending tilt, equity-premium/variance clamps, ∞-RRA case) | Ported | `../simulation/mertons.py` |
| Backward NPV precompute pass + `cumulative_1_plus_g_over_1_plus_r` amortization | Ported | `../simulation/npv.py`, `../simulation/preprocess.py` |
| Vectorized forward monthly loop (wealth, pool carve, expected-run elasticity, contributions/withdrawals, allocation, rebalancing) | Ported | `../simulation/engine.py` |
| Expected-run diagnostics (RRA, Merton, savings carve series, and monthly net-income flows) on raw + public results | Ported | `../simulation/diagnostics.py`, `../simulation/engine.py` |
| Raw per-run result arrays (engine-internal) | Ported | `../simulation/result.py` (`RawSimulationResult`) |
| Percentile aggregation (10th/50th/90th, etc. reduction over raw arrays) | Ported | `../simulation/aggregate.py` |
| Wealth composition (tax-prorated NPV by income source: job / SS / pension / manual) | Ported | `../simulation/composition.py` |
| Planning-returns presets (live CAPE/EOD-derived expected returns, empirical variance refinement) | Ported | `../simulation/presets.py`, `../simulation/market_data/presets_data.py` |
| S&P + Treasury 20-yr TIPS market feeds (cache + vendored fallback) | Ported | `../simulation/market_data/` |
| Historical-returns adjustment (rescale bootstrapped returns to the planning expected return: block-size shift correction, log-volatility scaling) | Ported | `../simulation/market_data/bootstrap.py`, `../simulation/presets.py` |
| Bootstrapped/stochastic inflation (currently a single resolved scalar inflation rate for the whole horizon) | Deferred | Issue #186 |
| Spending ceiling/floor constraints | Removed from scope | Not planned — this rebuild's product scope removed ceiling/floor |
| Detailed tax-bucket modeling interactions with withdrawals (traditional vs. Roth vs. taxable sequencing) | Deferred | Unscheduled |
| Withdrawal rate from savings | Deferred | Later / if needed |
| Total-portfolio stock allocation series | Deferred | Later |
| Spending-tilt result series | Deferred | Later (tilt already drives engine) |
| Ending-balance percentile scalars | Deferred | Later |
| NPV balance-sheet approx blob | Deferred | Later / skip unless needed |

`run_simulation` returns a public, percentile-major `SimulationResult` (balance,
withdrawals, savings stock allocation, wealth-composition bands, plus expected-run
`diagnostics`). The engine still emits private `RawSimulationResult`
(`num_runs × months`); aggregation happens in `../simulation/aggregate.py` via
`numpy.percentile` along the run axis. Percentiles default from
`plan.advanced.percentiles` (`[5, 50, 95]`); the `percentiles` kwarg overrides.
Chart UI wiring lives in the web package.

## Numerical parity caveat

TPAW runs on CUDA with mixed float32/float64 arithmetic and ChaCha8 RNG
streams. This port uses NumPy `float64` throughout and the seeded RNG
(`numpy.random.default_rng`), which is **not** bit-identical to TPAW's ChaCha8
streams — see `../simulation/market_data/bootstrap.py`'s `build_index_sequences`
docstring, which already notes "algorithmic parity, our own determinism." We
target **algorithmic** parity — the same formulas applied in the same
sequence — validated against TPAW's own published test/doctest values, not
bit-identical output against a running TPAW instance. Differences at the level
of floating-point rounding (float32 vs. float64) or RNG stream identity are
expected and are not treated as bugs.

Bootstrapped return paths match TPAW's historical-returns adjustment.
`../simulation/market_data/bootstrap.py::adjusted_historical_returns` rescales the vendored
monthly log series (via `presets.adjust_log_returns`) so the *block-bootstrapped*
annualized non-log mean equals the planning expected return, using the per-block
empirical mean for the shift correction and scaling stocks' deviations by
`stock_volatility_scale` (bonds at `1.0`). This mirrors TPAW's
`process_historical_returns.rs` → `adjust_log_returns_detailed` and its
`adjust_log_returns_monte_carlo` test (the `block_size=None` case is the
preset-menu correction in `presets._shift_correction`). The deterministic
expected run uses planning returns and is unaffected.

The block size and volatility scale are read from the resolved `PlanningReturns`
snapshot rather than directly from `Plan`, so the adjustment targets and the
index sequences use the same values. `build_return_paths` raises `ValueError`
when its `plan` and `planning` arguments disagree on `block_size_months` or
`stock_volatility_scale` — resolve planning from the same plan you pass in.

## Input and sign mapping

The risk block can be a source of month-0 drift because some quantities are
stored with opposite signs. Compare the stored values, not the UI labels.

| TPAW export path | LifeFinances | Convention |
| --- | --- | --- |
| `risk.tpaw.riskTolerance.at20` | `risk.risk_tolerance_at_20` | Same value. |
| `risk.tpaw.riskTolerance.deltaAtMaxAge` | `risk.delta_at_max_age` | TPAW stores the negation of the displayed decrease and adds it (`at20 + deltaAtMaxAge`); LifeFinances stores the decrease and subtracts it. TPAW `-8` corresponds to LifeFinances `8`. |
| `risk.tpaw.riskTolerance.forLegacyAsDeltaFromAt20` | `risk.legacy_delta_from_at_20` | Same value; added to the age-20 tolerance. Affects only the legacy carve. |
| `risk.tpaw.timePreference` | `risk.time_preference` | Both are the time preference rate (impatience). Both UIs show **Preference for the Future**, the negation of this stored rate. |
| `risk.tpaw.additionalAnnualSpendingTilt` | `risk.additional_annual_spending_tilt` | Same value; added directly to the Merton spending tilt. |
| `advanced.returnsStatsForPlanning.expectedValue.empiricalAnnualNonLog.type` | `planning_returns.preset` | Preset mapping; for example `conservativeEstimate,20YearTIPSYield` ↔ `conservative_estimate`. |
| `advanced.sampling.data.blockSize.inMonths` | `sampling.block_size_months` | Same value. |
| `advanced.sampling.data.staggerRunStarts` | `sampling.stagger_run_starts` | Same value. |
| `advanced.annualInflation` | `inflation` | `suggested` ↔ `mode: suggested`; a manual rate maps to `manual_annual_rate`. |
| `wealth.portfolioBalance.amount` (or `updatedTo` when carried forward) | `portfolio.current_savings_balance` | Same value. |
| `adjustmentsToSpending.tpawAndSPAW.legacy.total` | `legacy_target` | Same value. |
| `adjustmentsToSpending.extraSpending.essential` / `.discretionary` | `extra_essential_spending` / `extra_discretionary_spending` | Amounts and windows; LifeFinances includes both start and end months, while TPAW's `startAndDuration` is a duration. |
| `wealth.incomeDuringRetirement` | jobs, Social Security, pension, manual streams | TPAW stores net manual streams; LifeFinances builds gross and taxes. Not one-to-one; compare annualized flows. |
| `people.*.ages.maxAge.inMonths` | `household.person*.max_age_years` | TPAW months; LifeFinances years. |

**Time-preference sign trap.** Both UIs show the negation of the stored
`timePreference`/`time_preference` rate: a visible +0.5% is stored `-0.005` in
both. The engine applies the stored rate as impatience. Compare the stored
values when diffing an export, or negate a displayed value before comparing it
with a stored rate. The UIs display `-TPR` for direction: moving the slider
right increases future spending. TPAW shows the stored TPR in its foldable
details; LifeFinances' help text describes it. A one-point rate mismatch moved
month-0 spending by roughly 7–8% on a long-horizon plan, versus about 0.6% for
a half-point glide mismatch.

**Glide sign trap.** TPAW's UI shows the decrease and stores its negation;
LifeFinances stores the decrease itself. TPAW `-8` is LifeFinances `8`, not
`-8`.

The legacy delta is not negated. It is added to the age-20 tolerance in both.

## Investigating a gap against a real TPAW plan

When the two disagree, the cause may be an input mismatch (cheaper to debug),
rather than engine math.
Work in this order.

**Compare month 0 first.** The first month is identical across Monte Carlo runs,
so a month-0 gap cannot come from sampling, the RNG, or the historical-returns
adjustment. Only read the later months once month 0 agrees.

**Diff the inputs, most sensitive first:** portfolio balance; risk (tolerance at
20, glide to max age, legacy delta, time preference, additional annual spending
tilt); planning-return preset and log-volatility scales; inflation; sampling;
horizon. For the risk block, use the mapping table above — TPAW's UI shows the
glide decrease and Preference for the Future; both are the negation of TPAW's
stored values.

**Take TPAW's values from an exported plan.** Plan menu → *Save to File* writes a
`.tpaw.txt`: prose header, then JSON from the first `{`. The payload is a
JSON-patch **history**, not a params snapshot — replay `planParamsHistory[].diff`
in order over an empty object (only `add`, `replace`, and `remove` appear in
practice); `reverseHeadIndex: 0` means the last entry is the current state. The
head's `timestamp` is the plan's **evaluation date**: run LifeFinances with
`today` set to it, because planning returns come from that date's CAPE and TIPS
data.

**Expect these mapping differences.** TPAW has no tax model — its `futureSavings`
and `incomeDuringRetirement` are net amounts, while LifeFinances builds gross
job/SS/pension income and taxes it; compare annualized `income_real` against the
stream schedule and accept a few percent of drift. `forLegacyAsDeltaFromAt20` is
added to the tolerance at 20, and `additionalAnnualSpendingTilt` is added
directly to the Merton spending tilt (the `deltaAtMaxAge` and time-preference
signs are covered above). TPAW's `startAndDuration` extra-spending windows are
durations, while LifeFinances includes both the start and end months; a
12-month TPAW sabbatical becomes 13 months in LifeFinances if the end is copied
literally. TPAW's month count includes the max-age month, so a tail difference
can be the horizon rather than the math. TPAW's chart percentile set and run
count are not in the exported params, so do not treat a band difference as
engine drift; compare month 0 and the summary scalars first.

**Mutate copies.** Ablate parameters on a copy of the plan — never the stored
plan or the exported TPAW params.

**Sensitivity, for triage on a long-horizon plan with real returns near 3%:** a
0.5%/yr additional spending tilt moves month-0 spending by roughly 12%, a
1.0-point time-preference mismatch by roughly 7–8%, a risk-tolerance glide of
2 points by roughly 5%, and one horizon month by roughly 0.1%. Tilt, time
preference, and glide mismatches are large enough to explain a four-figure
monthly gap on their own.

Two worked examples. A plan carrying a −0.5%/yr additional tilt and a flat
glide, compared against TPAW with tilt 0 and a 2-point glide, differed by
~$1k/month at month 0 and matched once both inputs were aligned, with no engine
change. A second plan showed $14,041 at month 0 with `time_preference = -0.005`
and $15,028 with `time_preference = +0.005`; the TPAW export carried the
positive rate and charted $14,952. Aligning the sign moved month 0 to within
$76 (0.5%) of TPAW, leaving only the usual net-income/tax drift.

## Testing approach: doctest-golden values

There is no runnable TPAW binary in this repo to diff full simulation runs
against, so correctness is validated in two layers:

1. **Unit goldens pinned to TPAW's own test cases.** The pure-math modules —
   `../simulation/mertons.py` (plain/effective Merton's formula cases, `get_rra_for_all_stocks`),
   `../simulation/risk.py` (risk-tolerance → RRA endpoints), `../simulation/npv.py`
   (backward precomputation at start, target withdrawals with no
   ceiling/floor, stock allocation), and `../simulation/withdrawals.py`
   (`apply_contributions_and_withdrawals`, `apply_allocation`) — have unit
   tests whose expected values are copied from TPAW's own doctests/test cases
   (e.g. `mertons_formula.cu`'s `plain_mertons_formula` test cases) and checked
   with a tolerance rather than exact equality (floating-point + float32/64
   parity caveat above). These literals are intentionally pinned contract
   values and are comment-marked with the TPAW test they were sourced from
   (e.g. `# pinned: tpaw mertons_formula.cu plain_mertons_formula TEST_CASE`).
2. **Deterministic end-to-end sanity checks.** Because there's no TPAW binary
   to run side-by-side, full-simulation correctness is checked with
   deterministic (no network, no live market data), constant-return scenarios:
   money-conservation checks (nothing is created or destroyed across a run),
   zero-income behavior, and monotonicity spot-checks (e.g. a run with better
   returns should never do worse than one with worse returns, all else equal).

Together, these give confidence that each individual formula matches TPAW's
own reference values, and that the assembled pipeline behaves sensibly, even
though no full end-to-end numerical diff against TPAW is possible.

## Planning-returns presets

The preset menu is at full TPAW parity: preset choice changes expected returns
only, not variance; planning returns are fixed at month 0 with no glide path.
The stock-allocation glide follows the separate RRA age glide, not planning
returns. The planning-returns mechanism is in `packages/simulation/README.md`
(Planning returns and CAPE regression).

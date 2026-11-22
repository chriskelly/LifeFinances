# TPAW parity and input mapping

Scope: how the engine maps to TPAW and what behavior matches. Read before
changing engine math or planning-return presets. Numerical validation and gap
diagnosis: `numerical-validation.md`.

This package is a Python port of [TPAW](https://tpawplanner.com/)'s withdrawal
engine (formerly CUDA/Rust: `run_tpaw.cu`, `run_common.cu`,
`mertons_formula.h`, `process_risk.rs`, `simulation_result.rs`,
`process_plan_params_server.rs`). This document records the behavior the port
implements and the input mapping needed to compare the two. Current product
scope is in `packages/simulation/README.md`.

## Implemented TPAW behavior

| TPAW feature | LifeFinances implementation |
| --- | --- |
| Risk-tolerance → RRA conversion (age glide, legacy delta) | `../simulation/risk.py` |
| Merton's formula (stock allocation + spending tilt, equity-premium/variance clamps, ∞-RRA case) | `../simulation/mertons.py` |
| Backward NPV precompute pass + `cumulative_1_plus_g_over_1_plus_r` amortization | `../simulation/npv.py`, `../simulation/preprocess.py` |
| Vectorized forward monthly loop (wealth, pool carve, expected-run elasticity, contributions/withdrawals, allocation, rebalancing) | `../simulation/engine.py` |
| Expected-run diagnostics (RRA, Merton, savings carve series, and monthly net-income flows) on raw + public results | `../simulation/diagnostics.py`, `../simulation/engine.py` |
| Raw per-run arrays + percentile aggregation (10th/50th/90th, etc.) | `../simulation/result.py`, `../simulation/aggregate.py` |
| Wealth composition (tax-prorated NPV by income source: job / SS / pension / manual) | `../simulation/composition.py` |
| Planning-returns presets (live CAPE/EOD-derived expected returns, empirical variance refinement) | `../simulation/presets.py`, `../simulation/market_data/presets_data.py` |
| S&P + Treasury 20-yr TIPS market feeds (cache + vendored fallback) | `../simulation/market_data/` |
| Historical-returns adjustment (rescale bootstrapped returns to the planning expected return: block-size shift correction, log-volatility scaling) | `../simulation/market_data/bootstrap.py`, `../simulation/presets.py` |

## Numerical parity caveat

TPAW runs on CUDA with mixed float32/float64 arithmetic and ChaCha8 RNG
streams. This port uses NumPy `float64` throughout and the seeded
`numpy.random.default_rng`, which is **not** bit-identical to TPAW's ChaCha8
streams — see the `build_index_sequences` comment in
`../simulation/market_data/bootstrap.py`. We target **algorithmic** parity: the
same formulas applied in the same sequence, validated against TPAW's published
test/doctest values, not bit-identical output against a running TPAW instance.
Differences at the level of floating-point rounding or RNG stream identity are
expected and are not treated as bugs.

Bootstrapped return paths match TPAW's historical-returns adjustment; the
mechanism and TPAW function/test mapping are in
`packages/simulation/README.md` (Stage by stage → **Return paths**).
`build_return_paths` raises `ValueError` when its `plan` and `planning`
arguments disagree on `block_size_months` or `stock_volatility_scale` — resolve
planning from the same plan you pass in.

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
| `wealth.futureSavings` / `wealth.incomeDuringRetirement` | jobs, Social Security, pension, manual streams | TPAW stores net future savings and retirement income; LifeFinances builds gross income and taxes it. Not one-to-one; compare annualized flows. |
| `people.*.ages.maxAge.inMonths` | `household.person*.max_age_years` | TPAW months; LifeFinances years. |

**Time-preference sign trap.** A visible +0.5% is stored -0.005 in both UIs.
Compare stored values when diffing an export, or negate a displayed value before
comparing. TPAW shows the stored TPR in its foldable details; LifeFinances' help
text describes it.

## Planning-returns presets

The preset menu is at full TPAW parity: preset choice changes expected returns
only, not variance; planning returns are fixed at month 0 with no glide path.
The stock-allocation glide follows the separate RRA age glide, not planning
returns. The planning-returns mechanism is in `packages/simulation/README.md`
(Planning returns and CAPE regression).

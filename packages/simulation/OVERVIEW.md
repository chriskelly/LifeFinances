# `simulation` — TPAW parity backlog

This package is a Python port of [TPAW](https://tpawplanner.com/)'s withdrawal
engine (formerly CUDA/Rust: `run_tpaw.cu`, `run_common.cu`,
`mertons_formula.h`, `process_risk.rs`, `simulation_result.rs`,
`process_plan_params_server.rs`). This document tracks which TPAW features have
been ported so far, which are intentionally deferred, and how we validate
numerical correctness without a runnable TPAW binary to diff against.

## Feature parity table

| Feature | Status | Where |
| --- | --- | --- |
| Risk-tolerance → RRA conversion (age glide, legacy delta) | Ported (Phase 3b) | `simulation/risk.py` |
| Merton's formula (stock allocation + spending tilt, equity-premium/variance clamps, ∞-RRA case) | Ported (Phase 3b) | `simulation/mertons.py` |
| Backward NPV precompute pass + `cumulative_1_plus_g_over_1_plus_r` amortization | Ported (Phase 3b) | `simulation/npv.py`, `simulation/preprocess.py` |
| Vectorized forward monthly loop (wealth, pool carve, expected-run elasticity, contributions/withdrawals, allocation, rebalancing) | Ported (Phase 3b) | `simulation/engine.py` |
| Raw per-run result arrays | Ported (Phase 3b) | `simulation/result.py` |
| Percentile aggregation (10th/50th/90th, etc. reduction over raw arrays) | Deferred | Phase 3d |
| Planning-returns presets (live CAPE/EOD-derived expected returns, empirical variance refinement) | Ported (Phase 3c-2) | `simulation/market_data/presets.py`, `simulation/market_data/presets_data.py` |
| S&P + Treasury 20-yr TIPS market feeds (cache + vendored fallback) | Ported (Phase 3c-1) | `simulation/market_data/` |
| Bootstrapped/stochastic inflation (3b uses a single resolved scalar inflation rate for the whole horizon) | Deferred | Issue #186 |
| Spending ceiling/floor constraints | Removed from scope | Not planned — this rebuild's product scope removed ceiling/floor |
| Detailed tax-bucket modeling interactions with withdrawals (traditional vs. Roth vs. taxable sequencing) | Deferred | Later phase, unscheduled |

`run_simulation`'s `percentiles: list[int] | None` parameter (see
`simulation/stub.py`) is already accepted at the call site so downstream API
shape doesn't need to change again in Phase 3d, but the value is currently
unused (`_ = percentiles  # reserved for Phase 3d aggregation`).

## Numerical parity caveat

TPAW runs on CUDA with mixed float32/float64 arithmetic and ChaCha8 RNG
streams. This port uses NumPy `float64` throughout and the Phase 3a seeded RNG
(`numpy.random.default_rng`), which is **not** bit-identical to TPAW's ChaCha8
streams — see `simulation/market_data/bootstrap.py`'s `build_index_sequences`
docstring, which already notes "algorithmic parity, our own determinism." We
target **algorithmic** parity — the same formulas applied in the same
sequence — validated against TPAW's own published test/doctest values, not
bit-identical output against a running TPAW instance. Differences at the level
of floating-point rounding (float32 vs. float64) or RNG stream identity are
expected and are not treated as bugs.

## Testing approach: doctest-golden values

There is no runnable TPAW binary in this repo to diff full simulation runs
against, so correctness is validated in two layers:

1. **Unit goldens pinned to TPAW's own test cases.** The pure-math modules —
   `mertons.py` (plain/effective Merton's formula cases, `get_rra_for_all_stocks`),
   `risk.py` (risk-tolerance → RRA endpoints), `npv.py`
   (backward precomputation at start, target withdrawals with no
   ceiling/floor, stock allocation), and `withdrawals.py`
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

## Phase 3c-2 — planning-returns presets

Preset menu is at full tpaw parity: regression, conservative, 1/CAPE, historical,
fixed-equity-premium, custom, and fixed. Expected returns come from vendored v7 CAPE
regression + Shiller earnings, combined with live or vendored S&P 500 and 20-yr TIPS
yields (Phase 3c-1 feeds). Variance uses the vendored block-size table scaled by
`stock_volatility_scale²` — preset choice affects expected returns only, not variance
(tpaw behavior). An expected-return glide path over the simulation horizon is
intentionally absent: tpaw fixes planning returns at month 0; the RRA-based stock
allocation glide shipped in Phase 3b.

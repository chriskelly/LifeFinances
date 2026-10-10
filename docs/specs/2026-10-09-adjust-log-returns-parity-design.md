# Historical-returns adjustment for Monte Carlo sampling (TPAW parity)

**Status:** open design — delete when implemented (repo docs policy).
**Date:** 2026-10-09
**Related:** [issue #231](https://github.com/chriskelly/LifeFinances/issues/231) (horizon off-by-one, explicitly out of scope here).

## Context

`packages/simulation` is a Python port of TPAW's withdrawal engine. A parity comparison
against the live TPAW service (a TPAW plan mirroring LifeFinances plan 22, "Parity
Testing") showed LifeFinances projecting **higher spending and portfolio on every
percentile**, with the gap growing over the horizon.

## Evidence

Captured TPAW `/3/simulate` response for the equivalent plan:

```
historical_returns.stocks:
  args.empirical_annual_non_log_expected_return : 0.052      <- target
  src_annualized_stats.non_log.mean             : 0.087367   <- raw source
  stats.annualized.non_log.mean                 : 0.051999   <- adjusted result
historical_returns.bonds:
  src 0.027723  ->  adjusted 0.032201   (target 0.032)
annual_inflation: 0.024   num_runs: 500
returns_stats_for_planning.stocks: 0.052, log variance 0.03204234689
```

LifeFinances plan 22 resolves the same inputs (planning preset `regression_prediction`,
5.2% stocks / 3.2% bonds, variance `0.032042347`, inflation 2.4%, RRA bit-identical to
TPAW at `2.054085703094072`), and month-0 spending matches to 0.06% ($1101.1 vs $1100.4).
At mid-horizon (month 390) LF's median spending/balance are ~**1.29×** TPAW; applying
TPAW's adjustment locally brings LF to ~**1.04×** (≈85% of the gap closed across
percentiles).

## Root cause

TPAW does not simulate with raw historical returns. Before the Monte Carlo runs it
**rescales the vendored history so its expected annual non-log return equals the planning
(expected) return**, then feeds the adjusted series to the engine:

- `simulator-rust/.../process_plan_params_server/process_historical_returns.rs` calls
  `adjust_log_returns_detailed(...)`; the adjusted `non_log_series` is shipped to CUDA.
- `utils/return_series.rs::adjust_log_returns` + `historical_monthly_returns.rs::get_shift_correction`.
- `run_tpaw.cu` uses the adjusted returns for normal runs; the expected run uses planning returns.
- TPAW tests assert it (`adjust_log_returns_historical`, `adjust_log_returns_monte_carlo`).

LifeFinances omits this. `market_data/bootstrap.py::build_return_paths` indexes the raw
v8 log series (`hist.stocks_log[sequences]`), and `engine.py::simulate_monthly` applies
them directly. LF vendors only the per-block stock **variance**, not the per-block
**non-log mean** the shift correction needs (`PROVENANCE.md` notes this explicitly).

## Goals

- Monte Carlo sampled returns have expected annual non-log return equal to the planning
  target, for stocks and bonds.
- Match TPAW's adjustment exactly: block-size-specific shift correction and
  log-volatility scaling.
- Preserve the existing preset-menu correction behavior (`presets.py` goldens unchanged).

## Non-goals

- Horizon off-by-one (#231).
- RNG stream identity (TPAW ChaCha8/XORWOW vs NumPy) — algorithmic parity only.
- Percentile aggregation method (`numpy.percentile` linear vs TPAW's pick).
- Spending ceiling/floor (removed from this rebuild's product scope).

## Design

### 1. Data artifacts (mirror TPAW's layout)

TPAW keeps two separate files, one per asset, each combining mean + variance per block
(`EmpiricalStats32::new(annual_non_log_returns_mean, annual_log_returns_variance)`).
Mirror that:

- Replace `market_data/data/stock_log_variance_by_block.csv` with
  `market_data/data/stock_empirical_stats_by_block.csv`:
  columns `block_size, annual_non_log_returns_mean, annual_log_returns_variance`, rows 1..1440.
- Add `market_data/data/bond_empirical_stats_by_block.csv`: same columns.
- Extract from `v8_empirical_stats_by_block_size_{stocks,bonds}.rs` (index 0 dummy dropped).

Consumers to update (enumerated):

- `market_data/presets_data.py` — `_VARIANCE_TABLE_PATH` → the two new paths;
  `load_stock_log_variance_by_block` → `load_empirical_stats_by_block(asset)` (the stock
  planning variance reads the stock table's variance column). Not re-exported via
  `market_data/__init__.py`, so no package `__init__` change.
- `simulation/presets.py` — import + `stock_log_variance` reads the stock table.
- `tests/test_presets.py` — imports/uses `load_stock_log_variance_by_block`.
- `tests/tpaw_preset_contract.py` — `EXPECTED_STOCK_LOG_VARIANCE_BLOCK_1` /
  `..._BLOCK_1440` endpoint pins.
- `packages/simulation/README.md` (§Planning returns, `variance_by_block[...]`) and
  `packages/simulation/OVERVIEW.md`.
- `market_data/data/PROVENANCE.md` — the artifact section and bump-checklist step 3.
- `packages/core/tests/test_sampling_inflation_config.py` — comment referencing the
  `stock_log_variance` vendored bound.
- This spec.

### 2. Loaders (`market_data/presets_data.py`)

- `load_empirical_stats_by_block(asset)` → per-asset `dict[int, (mean, variance)]`.
- `presets.py::stock_log_variance` reads the stock table's variance column (behavior
  unchanged: `variance × stock_volatility_scale²`).

### 3. Adjustment math (`presets.py`, generalize existing helpers)

Port TPAW exactly. Let `series` be the monthly log-return array.

```
shift_correction(unadjusted_annual_non_log_mean, series_log_mean, scale):
    return (ln(1 + unadjusted_annual_non_log_mean)/12 - series_log_mean) * scale**2

adjust_log_returns(log_returns, target_annual_non_log, unadjusted_annual_non_log_mean, scale):
    correction = shift_correction(unadjusted_annual_non_log_mean, mean(log_returns), scale)
    target_monthly = ln(1 + target_annual_non_log)/12 - correction
    return target_monthly + (log_returns - mean(log_returns)) * scale
```

The existing `presets.py::_shift_correction` is the `block_size=None, scale=1` case
(`unadjusted` = the series' own annualized non-log mean); refactor it to call the
generalized helper so preset-menu behavior is unchanged.

**Load-bearing invariant:** `unadjusted_annual_non_log_mean` is the *per-block table
mean*, **not** the mean of the series being adjusted. The two differ materially at small
blocks (v8 block 1 = `0.0811` vs series `0.0874`) and only coincide to the 6th decimal at
block 60 — so a series-mean substitution is a silent bug at other block sizes. A test must
pin this at a non-default block size (see §Testing).

### 4. Sampling integration (`market_data/bootstrap.py`, `stub.py`)

- `build_return_paths` gains a **required** keyword `planning: PlanningReturns` (the
  resolved planning returns). Block size comes from `plan.sampling.block_size_months`;
  scales are `plan.planning_returns.stock_volatility_scale` (stocks) and `1.0` (bonds).
- It adjusts each series **before** indexing:
  - stocks: target = planning `annual_stocks`; `unadjusted` = stock block mean.
  - bonds: target = planning `annual_bonds`; `unadjusted` = bond block mean; scale `1.0`
    (TPAW's `historical_returns_adjustment.standard_deviation.bonds.scale.log` default;
    LF has no per-plan bond scale).
- Callers to update: `stub.run_simulation` (pass `processed.planning_resolved`),
  `tests/market_data/test_bootstrap.py` (3 calls), `tests/market_data/test_public_api.py`.
- `ReturnPaths.stocks_log`/`bonds_log` become the adjusted log series, so
  `stocks_log_to_simple()` yields the adjusted simple returns (matching TPAW's
  `non_log_series`).
- The deterministic expected run is unchanged (planning returns).

### 5. Testing (TDD)

No committed TPAW-response goldens or fixtures — the captured comparison is a one-time
manual check (§Verification). Tests assert behavior/properties using production constants:

- Mean: after `adjust_log_returns`, the adjusted series' annualized non-log mean ≈ target
  (±1e-3), mirroring TPAW's `adjust_log_returns_historical`.
- Scale: adjusted std = original std × `scale`, mirroring `test_adjust_log_returns_scale`.
- Block-size invariant: at a non-default block size (e.g. 1, where the per-block mean
  differs materially from the series mean), the adjusted log mean equals
  `ln(1+target)/12 − shift_correction(block_mean, series_log_mean, scale)` computed from the
  production table — fails if the series mean is substituted for the block mean.
- Integration: `build_return_paths`'s sampled series' annual non-log mean ≈ planning
  target; update `test_build_return_paths_gathers_both_assets_with_metadata` (it currently
  pins "sampled values are members of the raw series").
- `test_presets.py` goldens must stay green (preset-menu correction unchanged).

### 6. Docs / provenance

- `market_data/data/PROVENANCE.md`: update the artifact sections and the vN bump checklist
  (step 3 currently keeps only the stock variance and states the mean is not vendored).
- `packages/simulation/README.md` and `OVERVIEW.md`: describe the sampling adjustment and
  update the parity notes.

## Verification

The property/integration tests above, plus a **one-time manual check** against the captured
TPAW response (plan 22 vs `/3/simulate`): expect the mid-horizon median gap to fall from
~29% to within a few percent (RNG/float residual), and the sampled stocks/bonds annual
non-log means to equal 5.2% / 3.2%. No fixture or golden is committed. Run `make` from the
repo root.

## Risks / notes

- Removing `stock_log_variance_by_block.csv` touches the vN bump checklist and any test
  pins on that filename/endpoints.
- TPAW precomputes the block-size stats via a 500k-run bootstrap with a fixed seed; LF
  cannot reproduce it (different RNG), so the tables must be vendored verbatim.
- The adjustment is only *approximately* a no-op when target = the series' own mean (e.g.
  the `historical` preset): it is exact only when the per-block mean equals the series mean.
  TPAW does not special-case `historical`, so neither should we.

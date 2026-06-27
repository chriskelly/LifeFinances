# Phase 3a — Simulation: Market Data and Bootstrap Design

**Date:** 2026-06-25
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-25-phase-2e-domain-single-household-design.md](./2026-06-25-phase-2e-domain-single-household-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3a-simulation-market-data.md` *(to write after spec approval)*
**Follow-up:** Phase 3a+ — networked market-data acquisition (optional, deferred); Phase 3b — TPAW withdrawal core

---

## 1. Goal & scope

Stand up the stochastic foundation for the TPAW engine: a `simulation/market_data/`
subpackage that turns vendored historical **real** monthly returns into reproducible
block-bootstrapped monthly return paths (stocks + bonds), plus a resolved monthly
**inflation** rate. This is the raw stochastic input the Phase 3b withdrawal engine
will consume; Phase 3a does not run the withdrawal loop or aggregate results.

Phase 3a includes:

1. **Vendored historical return data** — tpaw v7 real monthly stock/bond returns,
   committed as CSV with provenance, loaded and converted to log returns in Python.
2. **Block-bootstrap sampler** — port of tpaw's staggered block-bootstrap algorithm,
   producing `(num_runs, months_per_run)` log-return paths per asset, deterministic
   under an injected seed.
3. **Scalar inflation resolution** — vendored FRED `T10YIE` (breakeven inflation)
   series with "latest at or before today" lookup for `suggested`, plus `manual`
   override; converted annual → monthly.
4. **Persisted config models** — `SamplingConfig` and `InflationConfig` on the `Plan`
   in `core`, with tpaw defaults; UI wiring deferred to Phase 4.
5. **Public simulation API** — `build_return_paths(...)` and `resolve_inflation(...)`.

Phase 3a does **not** include:

- The TPAW withdrawal loop, cashflow accounting, or rebalancing (Phase 3b).
- Mean/volatility return adjustment, CAPE regression, or empirical-stats-by-block-size
  (Phase 3c — planning expected returns/vol).
- Percentile aggregation or `SimulationResult` chart series (Phase 3d).
- Per-run bootstrapped inflation paths (interface left open; not implemented).
- tpaw's "historical" sequential sampling mode (Monte Carlo only for now).
- Live/networked market-data fetch (Phase 3a+ — see §10).
- Sampling/inflation editor UI (Phase 4).

---

## 2. Decisions captured from brainstorming

| #   | Decision                                                        | Rationale                                                                                                                          |
| --- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Real returns + scalar inflation (tpaw model)**               | tpaw's historical data is already inflation-adjusted (real); inflation is a single rate that converts nominal cashflows to real. Diverges from the rebuild-index "block-bootstrap inflation" criterion (see §9). |
| 2   | **Scalar now, paths-capable interface later**                  | No bootstrapped inflation paths in 3a, but the resolver interface is shaped so per-run paths can be added without changing callers. |
| 3   | **Port v7 only**                                               | One current dataset (effective Jan 2026); simplest. Timestamp-based multi-version selection (v1–v7) can be added later if needed.   |
| 4   | **Vendor raw CSV as source of truth, derive in Python**        | Smallest, most auditable footprint; mirrors tpaw's own derive-log-series-at-load pipeline. Empirical-stats/CAPE constants deferred to 3c. |
| 5   | **Monte Carlo block-bootstrap only**                           | tpaw default sampling mode. "Historical" sequential mode deferred.                                                                |
| 6   | **Raw resampling only (no return adjustment)**                 | 3a emits unadjusted real return paths; mean/vol adjustment is Phase 3c per the rebuild index.                                     |
| 7   | **Algorithmic parity, our own determinism**                    | Replicate tpaw's staggered block-bootstrap algorithm with a seeded numpy RNG. Reproducible for us; not bit-identical to tpaw's ChaCha8 sequences. |
| 8   | **numpy float64**                                              | Matches tpaw's f64 math; performant for 500 runs × hundreds of months × 2 assets. `Decimal` stays for money in `core`; returns/series are float. |
| 9   | **Config models on the `Plan` in `core`**                      | `SamplingConfig` / `InflationConfig` persisted with the plan, consistent with SS/job config already in core. Suggested-inflation resolved against vendored data inside simulation. |
| 10  | **Vendored `T10YIE` for suggested inflation**                  | Same indicator and selection rule as tpaw, without a live API. Networked acquisition deferred to Phase 3a+. |

---

## 3. Data vendoring & loading

### Source

tpaw v7 historical monthly returns:
`tpaw/packages/simulator-rust/src/lib/historical_monthly_returns/data/v7/v7_raw_data.csv`

- ~1,857 monthly rows, 1871-01 → 2025-09 (real, non-log returns).
- Columns: `year, month, CAPE, stock real return, bond real return`.
- Effective timestamp: `V7_HISTORICAL_MONTHLY_RETURNS_EFFECTIVE_TIMESTAMP_MS = 1768510800000`
  (Thursday, Jan 15, 2026).

### Vendored layout

```
packages/simulation/simulation/market_data/
├── __init__.py
├── data/
│   ├── v7_real_monthly_returns.csv      # vendored from tpaw v7_raw_data.csv
│   ├── t10yie_daily.csv                 # vendored FRED breakeven inflation
│   └── PROVENANCE.md                    # source, version, dates, attribution
├── returns.py                           # historical series load + log conversion
├── bootstrap.py                         # block-bootstrap sampler
└── inflation.py                         # suggested/manual resolution
```

### Loading behavior (`returns.py`)

- Parse the CSV once; drop the `CAPE` column (deferred to 3c).
- Convert real non-log returns to **log returns** via `ln(1 + r)`, mirroring tpaw's
  `process_raw_monthly_non_log_series`.
- Expose an immutable `HistoricalReturns` object:
  - `stocks_log: np.ndarray` (float64), `bonds_log: np.ndarray` (float64)
  - `start: (year, month)`, `length: int`
  - `effective_date` metadata (for traceability / future multi-version support).
- Module-level memoization so the CSV parses once per process.

### Faithful-port guard

A test asserts our parsed series matches tpaw's baked `.rs` array
(`V7_RAW_MONTHLY_NON_LOG_SERIES`) values within float tolerance, so the vendored CSV
is a verified faithful copy of tpaw's source. (Values exceed f32/f64 display precision
but round-trip to the same floats.)

---

## 4. Block-bootstrap sampler (`bootstrap.py`)

Port of tpaw's `generate_random_index_sequences` (`utils/random.rs`), preserving the
algorithm with a seeded numpy RNG.

### Algorithm

For each run, build a length-`months_per_run` sequence of indices into the historical
series:

1. Number of blocks per run: `months_per_run // block_size + 2` (one extra for the
   remainder, one extra for staggering).
2. Draw `num_blocks` random block-start months uniformly from `[0, length)`.
3. `stagger = run_index % block_size` if `stagger_run_starts` else `0`.
4. For month `i` in `0..months_per_run`:
   - `staggered_i = i + stagger`
   - `block_index = staggered_i // block_size`
   - `index = (block_start[block_index] + staggered_i % block_size) % length`

Staggering offsets block boundaries across runs so blocks don't all change at the same
month. The final `% length` wraps blocks that run off the end of the series.

### Inputs / output

```python
def build_return_paths(
    plan: Plan,
    *,
    months_per_run: int,
    today: date | None = None,
) -> ReturnPaths
```

- `months_per_run` = plan horizon in months (via existing
  `core.timeline.horizon_months`); the resolved value is passed in by the caller.
- `block_size`, `num_runs`, `stagger_run_starts`, `seed` come from `plan.sampling`.
- Index sequences are built once, then used to gather from both the stocks and bonds
  log series.

`ReturnPaths` (pydantic model, arrays as numpy via `arbitrary_types_allowed`):

- `stocks_log: np.ndarray` shape `(num_runs, months_per_run)`
- `bonds_log: np.ndarray` shape `(num_runs, months_per_run)`
- metadata: `seed`, `block_size`, `num_runs`, `months_per_run`

These are the inputs to Phase 3b's engine. (Log vs non-log handoff convention is fixed
in 3b; 3a exposes log returns plus a documented `exp_m1`-style accessor if the engine
prefers non-log.)

### Determinism

Same `seed` + same sampling params → identical paths. Different seed → different paths.
A fixed default seed lives on `SamplingConfig` so default plans are reproducible.

---

## 5. Inflation (`inflation.py`)

### Suggested (vendored `T10YIE`)

- Vendor a small daily `T10YIE` (10-Year Breakeven Inflation Rate) CSV from FRED,
  `date,value` where value is percent (e.g. `2.35` → `0.0235`).
- Resolution rule (matches tpaw `fget_item_at_or_before_key`): take the **latest
  observation at or before `today`**, parse percent → decimal annual rate, round to
  3 decimal places.
- Skip non-numeric rows (FRED occasionally emits `"."`), mirroring tpaw's
  `parse_percent_string` tolerance.

### Manual

- `InflationConfig.mode == "manual"` → use `manual_annual_rate` directly (no rounding
  beyond the stored Decimal).

### Annual → monthly

Convert with tpaw's formula (`annual_non_log_to_monthly_non_log_return_rate`):

```python
monthly = (1 + annual) ** (1 / 12) - 1
```

### API

```python
def resolve_inflation(plan: Plan, *, today: date | None = None) -> InflationResolved
```

`InflationResolved` carries `annual: float`, `monthly: float`, and `source`
(`"suggested" | "manual"`). Returns are real, so this scalar is only used downstream
to convert nominal domain cashflows into real terms (Phase 3b). The return type is a
single scalar today, but the function is the single seam where per-run inflation paths
could later be introduced without changing callers. Track evaluation in
[#186 — Evaluate per-run bootstrapped inflation paths](https://github.com/chriskelly/LifeFinances/issues/186).

---

## 6. Config models (in `core`)

Added to `core.models`, persisted on `Plan`, with tpaw defaults. Defaults ensure
existing plans and `data.db.blank` still load without migration.

### `SamplingConfig`

| Field                 | Type   | Default | Source / note                                  |
| --------------------- | ------ | ------- | ---------------------------------------------- |
| `block_size_months`   | int    | `60`    | tpaw `blockSize.inMonths = 12 * 5`             |
| `num_runs`            | int    | `500`   | tpaw `numOfSimulationForMonteCarloSampling`    |
| `stagger_run_starts`  | bool   | `True`  | tpaw `staggerRunStarts`                        |
| `seed`                | int    | fixed   | LifeFinances default for reproducibility       |

Validation: `block_size_months >= 1`, `num_runs >= 1`.

### `InflationConfig`

| Field                | Type                          | Default       | Note                          |
| -------------------- | ----------------------------- | ------------- | ----------------------------- |
| `mode`               | `Literal["suggested","manual"]` | `"suggested"` | tpaw default is suggested     |
| `manual_annual_rate` | `Decimal \| None`             | `None`        | required when `mode=="manual"` |

Validation: `manual_annual_rate` present (and ≥ some sane bound) when
`mode == "manual"`.

### `Plan` additions

```python
class Plan(BaseModel):
    ...
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    inflation: InflationConfig = Field(default_factory=InflationConfig)
```

Defaults via `default_factory` so deserializing older persisted plans fills new fields.

---

## 7. Public API (simulation package)

```python
# simulation/market_data/__init__.py re-exports
build_return_paths(plan, *, months_per_run, today=None) -> ReturnPaths
resolve_inflation(plan, *, today=None) -> InflationResolved
HistoricalReturns, ReturnPaths, InflationResolved  # types
```

`run_simulation` remains the Phase 1 stub in 3a; it is not yet wired to these
functions (that integration is Phase 3b). 3a delivers tested building blocks plus the
config they read.

Dependency direction unchanged: `simulation → domain, core`. New numpy dependency
added to the simulation package via `uv add` (not hand-edited into lockfiles).

---

## 8. Testing (TDD)

Test our logic, not numpy/pydantic behavior. Pull constants from source; avoid
duplicated literals across arrange/assert.

- **Historical load:** log conversion correctness on a tiny fixture; CSV faithful-port
  guard vs tpaw `V7_RAW_MONTHLY_NON_LOG_SERIES`.
- **Sampler:**
  - output shape `(num_runs, months_per_run)` for both assets;
  - determinism (same seed → identical; different seed → different);
  - block contiguity (within a block, indices are consecutive months mod length);
  - staggering offsets block boundaries across runs as specified;
  - all sampled values come from the source series (membership);
  - wrap-around at series end behaves (modulo length).
- **Inflation:**
  - suggested as-of lookup (before first / on / between / after last observation);
  - non-numeric row skipped;
  - rounding to 3 dp;
  - manual mode uses configured rate;
  - annual → monthly conversion pinned to the formula.
- **Config models:** defaults match tpaw constants (imported, not re-hardcoded);
  manual-rate validation; older-plan deserialization fills defaults.

---

## 9. Divergence from rebuild index

The Phase 3a exit criterion in the rebuild index reads:

> Inflation paths: bootstrap default + suggested/manual override

This design intentionally **replaces** "bootstrap default" with tpaw's actual model:
historical returns are real, and inflation is a single scalar (suggested breakeven or
manual) used to deflate nominal cashflows. There is no historical inflation series to
bootstrap in tpaw's v7 data. The rebuild index should be updated to:

> Inflation: scalar suggested (vendored breakeven) + manual override; bootstrapped
> inflation paths deferred (interface left open).

Per-run bootstrapped inflation remains possible later behind `resolve_inflation`
([#186](https://github.com/chriskelly/LifeFinances/issues/186)).

---

## 10. Phase 3a+ — networked market data (optional, deferred)

Captured now so it isn't lost; not part of Phase 3a and not blocking 3b.

| Field          | Value                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------- |
| **Goal**       | tpaw parity for suggested inflation, and groundwork for other live presets (bond yields, SP500/CAPE) |
| **Scope**      | Live FRED `T10YIE` fetch with caching + offline fallback to the vendored CSV; optional extension to Treasury real-yield and SP500 feeds |
| **Out of scope** | Full tpaw `MarketDataForPresets` surface (CAPE regression, expected-return presets) — stays in Phase 3c |
| **Entry**      | Phase 3a complete                                                                                  |
| **Exit**       | Suggested inflation auto-updates from network when configured; vendored CSV remains fallback; API key / offline behavior documented |

---

## 11. Out of scope (deferred summary)

- Mean/volatility adjustment, CAPE regression, empirical-stats-by-block-size → Phase 3c.
- Multi-version (v1–v6) data + timestamp selection → later if reproducibility needed.
- "Historical" sequential sampling mode → later.
- Bootstrapped inflation paths, live market-data feed → Phase 3a+ / beyond.
- Engine integration, percentile aggregation, chart series → Phase 3b / 3d.
- Sampling / inflation editor UI → Phase 4.

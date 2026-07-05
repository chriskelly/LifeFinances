# Phase 3c-2 — Simulation: Planning-Returns Presets Design

**Date:** 2026-07-05
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Depends on:** [2026-07-05-phase-3c-1-simulation-market-feeds-design.md](./2026-07-05-phase-3c-1-simulation-market-feeds-design.md)
**Builds on:** [2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md](./2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3c-2-simulation-planning-returns-presets.md` *(to write after spec approval)*

---

## 1. Goal & scope

Replace Phase 3b's fixed/manual planning-return numbers — the annual stock/bond expected
returns and stock log-variance that feed Merton's stock allocation and the PV of future
income — with **market-data-derived expected-return presets**, at **full tpaw parity**.

Phase 3b already delivered RRA / age glide, Merton's formula, PV precompute, amortization,
and total-portfolio allocation. **3c-2 only changes the *source* of the planning-return
inputs those formulas consume.** No engine math changes; `resolve_planning_returns` keeps
returning the same frozen `PlanningReturns(annual_stocks, annual_bonds,
annual_stock_log_variance)` shape.

Live inputs (S&P close, Treasury 20-yr TIPS yield) come from the Phase 3c-1 resolvers,
each with a vendored fallback. The preset math and its inert vendored constants
(regression coefficients, Shiller earnings, variance-by-block table) ship here.

### In scope

- Full-parity `PlanningReturnsConfig` model (preset menu + custom/fixed/fixed-equity-premium
  + user log-volatility scale).
- `presets.py` — pure preset math ported from tpaw
  (`process_market_data_for_presets` + `process_returns_stats_for_planning`).
- Vendored constants: `cape_regression_v7.json` (8 slope/intercept pairs + Shiller 10-yr
  avg real earnings), `stock_log_variance_by_block.csv`.
- `resolve_planning_returns` dispatch on the selected preset, consuming the 3c-1 resolvers.
- Web/CLI key injection for planning returns (pass `EOD_API_KEY` + `allow_refresh` on a
  real run), mirroring the 3a+ inflation wiring.
- `rebuild-index.md` correction (glide-path item, VT/BND dropped, bonds-via-TIPS delivered).

### Out of scope

- The rich preset-selection editor **UI** → Phase 4 (3a+ already deferred its editor;
  the masked API-key form already exposes `EOD_API_KEY`). 3c-2 ships model + resolution only.
- Any live-feed acquisition code → delivered in Phase 3c-1.
- Per-run bootstrapped inflation paths ([#186](https://github.com/chriskelly/LifeFinances/issues/186)).
- An expected-return glide path — **does not exist in tpaw** (see §7).

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Full tpaw preset parity** | Expose every tpaw preset type: regressionPrediction, conservativeEstimate, 1/CAPE, historical, fixedEquityPremium, custom, fixed. |
| 2 | **Default flips to `regression_prediction`** | tpaw's default (`regressionPrediction,20YearTIPSYield`). Vendored fallback guarantees it resolves offline; `"fixed"` preserves the 3b literal behavior. |
| 3 | **Vendor tpaw's v7 constants** | Copy the 8 slope/intercept pairs + Shiller 10-yr avg real earnings with attribution; compute the runtime prediction from the (live-or-vendored) S&P level. No offline OLS pipeline to reproduce. |
| 4 | **Vendor tpaw's variance-by-block-size table** | Look up variance by `SamplingConfig.block_size_months`; apply the user log-volatility scale². Exact parity, no 500k-run local precompute. |
| 5 | **`presets.py` is pure (no I/O)** | Takes resolved inputs (S&P close, TIPS curve, vendored constants, historical series); doctest-golden testable against tpaw's own values. |
| 6 | **`resolve_planning_returns` mirrors `resolve_inflation`** | Same seam: `allow_refresh`, `api_key`, injected fetchers/resolvers, `today`/`now`. `simulation` never reads secrets. |
| 7 | **`fixed` never touches the network** | Pure config path; only preset modes resolve S&P/TIPS. |
| 8 | **Drop the glide-path exit criterion** | tpaw fixes expected returns at month 0; the RRA stock-allocation glide already shipped in 3b. Correct the index. |
| 9 | **Bonds via 20-yr TIPS, not VT/BND** | Matches tpaw's default bond base; VT/BND never fed presets and are dropped in 3c-1. |

---

## 3. Config model (`core.models.PlanningReturnsConfig`)

```python
StockPresetBase = Literal["regression_prediction", "conservative_estimate", "one_over_cape", "historical"]
BondPresetBase  = Literal["twenty_year_tips_yield", "historical"]

class PlanningReturnsConfig(BaseModel):
    preset: Literal[
        "regression_prediction",   # regressionPrediction + 20yr TIPS  (tpaw default)
        "conservative_estimate",   # conservativeEstimate + 20yr TIPS
        "one_over_cape",           # 1/CAPE + 20yr TIPS
        "historical",              # historical stocks + historical bonds
        "fixed_equity_premium",    # bond base + fixed premium
        "custom",                  # chosen stock/bond bases + deltas
        "fixed",                   # literal returns (Phase 3b behavior)
    ] = "regression_prediction"

    fixed_equity_premium: Decimal | None = None        # required for "fixed_equity_premium"
    custom_stocks_base: StockPresetBase | None = None   # required for "custom"
    custom_bonds_base: BondPresetBase | None = None
    custom_stocks_delta: Decimal = Decimal(0)
    custom_bonds_delta: Decimal = Decimal(0)

    # "fixed" mode reuses the existing literal fields (back-compat with 3b)
    expected_annual_return_stocks: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS
    expected_annual_return_bonds: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS

    # user log-volatility scale (tpaw standardDeviation.stocks.scale.log; default 1.0)
    stock_volatility_scale: Decimal = Decimal(1)
```

Model validators enforce the per-mode required fields (`fixed_equity_premium` set when
`preset == "fixed_equity_premium"`; both `custom_*_base` set when `preset == "custom"`),
mirroring `InflationConfig._require_manual_rate`.

---

## 4. Preset math (`simulation/presets.py`, pure functions)

Direct port of tpaw's `process_market_data_for_presets` (stock/bond estimates) and
`process_returns_stats_for_planning` (preset selection). All functions take already-resolved
inputs, so the module is I/O-free.

```python
@dataclass(frozen=True)
class RegressionCoeffs:
    # 8 (slope, intercept) pairs: {full, restricted} x {5, 10, 20, 30} year
    pairs: tuple[tuple[float, float], ...]

def one_over_cape(*, sp500_close: float, shiller_10yr_real_earnings: float) -> float:
    return shiller_10yr_real_earnings / sp500_close

def regression_predictions(one_over_cape: float, coeffs: RegressionCoeffs) -> list[float]:
    # per pair: annual_log = slope*ln(1 + one_over_cape) + intercept
    #           annual non-log via shift-corrected exp(12*(mu_month + corr)) - 1, round_p(3)

def regression_prediction(one_over_cape: float, coeffs: RegressionCoeffs) -> float:
    # mean of the 8 regression values

def conservative_estimate(one_over_cape: float, coeffs: RegressionCoeffs) -> float:
    # mean of the 4 lowest of (one_over_cape + the 8 regression values)

def historical_stock_return(stocks_log: np.ndarray) -> float   # annual non-log of series mean
def historical_bond_return(bonds_log: np.ndarray) -> float

def stock_log_variance(*, block_size_months: int, table: VarianceByBlock, volatility_scale: float) -> float
    # vendored table lookup x scale**2
```

Log→non-log conversion mirrors tpaw's
`get_empirical_annual_non_log_from_log_monthly_expected_value` (shift-corrected
`exp(12·(μ_monthly + correction)) − 1`, `round_p(3)` rounding). Reuse the existing
`load_historical_returns()` series for the historical presets.

### Vendored constants

```
packages/simulation/simulation/market_data/data/
  cape_regression_v7.json          # { "effective_date", "shiller_10yr_real_earnings",
                                    #   "pairs": [[slope, intercept] x8], "provenance": ... }
  stock_log_variance_by_block.csv  # block_months, annual_log_variance  (tpaw table 1..1440)
  PROVENANCE.md                    # extend with tpaw v7 attribution for both files
```

---

## 5. Resolution (`simulation/planning_returns.py`)

`resolve_planning_returns` gains the 3a+ seam and dispatches on the selected preset:

```python
def resolve_planning_returns(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    eod_api_key: str | None = None,
    sp500_resolver: ... = resolve_latest_sp500_close,     # from 3c-1
    treasury_resolver: ... = resolve_treasury_real_yields, # from 3c-1
) -> PlanningReturns: ...
```

| preset | stocks | bonds |
| ------ | ------ | ----- |
| `regression_prediction` | regressionPrediction | 20yr TIPS |
| `conservative_estimate` | conservativeEstimate | 20yr TIPS |
| `one_over_cape` | 1/CAPE | 20yr TIPS |
| `historical` | historical | historical |
| `fixed_equity_premium` | 20yr TIPS + `fixed_equity_premium` | 20yr TIPS |
| `custom` | `custom_stocks_base` + `custom_stocks_delta` | `custom_bonds_base` + `custom_bonds_delta` |
| `fixed` | `expected_annual_return_stocks` | `expected_annual_return_bonds` |

- `fixed` short-circuits: no resolver calls, pure config (Phase 3b behavior preserved).
- All other modes resolve the S&P close and/or TIPS curve via the 3c-1 resolvers (each with
  its own vendored fallback), then apply the pure `presets.py` math.
- `annual_stock_log_variance` **always** comes from the vendored block-size table keyed by
  `plan.sampling.block_size_months`, scaled by `stock_volatility_scale²` — replacing the
  current `np.var(stocks_log) × 12` estimate.

The returned `PlanningReturns` dataclass is unchanged, so `preprocess.py`/`engine.py` are
untouched downstream.

---

## 6. Integration & wiring

- **Engine/preprocess:** `resolve_planning_returns` is already the single call site feeding
  Merton/PV. Only its internals + signature grow; the frozen return type is stable.
- **Web/CLI boundary:** on a real run the web layer loads `EOD_API_KEY` (and `FRED_API_KEY`)
  from `SettingsRepository` and passes them + `allow_refresh=True` into the resolvers;
  `simulation` never reads the DB. The 3a+ masked settings form already exposes the EOD field.
- **Index correction:** update `rebuild-index.md` Phase 3c exit criteria — remove/reword the
  glide-path item, note VT/BND dropped, mark bonds-via-TIPS delivered, and reflect the 3c-1 /
  3c-2 two-PR split.

---

## 7. Note: no expected-return glide path

The rebuild index listed *"stock-allocation glide path derived from the live preset feed."*
tpaw fixes planning expected returns at **month 0** for the whole horizon (Rust sets
`expected_return_change = 0.0`); the only thing that glides is the **RRA-based stock
allocation**, already delivered in Phase 3b. This criterion is dropped and the index
corrected. No expected-return glide is implemented.

---

## 8. Testing strategy (TDD, network-free)

| Unit | Test |
| ---- | ---- |
| `presets.one_over_cape` / `regression_*` / `conservative_estimate` | Doctest-golden values pinned to tpaw's own published preset outputs for a known S&P close + vendored v7 coeffs. |
| `presets.historical_*` | Annual non-log conversion of the vendored v7 series mean matches tpaw. |
| `presets.stock_log_variance` | Table lookup by block size × scale²; constants imported from source, not copied. |
| `PlanningReturnsConfig` validators | Per-mode required fields enforced (custom bases, fixed premium); `fixed` back-compat defaults. |
| `resolve_planning_returns` dispatch | Each preset returns the correct stock/bond pair; `fixed` calls no resolver (spy); preset modes call resolvers; variance from table × scale². |
| Fallback | Injected 3c-1 resolvers returning vendored values → resolution still succeeds offline. |

Constants (defaults, RRA scale, variance table) imported from production code. CI never
passes `allow_refresh=True` to a real fetcher.

---

## 9. PR boundary

3c-2 depends on 3c-1's resolvers. It is the second of the two Phase 3c PRs:

1. **3c-1** — feeds (S&P + Treasury), caches, vendored snapshots, CLI. Additive, unconsumed.
2. **3c-2** — this PR: preset math, config, resolution, wiring, index correction.

---

## 10. Exit criteria

- [ ] `PlanningReturnsConfig` supports the full tpaw preset menu; default `regression_prediction`;
      `fixed` preserves 3b behavior; validators enforce per-mode fields.
- [ ] `presets.py` ports tpaw's stock/bond estimates + variance lookup as pure functions,
      pinned by doctest-golden tests to tpaw's published values.
- [ ] Vendored `cape_regression_v7.json` + `stock_log_variance_by_block.csv` committed with provenance.
- [ ] `resolve_planning_returns` dispatches per preset, consuming the 3c-1 resolvers with
      vendored fallback; `fixed` never touches the network.
- [ ] Variance from the vendored block-size table × `stock_volatility_scale²`, replacing `var×12`.
- [ ] Web/CLI inject `EOD_API_KEY` + `allow_refresh` on real runs; `simulation` reads no secrets.
- [ ] `rebuild-index.md` corrected (glide-path dropped, VT/BND dropped, bonds-via-TIPS delivered,
      two-PR split noted); `make` passes.

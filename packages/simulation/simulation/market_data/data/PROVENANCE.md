# Market data provenance

## Bump historical-returns version (TPAW → LifeFinances)

When live TPAW ships a new `vN` historical-returns bundle (Shiller earnings + CAPE
regressions + monthly returns + block-size variance), update the three vendored
artifacts below. This is **not** covered by `scripts/refresh_market_data.py`
(that script only refreshes T10YIE / S&P / Treasury).

Prerequisite: read sources from `tpaw` at the commit that introduced `vN`
(usually `origin/main`).

1. **Monthly returns CSV** — copy
   `tpaw/.../data/vN/vN_raw_data.csv` verbatim (keep the UTF-8 BOM) to
   `vN_real_monthly_returns.csv`. Delete the previous `v*_real_monthly_returns.csv`.
2. **CAPE regression JSON** — extract the eight `(slope, intercept)` pairs from
   `vN_annual_log_mean_from_one_over_cape_regression_info_stocks.rs` into keys
   `full_5`…`restricted_30` (full then restricted, each 5/10/20/30). Take the
   **latest** entry from `average_annual_real_earnings_for_sp500_for_10_years.rs`
   for `shiller_10yr_real_earnings`, `shiller_window`, and
   `effective_timestamp_ms`. Write `cape_regression_vN.json` (same schema as the
   previous file). Delete the previous `cape_regression_v*.json`.
3. **Stock log-variance table** — parse
   `vN_empirical_stats_by_block_size_stocks.rs` (`EmpiricalStats32::new(mean,
   variance)`); keep the **variance** (2nd arg); **drop index 0**; write
   `stock_log_variance_by_block.csv` with rows `block_size` 1..1440.
4. **Loaders** — point `returns.py` (`_DEFAULT_RETURNS_CSV`, effective-date
   constant) and `presets_data.py` (`_CAPE_REGRESSION_PATH`) at the new filenames.
5. **Docs** — update this file’s artifact sections, plus `packages/simulation/README.md`
   and `OVERVIEW.md` version wording.
6. **Tests** — rebase `test_returns.py` length/first/last pins,
   `tpaw_preset_contract.py` goldens (including Shiller earnings and variance
   table endpoints), and any Sep-4-style parity smoke
   (`stock_estimates(sp500_close=…)` vs live TPAW guide numbers).
7. Run `make` from the repo root.

Do **not** vendor `vN_raw_cape_series.json`, bond variance, or the Rust monthly
non-log array (the CSV is LifeFinances’ source of truth; `ln(1+r)` happens at load).

## v8_real_monthly_returns.csv

- **Source:** TPAW (`tpaw/packages/simulator-rust/src/lib/historical_monthly_returns/data/v8/v8_raw_data.csv`).
- **Version:** v8 (effective Monday, Jul 27, 2026; tpaw `V8_HISTORICAL_MONTHLY_RETURNS_EFFECTIVE_TIMESTAMP_MS = 1785191400000`).
- **Coverage:** 1863 monthly rows, 1871-01 → 2026-03.
- **Columns:** `year, month, CAPE, stock real return, bond real return`. Returns are
  **real** (inflation-adjusted), **non-log**. `CAPE` is unused at load time
  (regression presets use live S&P + vendored Shiller earnings).
- **Transformations:** none at vendor time (copied verbatim, including the UTF-8 BOM).
  Log conversion `ln(1 + r)` happens at load (`returns.py`), mirroring tpaw's
  `process_raw_monthly_non_log_series`.
- **Attribution:** TPAW by Ben Mathew (https://tpawplanner.com), underlying data
  derived from Robert Shiller's dataset.

## t10yie_daily.csv

- **Source:** FRED series `T10YIE` (10-Year Breakeven Inflation Rate),
  https://fred.stlouisfed.org/series/T10YIE — downloaded from the public CSV endpoint
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10YIE`.
- **Downloaded:** 2026-07-06.
- **Columns:** first column is the observation date (`YYYY-MM-DD`), second column is the
  breakeven rate in **percent** (e.g. `2.35`). Missing observations appear as `.`.
- **Use:** "suggested" inflation = latest observation at or before `today`, parsed
  percent → decimal, rounded to 3 dp (mirrors tpaw `T10YIE` handling).

## sp500_close.csv

- **Source:** EOD Historical Data (EODHD) `GSPC.INDX` daily `close`
  (https://eodhistoricaldata.com/api/eod/GSPC.INDX). Used unadjusted (price, for CAPE).
- **Seeded:** 2026-07-06
- **Columns:** `observation_date` (`YYYY-MM-DD`), `close` (index level).
- **Use:** latest close at or before `today` feeds the 1/CAPE regression presets.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (requires the EOD API key configured in Settings).

## treasury_real_yield.csv

- **Source:** U.S. Treasury daily TIPS real-yield curve
  (https://home.treasury.gov/.../daily-treasury-rates.csv, `daily_treasury_real_yield_curve`).
- **Seeded:** 2026-07-06
- **Columns:** `observation_date` (`YYYY-MM-DD`), `5,7,10,20,30` real yields as **decimals**
  (e.g. `0.0217` = 2.17%).
- **Use:** latest curve at or before `today`; the 20-yr yield is the bond preset.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (no API key required).

## cape_regression_v8.json

- **Source:** TPAW simulator-rust v8 historical-returns bundle:
  `v8_annual_log_mean_from_one_over_cape_regression_info_stocks.rs` (8 slope/intercept
  pairs) and `average_annual_real_earnings_for_sp500_for_10_years.rs` (latest entry,
  `added_date_ms = 1785191400000`).
- **Version:** v8 (effective 2026-07-27), the same release as `v8_real_monthly_returns.csv`.
- **Contents:** OLS coefficients predicting annual log stock return from `ln(1 + 1/CAPE)`
  for {full, restricted} × {5, 10, 20, 30}-year forward windows, plus the 10-year average
  real S&P 500 earnings used to reconstruct `1/CAPE = earnings / price`
  (`shiller_10yr_real_earnings = 184.43`, window 2016-04 → 2026-03).
- **Use:** `regression_prediction` / `conservative_estimate` / `1/CAPE` presets.
- **Attribution:** TPAW by Ben Mathew (https://tpawplanner.com); earnings from Robert Shiller's dataset.

## stock_log_variance_by_block.csv

- **Source:** TPAW simulator-rust `v8_empirical_stats_by_block_size_stocks.rs`
  (`annual_log_returns_variance` column; `annual_non_log_returns_mean` not vendored).
- **Version:** v8 (effective 2026-07-27).
- **Generation (upstream):** 500,000-run block-bootstrap, 600 months/run, staggered
  starts, fixed seed — precomputed by tpaw, copied verbatim (index 0 dummy dropped).
- **Columns:** `block_size` (1..1440 months), `annual_log_returns_variance`.
- **Use:** planning stock variance = `table[sampling.block_size_months] × stock_volatility_scale²`.
- **Attribution:** TPAW by Ben Mathew (https://tpawplanner.com).

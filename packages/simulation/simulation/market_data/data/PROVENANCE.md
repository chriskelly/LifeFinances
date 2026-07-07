# Market data provenance

## v7_real_monthly_returns.csv

- **Source:** TPAW (`tpaw/packages/simulator-rust/src/lib/historical_monthly_returns/data/v7/v7_raw_data.csv`).
- **Version:** v7 (effective Thursday, Jan 15, 2026; tpaw `V7_HISTORICAL_MONTHLY_RETURNS_EFFECTIVE_TIMESTAMP_MS = 1768510800000`).
- **Coverage:** 1857 monthly rows, 1871-01 → 2025-09.
- **Columns:** `year, month, CAPE, stock real return, bond real return`. Returns are
  **real** (inflation-adjusted), **non-log**. `CAPE` is unused in Phase 3a (deferred to 3c).
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
- **Use:** latest close at or before `today` feeds the Phase 3c-2 1/CAPE regression presets.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (requires the EOD API key configured in Settings).

## treasury_real_yield.csv

- **Source:** U.S. Treasury daily TIPS real-yield curve
  (https://home.treasury.gov/.../daily-treasury-rates.csv, `daily_treasury_real_yield_curve`).
- **Seeded:** 2026-07-06
- **Columns:** `observation_date` (`YYYY-MM-DD`), `5,7,10,20,30` real yields as **decimals**
  (e.g. `0.0217` = 2.17%).
- **Use:** latest curve at or before `today`; the 20-yr yield is the Phase 3c-2 bond preset.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (no API key required).

## cape_regression_v7.json

- **Source:** TPAW simulator-rust v7 historical-returns bundle:
  `v7_annual_log_mean_from_one_over_cape_regression_info_stocks.rs` (8 slope/intercept
  pairs) and `average_annual_real_earnings_for_sp500_for_10_years.rs` (latest entry,
  `added_date_ms = 1768510800000`).
- **Version:** v7 (effective 2026-01-15), the same release as `v7_real_monthly_returns.csv`.
- **Contents:** OLS coefficients predicting annual log stock return from `ln(1 + 1/CAPE)`
  for {full, restricted} × {5, 10, 20, 30}-year forward windows, plus the 10-year average
  real S&P 500 earnings used to reconstruct `1/CAPE = earnings / price`.
- **Use:** Phase 3c-2 `regression_prediction` / `conservative_estimate` / `1/CAPE` presets.
- **Attribution:** TPAW by Ben Mathew (https://tpawplanner.com); earnings from Robert Shiller's dataset.

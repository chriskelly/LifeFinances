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
- **Downloaded:** 2026-06-27.
- **Columns:** first column is the observation date (`YYYY-MM-DD`), second column is the
  breakeven rate in **percent** (e.g. `2.35`). Missing observations appear as `.`.
- **Use:** "suggested" inflation = latest observation at or before `today`, parsed
  percent → decimal, rounded to 3 dp (mirrors tpaw `T10YIE` handling).

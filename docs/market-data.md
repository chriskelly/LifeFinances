# Market data refresh

Scope: the manual refresh script, cache locations, vendored fallbacks, and the
TPAW data version checklist. Read before refreshing market data or changing
vendored series.

Manual market-data fetch for suggested inflation (FRED `T10YIE`), S&P 500 close
(EOD `GSPC.INDX`), and Treasury TIPS real yields. API keys are read from
`AppSettings` in the local SQLite DB (enter them in the app Settings UI, or use
`--db-path` to point at another DB). Treasury needs no key. No `.env` is
consulted.

```bash
# Warm the gitignored T10YIE cache (30-day lookback) — default when no source flags
uv run python scripts/refresh_market_data.py

# Warm a single source
uv run python scripts/refresh_market_data.py --only sp500
uv run python scripts/refresh_market_data.py --only treasury

# Warm every source
uv run python scripts/refresh_market_data.py --all

# Use a specific database
uv run python scripts/refresh_market_data.py --db-path data/data.db

# Maintainer: full-series fetch → rewrite committed vendored CSV
uv run python scripts/refresh_market_data.py --update-vendored
uv run python scripts/refresh_market_data.py --all --update-vendored
```

Treasury `--update-vendored` loops years from 2003 through the current year (the
Treasury API is year-scoped). S&P `--update-vendored` uses a long `from` date
(1990-01-01).

Default cache output: `data/market_cache/t10yie_daily.csv` (+ sidecar metadata).
S&P and Treasury caches live alongside it (`sp500_close.csv`,
`treasury_real_yield.csv`). Each cache file is written to a temporary file in the
same directory and moved into place, so an interrupted refresh leaves the
previous file intact. Vendored fallbacks are under
`packages/simulation/simulation/market_data/data/`; update
`packages/simulation/simulation/market_data/data/PROVENANCE.md` before committing
vendored data changes. T10YIE / S&P / Treasury refreshes are
`scripts/refresh_market_data.py`; TPAW historical-returns version bumps (CAPE
regression, Shiller earnings, monthly returns, per-asset empirical stats — mean
and variance for stocks and bonds) follow that file's checklist — they are not
covered by the refresh script.

Exit codes: `0` success, `1` no usable observations, `2` required API key not
configured in Settings.

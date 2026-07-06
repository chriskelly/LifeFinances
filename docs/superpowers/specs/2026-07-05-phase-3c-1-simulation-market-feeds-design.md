# Phase 3c-1 — Simulation: Networked S&P + Treasury Feeds Design

**Date:** 2026-07-05
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-28-phase-3a-plus-networked-market-data-design.md](./2026-06-28-phase-3a-plus-networked-market-data-design.md)
**Sibling:** [2026-07-05-phase-3c-2-simulation-planning-returns-presets-design.md](./2026-07-05-phase-3c-2-simulation-planning-returns-presets-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3c-1-simulation-market-feeds.md` *(to write after spec approval)*

---

## 1. Goal & scope

Add **best-effort live refresh** for the two market-data series that the Phase 3c-2
expected-return presets consume, using the exact 3a+ pattern already validated for
inflation (FRED `T10YIE`):

1. **S&P 500 price level** — EOD `GSPC.INDX` daily close (bring-your-own `EOD_API_KEY`).
2. **Treasury real-yield curve** — the daily TIPS real-yield curve (5/7/10/20/30-yr) from
   the public `home.treasury.gov` CSV (no key required).

This PR is **purely additive data acquisition**: it ships the fetchers, caches, vendored
snapshots, resolver functions, and CLI cache-warming, but **nothing consumes them yet**.
The consumer (planning-returns presets) lands in Phase 3c-2. This mirrors how Phase 3a
shipped market data + bootstrap before Phase 3b consumed them.

The vendored snapshots are the guaranteed offline fallback; live data only ever *improves*
freshness. The simulation never depends on the network.

### In scope

- Generalize the `fetch.py` HTTP seam (currently FRED-only) so multiple sources share the
  guarded opener and `UrlOpener` protocol.
- `eod_gspc_close(...)` fetcher — EOD API → normalized `(date, close)` rows.
- `treasury_real_yield_curve(...)` fetcher — Treasury CSV → normalized `(date, {tenor: yield})` rows.
- `sp500.py` / `treasury.py` resolvers — cache-or-vendored read ladder + opt-in
  fail-silent refresh, returning the *latest* usable close / TIPS curve.
- Vendored snapshots: `sp500_close.csv`, `treasury_real_yield.csv` + `PROVENANCE.md` entries.
- Generalized cache (`cache.py`) — per-source CSV + `.meta.json` sidecar, 24h TTL.
- `scripts/refresh_market_data.py` — warm the two new caches; `--update-vendored` for the
  two new snapshots.

### Out of scope (Phase 3c-2)

- Any preset math, CAPE/regression, variance table, or `PlanningReturnsConfig` change.
- `resolve_planning_returns` wiring / web key injection for planning returns.
- The inert vendored constants (regression coeffs, Shiller earnings, variance-by-block
  table) — those ship with the math that uses them.

### Out of scope (dropped)

- `VT.US` / `BND.US` feeds. In tpaw these feed only live *current-portfolio-balance*
  estimation, which LifeFinances does not do (savings are entered manually). They add no
  preset value and are dropped from the rebuild scope.

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **Reuse the 3a+ best-effort ladder verbatim** | Cache-or-vendored read always runs; refresh only when `allow_refresh` + (key if required) + stale. Offline-safe by construction. |
| 2 | **One source module per feed** (`sp500.py`, `treasury.py`) | Isolated units, each independently testable with an injected fetcher; matches `inflation.py`. |
| 3 | **Generalize `fetch.py`, don't fork it** | Extract the shared guarded opener / `UrlOpener`; add per-source fetchers. Single SSL/trust seam. |
| 4 | **Treasury feed needs no key** | Public CSV. Refresh gates on `allow_refresh` + stale only; EOD additionally requires `EOD_API_KEY`. |
| 5 | **Canonical internal format = CSV** | Normalize foreign formats (EOD JSON, Treasury CSV) at the fetch boundary; one reader shape for cache and vendored, as in 3a+. |
| 6 | **Ship additive, unconsumed** | 3c-1 is safe to merge alone; `main` stays green with the feeds present but unused. |
| 7 | **Drop VT/BND** | They never feed presets; LifeFinances has no live portfolio-balance estimation. |
| 8 | **`EOD_API_KEY` reuses the existing `AppSettings` field** | Added in 3a+; the settings form already exposes it. No `core` change needed here. |

---

## 3. Components

```
packages/simulation/simulation/market_data/
  fetch.py        # EXISTING — extract shared opener/UrlOpener; add EOD + Treasury fetchers
  cache.py        # EXISTING — generalize write/TTL/read-path helpers to per-source paths
  sp500.py        # NEW — resolve_latest_sp500_close(...) : EOD → cache → vendored
  treasury.py     # NEW — resolve_treasury_real_yields(...) : Treasury CSV → cache → vendored
  data/
    sp500_close.csv           # NEW vendored snapshot (observation_date, close)
    treasury_real_yield.csv   # NEW vendored snapshot (observation_date, y5, y7, y10, y20, y30)
    PROVENANCE.md             # EXISTING — add EOD + Treasury source rows

data/market_cache/            # gitignored — new live targets
  sp500_close.csv + sp500_close.meta.json
  treasury_real_yield.csv + treasury_real_yield.meta.json

scripts/refresh_market_data.py  # EXISTING — warm the two new caches; --update-vendored path
```

### `fetch.py` generalization

- Promote `_default_opener` + `UrlOpener` + the response protocols to shared, reusable
  helpers (they are already source-agnostic).
- Add `eod_gspc_close(*, api_key, from_date, timeout_seconds=10.0, opener=_default_opener)
  -> list[tuple[date, Decimal]]`
  - Endpoint: `https://eodhistoricaldata.com/api/eod/GSPC.INDX` with
    `api_token`, `fmt=json`, `order=a`, `from=<lookback>`.
  - Reads `date` + `close` (unadjusted — CAPE uses price, not total return).
  - Skips unparseable rows; raises a typed error on transport/HTTP/JSON failure; returns
    `[]` on an API error body (mirrors `parse_fred_observations`).
- Add `treasury_real_yield_curve(*, year, timeout_seconds=10.0, opener=_default_opener)
  -> list[tuple[date, dict[str, Decimal]]]`
  - Endpoint: `https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/<year>/all?type=daily_treasury_real_yield_curve&field_tdr_date_value=<year>`.
  - Parses the CSV header to the `{5,7,10,20,30}`-yr TIPS columns; normalizes percent →
    decimal (`value / 100`) with `Decimal` precision preserved.
  - No `api_key` parameter (public data).

Both fetchers are pure wire→rows: no disk access, no fallback logic.

### `cache.py` generalization

The 3a+ helpers are already parameterized by path; 3c-1 makes the source-specific pieces
(header row, series id) parameters rather than T10YIE constants, or adds thin per-source
wrappers. Requirements:

- `write_cache(rows, *, now, cache_path, meta_path, source, header)` — CSV in the same
  column shape the resolver reads, plus sidecar `{fetched_at, source, series_id/source_id}`.
- `resolve_read_path(*, cache_path, vendored_path)` — cache if present, else vendored (unchanged).
- `is_cache_stale(*, now, meta_path, ttl=CACHE_TTL)` — unchanged 24h TTL logic.

The existing T10YIE call sites keep working (either via the generalized signature with
T10YIE defaults, or a thin `t10yie`-named wrapper — implementer's choice, no behavior change).

### `sp500.py` — latest close resolver

```python
@dataclass(frozen=True)
class SP500Resolved:
    close: float
    observation_date: date
    source: Literal["live", "cache", "vendored"]

def resolve_latest_sp500_close(
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    api_key: str | None = None,
    fetcher: EodCloseFetcher = eod_gspc_close,
    cache_path: Path = DEFAULT_SP500_CACHE_PATH,
    meta_path: Path = DEFAULT_SP500_META_PATH,
    vendored_path: Path = DEFAULT_SP500_VENDORED_PATH,
    lookback_days: int = LOOKBACK_DAYS,
) -> SP500Resolved: ...
```

- Refresh trigger (all required): `allow_refresh` **and** `api_key` **and** cache stale.
- Read ladder (always): cache CSV if present → vendored CSV.
- Returns the **latest row at or before `today`** (reuse the `_suggested_annual` "latest
  observation" pattern from `inflation.py`).

### `treasury.py` — TIPS curve resolver

```python
@dataclass(frozen=True)
class TreasuryYieldsResolved:
    yields: dict[str, float]        # {"5": .., "7": .., "10": .., "20": .., "30": ..}
    observation_date: date
    source: Literal["live", "cache", "vendored"]

def resolve_treasury_real_yields(
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fetcher: TreasuryFetcher = treasury_real_yield_curve,
    cache_path: Path = DEFAULT_TREASURY_CACHE_PATH,
    meta_path: Path = DEFAULT_TREASURY_META_PATH,
    vendored_path: Path = DEFAULT_TREASURY_VENDORED_PATH,
) -> TreasuryYieldsResolved: ...
```

- Refresh trigger: `allow_refresh` **and** cache stale (no key). The Treasury fetch uses
  the current year for `observation_start`.
- Same read ladder + latest-row selection as S&P.

---

## 4. Control flow (both feeds, identical to 3a+)

```
resolve_latest_sp500_close(*, today, allow_refresh=False, now=None, api_key=None, fetcher=...)
├─ if allow_refresh and api_key and cache.is_stale(now):
│     try:
│         rows = fetcher(api_key=api_key, from_date=today - lookback)   # short timeout
│         cache.write(rows, now=now, source="eod_api")
│     except Exception:
│         pass                                              # best-effort; log a warning
└─ path = cache.resolve_read_path()                        # cache if present, else vendored
   return latest row at/before today

resolve_treasury_real_yields(...)  # same, minus the api_key gate
```

Any failure — no key, timeout, SSL, HTTP error, malformed payload, empty rows — is
swallowed; control falls through to the read ladder. Neither resolver ever blocks or
raises on network trouble.

---

## 5. Manual refresh command

`scripts/refresh_market_data.py` gains the two new sources alongside T10YIE:

```bash
# Warm all gitignored caches (T10YIE + S&P + Treasury); loud on failure.
uv run python scripts/refresh_market_data.py

# Maintainer: rewrite the committed vendored snapshots from a full/long fetch.
uv run python scripts/refresh_market_data.py --update-vendored
```

- The EOD key is loaded from `SettingsRepository` (same DB the app uses); Treasury needs none.
- Auto path uses the 30-day (S&P) / current-year (Treasury) lookback; `--update-vendored`
  fetches a longer history and rewrites `data/.../sp500_close.csv` and
  `treasury_real_yield.csv`, printing a diff summary and a `PROVENANCE.md` reminder.
- `--update-vendored` is a maintainer action; never run in CI or tests.

---

## 6. Testing strategy (TDD, network-free)

The network boundary is **injected**, so no HTTP and no monkeypatching.

| Unit | Test |
| ---- | ---- |
| `fetch.eod_gspc_close` parser | Canned EOD JSON → `(date, close)` rows; bad rows skipped; API-error body → `[]`. |
| `fetch.treasury_real_yield_curve` parser | Canned Treasury CSV → per-tenor decimals; missing/`""` cells skipped; percent→decimal. |
| `cache` generalization | Rows → cache CSV round-trips through the resolver reader; sidecar has `fetched_at`/`source`; TTL boundary uses `CACHE_TTL` imported from source. |
| `sp500.resolve_latest_sp500_close` | Gating: `allow_refresh=False` **or** `api_key=None` → fetcher spy never called. Cache present → cache close; absent → vendored. Fetch raises → vendored, no exception. Latest-at-or-before-`today` selection. |
| `treasury.resolve_treasury_real_yields` | Gating: `allow_refresh=False` → fetcher never called (no key gate). Cache/vendored ladder; failure swallow; 20yr present in result. |

**Not tested in CI:** the live EOD/Treasury calls and `--update-vendored`. Documented as
manual/maintainer actions. Tests use injected fakes and never pass `allow_refresh=True` to
a real fetcher.

---

## 7. Dependencies

**No new package dependencies.** Reuse `urllib` + the guarded `truststore` dev-only import
already in `fetch.py`. `EOD_API_KEY` already exists on `AppSettings` (3a+); no `core`
change here. Vendored snapshots live under
`packages/simulation/simulation/market_data/data/` (committed); live caches under the
gitignored `data/market_cache/`.

---

## 8. Exit criteria

- [ ] `fetch.py` exposes a shared opener + `eod_gspc_close` + `treasury_real_yield_curve`
      fetchers (pure wire→rows, typed failures, injected opener).
- [ ] `sp500.resolve_latest_sp500_close` and `treasury.resolve_treasury_real_yields`
      implement the cache→vendored ladder with opt-in fail-silent refresh.
- [ ] Vendored `sp500_close.csv` + `treasury_real_yield.csv` committed with `PROVENANCE.md`.
- [ ] `scripts/refresh_market_data.py` warms the two new caches; `--update-vendored` rewrites
      the snapshots.
- [ ] All tests network-free (injected fetchers); CI never passes `allow_refresh=True` to a
      real fetcher.
- [ ] Purely additive: no existing behavior changes; `make` passes.

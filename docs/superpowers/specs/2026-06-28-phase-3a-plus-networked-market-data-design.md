# Phase 3a+ — Simulation: Networked Market Data Design

**Date:** 2026-06-28
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-25-phase-3a-simulation-market-data-design.md](./2026-06-25-phase-3a-simulation-market-data-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-3a-plus-networked-market-data.md` *(to write after spec approval)*
**Follow-up:** Phase 3c — live SP500/EOD presets and Treasury bond-yield feed

---

## 1. Goal & scope

Add **best-effort live refresh** of the suggested-inflation series (FRED `T10YIE`) on
top of the Phase 3a vendored pipeline, achieving tpaw parity for inflation acquisition
without ever making the simulation depend on the network. The vendored CSV shipped in
Phase 3a remains the guaranteed fallback; live data only ever *improves* freshness.

Phase 3a+ is **optional** and does **not** block Phase 3b. It is a self-contained
enhancement to `simulation/market_data/`.

Phase 3a+ includes:

1. **FRED JSON API fetch client** — official, versioned `series/observations` endpoint
   (requires `FRED_API_KEY`), 30-day `observation_start` lookback, short timeout.
2. **On-disk cache** — gitignored CSV (same shape as the vendored file) plus a sidecar
   metadata JSON (`fetched_at`, `source`, `series_id`) for TTL/provenance.
3. **Best-effort auto-refresh** — `resolve_inflation` gains opt-in, fail-silent refresh
   that the app/sim enables and tests never do.
4. **Manual refresh command** — a real, tested CLI replacing the throwaway PoC, with a
   `--update-vendored` maintainer mode that rewrites the committed CSV from a full-series
   fetch.

Phase 3a+ does **not** include:

- Live SP500 / EOD equity data or CAPE presets (Phase 3c).
- A fully wired Treasury real-yield cache/fallback (Phase 3c; PoC smoke test only).
- Per-run bootstrapped inflation paths ([#186](https://github.com/chriskelly/LifeFinances/issues/186)).
- Any change to the bootstrap sampler or the scalar-inflation resolution math.

---

## 2. Decisions captured from brainstorming

| #   | Decision                                                   | Rationale                                                                                                                                       |
| --- | ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Hybrid best-effort refresh**                             | Live fetch is attempted lazily but never blocks: stale cache or vendored is used immediately on any failure/timeout. Simulation stays offline-safe. |
| 2   | **Cache = per-series CSV + sidecar, gitignored**           | Reuses the Phase 3a CSV reader unchanged; fallback is pure path selection. TTL/provenance live in a small `.meta.json` sidecar, not the data.   |
| 3   | **FRED JSON API as the live source (`FRED_API_KEY` required)** | Official, documented, versioned endpoint chosen over the keyless graph CSV for **endpoint robustness**. tpaw parity is a bonus. Vendored CSV covers the no-key case. |
| 4   | **Cache stored as CSV, not JSON**                          | Normalize foreign formats at the fetch boundary; keep one canonical internal representation. The resolver keeps a single (CSV) reader for both cache and vendored. |
| 5   | **Refresh gated by explicit `allow_refresh` flag**         | CI is hermetic by construction: the test suite never passes `allow_refresh=True`, so no env scrubbing is needed even when a dev has a key set.  |
| 6   | **TTL gates *attempting* a refresh, never cache usability**| A stale cache is still newer than vendored, so it is always preferred on read. TTL (24h) only decides whether to try the network.               |
| 7   | **Network boundary injected into `resolve_inflation`**     | A `fetcher` parameter (defaulting to the real one) lets tests pass a fake — no HTTP, no monkeypatching, fully offline tests.                    |
| 8   | **Manual command with `--update-vendored` maintainer mode**| Folds the PoC into a tested entrypoint. Auto path uses 30-day lookback; vendored update uses a full-series fetch + `PROVENANCE.md` bump.        |
| 9   | **`truststore` stays a guarded dev-only import**           | Optional best-effort feature; a missing `truststore` just degrades to vendored fallback on affected macOS builds. No new runtime dep.           |
| 10  | **Treasury real-yield deferred to Phase 3c**               | It feeds bond-return presets, not inflation. PoC smoke test de-risks 3c; full cache/fallback wiring is YAGNI for 3a+.                           |

---

## 3. Components

New code stays inside the existing `simulation/market_data/` subpackage. Fetching
(network, foreign formats) is kept separate from resolving (the Phase 3a scalar logic).

```
packages/simulation/simulation/market_data/
  inflation.py        # EXISTING — resolve_inflation(), _suggested_annual() (CSV reader)
  fetch.py            # NEW — FRED JSON API client; JSON → list[(date, Decimal)]
  cache.py            # NEW — cache CSV write, TTL/freshness, sidecar metadata, path selection
  data/
    t10yie_daily.csv  # EXISTING vendored fallback (committed)

data/market_cache/                  # NEW, gitignored — live refresh target
  t10yie_daily.csv                  # cache, identical shape to vendored
  t10yie_daily.meta.json            # sidecar: { fetched_at, source, series_id }

scripts/refresh_market_data.py      # NEW — manual refresh CLI (replaces fetch_t10yie_poc.py)
```

### `fetch.py` — wire → pairs

- Owns the single FRED JSON API request (`series_id=T10YIE`, `file_type=json`,
  `observation_start` lookback, `Cache-Control: no-cache`, short timeout).
- Reads `FRED_API_KEY` from the environment.
- Applies the guarded `truststore` import (macOS SSL) exactly as the PoC does.
- Returns normalized `list[tuple[date, Decimal]]`; skips unparseable rows (the `"."`
  holiday value, e.g. `2023-05-29`). Raises a typed error on transport/HTTP/JSON failure.
- No disk access, no fallback logic — pure wire→pairs.

### `cache.py` — canonical store

- `write(pairs, *, now, source)` — emits the cache CSV in the **same column shape as the
  vendored file** (so the Phase 3a reader round-trips it) and writes the sidecar
  (`fetched_at = now`, `source`, `series_id`).
- `is_stale(*, now, ttl)` — compares sidecar `fetched_at` to `now`; missing cache/sidecar
  counts as stale.
- `resolve_read_path()` — returns the cache CSV if it exists, else the vendored CSV.
- TTL default is a module constant (`CACHE_TTL = timedelta(hours=24)`), imported by tests.

### `inflation.py` — minimal additions

- `resolve_inflation` gains `allow_refresh: bool = False`, `now: datetime | None = None`,
  and an injected `fetcher` (defaulting to `fetch.fred_observations`).
- `_suggested_annual` and the manual-mode path are **unchanged**; only the read path now
  selects between cache and vendored via `cache.resolve_read_path()`.

---

## 4. Control flow

```
resolve_inflation(plan, *, today, allow_refresh=False, now=None, fetcher=...)
├─ manual mode → return configured rate                       (UNCHANGED)
└─ suggested mode
   ├─ if allow_refresh and FRED_API_KEY set and cache.is_stale(now):
   │     try:
   │         pairs = fetcher(observation_start=...)            # short timeout
   │         cache.write(pairs, now=now, source="fred_api")
   │     except Exception:
   │         pass                                              # best-effort; log a warning
   └─ path  = cache.resolve_read_path()                       # cache if present, else vendored
      annual = _suggested_annual(today, path)                 # EXISTING reader
      return InflationResolved(annual, monthly, source="suggested")
```

### Refresh trigger (all three required)

1. `allow_refresh=True` (app/sim passes this; tests never do), **and**
2. `FRED_API_KEY` is set, **and**
3. cache is stale (sidecar `fetched_at` older than `CACHE_TTL`).

### Read ladder (always runs)

1. cache CSV exists → use it (**even if stale**).
2. else → vendored CSV (Phase 3a, always present).

Any fetch failure — no key, timeout, SSL, HTTP error, malformed JSON, empty
observations — is swallowed; control falls through to the read ladder. The simulation
never blocks and never raises on network trouble.

---

## 5. Manual refresh command

`scripts/refresh_market_data.py` promotes the PoC into a tested entrypoint with two modes:

```bash
# Warm the gitignored cache (30-day lookback); loud on failure, prints provenance.
uv run python scripts/refresh_market_data.py

# Maintainer mode: full-series fetch → rewrite the committed vendored CSV.
uv run python scripts/refresh_market_data.py --update-vendored
```

Differences from the auto path:

| | Auto (`allow_refresh=True`) | Manual command | `--update-vendored` |
| --- | --- | --- | --- |
| Trigger | Lazy, on stale cache during a sim | On demand | On demand (maintainer) |
| Lookback | 30 days | 30 days | Full series (no/early `observation_start`) |
| Target | `data/market_cache/…csv` | `data/market_cache/…csv` | committed `…/data/t10yie_daily.csv` |
| Failure | Silent → fallback | Loud, non-zero exit | Loud, non-zero exit |
| Output | None | Provenance + resolved rate | Diff summary + `PROVENANCE.md` reminder |

`--update-vendored` is a **maintainer action**: it touches a committed file, should print
a diff summary ("N new observations since last vendored date"), and reminds the user to
bump the `PROVENANCE.md` download date. It is never run in CI or tests.

The existing `scripts/fetch_t10yie_poc.py` is retired (folded into this command).

---

## 6. Testing strategy

All tests are network-free and follow TDD. The network boundary is **injected**, so no
HTTP and no monkeypatching is required.

| Unit | Test |
| --- | --- |
| `fetch.py` JSON→pairs parser | Canned FRED JSON (incl. the `"."` holiday value) → normalized pairs, bad rows skipped. |
| `cache.py` write | Pairs → cache CSV round-trips through the existing reader; sidecar has `fetched_at`/`source`/`series_id`. |
| `cache.py` TTL | Injected `now`; stale-vs-fresh boundary using `CACHE_TTL` imported from source (not copied). |
| `cache.py` read path | cache present → cache wins; cache absent → vendored. |
| `resolve_inflation` gating | `allow_refresh=False` (default) → fetcher (a spy) is **never** called; manual mode unchanged. |
| Refresh failure swallow | Injected fetcher raises → resolve still returns the vendored value, no exception. |

**Not tested in CI:** the live FRED call and `--update-vendored`. Documented as
manual/maintainer actions in `AGENTS.md` and `PROVENANCE.md`.

---

## 7. Dependencies

`truststore` stays a **guarded, dev-only import** (`try: import truststore;
truststore.inject_into_ssl() except ImportError: pass`). The refresh feature is opt-in
and best-effort; a missing `truststore` on some macOS builds simply degrades to the
vendored fallback — the designed behavior. No new runtime dependency is added.

`FRED_API_KEY` is read from the environment (or a local gitignored `.env`); never stored
in SQLite, never committed, never required in CI.

---

## 8. Out of scope (deferred)

- Live SP500 / EOD equity data, CAPE regression, expected-return presets → Phase 3c.
- Fully wired Treasury real-yield cache/fallback → Phase 3c (PoC smoke test only here).
- Per-run bootstrapped inflation paths → [#186](https://github.com/chriskelly/LifeFinances/issues/186).
- Sampling / inflation editor UI → Phase 4.

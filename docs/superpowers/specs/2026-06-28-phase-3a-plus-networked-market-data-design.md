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
5. **DB-backed API keys + minimal settings UI** — a singleton `AppSettings` row in
   SQLite holds the FRED key (and a placeholder for the Phase 3c EOD key); a small
   masked web form lets the user enter it without touching the filesystem.

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
| 11  | **API keys in a singleton `AppSettings` DB row, not `.env`**| The DB is the existing gitignored personal asset; a local-only app shouldn't push users to the filesystem. Keys enter through a UI form, travel with the DB, and stay off the `Plan` (no per-plan duplication, never in plan export/import). Same row holds `EOD_API_KEY` in Phase 3c. |
| 12  | **Keys injected at the web/CLI boundary, not read by `simulation`**| `simulation` never reaches into the DB for secrets. The web layer / CLI loads the key from the repository and passes it in, mirroring the injected-`fetcher` seam and keeping package boundaries clean. |
| 13  | **Minimal masked settings form ships in 3a+**              | Closes the UX gap so live refresh is usable without SQL or scripts; the full advanced editor remains Phase 4. Values render masked (`••••••••`) and are never echoed back in HTML. |

---

## 3. Components

Market-data code stays inside the existing `simulation/market_data/` subpackage; secrets
live in `core` (model + repository) and `web` (settings form). Fetching (network, foreign
formats) is kept separate from resolving (the Phase 3a scalar logic), and `simulation`
never reads secrets — the key is injected at the web/CLI boundary.

```
packages/core/core/
  models.py           # EXISTING — add AppSettings (singleton settings model)
  settings_repository.py  # NEW — load/save the singleton AppSettings row

packages/simulation/simulation/market_data/
  inflation.py        # EXISTING — resolve_inflation(), _suggested_annual() (CSV reader)
  fetch.py            # NEW — FRED JSON API client; JSON → list[(date, Decimal)]
  cache.py            # NEW — cache CSV write, TTL/freshness, sidecar metadata, path selection
  data/
    t10yie_daily.csv  # EXISTING vendored fallback (committed)

packages/web/web/
  sections.py         # EXISTING — add SETTINGS title constant
  forms.py            # EXISTING — add AppSettingsForm (masked key field)
  routes.py           # EXISTING — add PLAN_SETTINGS route
  templates/…         # NEW editor_settings.html partial

data/market_cache/                  # NEW, gitignored — live refresh target
  t10yie_daily.csv                  # cache, identical shape to vendored
  t10yie_daily.meta.json            # sidecar: { fetched_at, source, series_id }

scripts/create_blank_db.py          # EXISTING — add app_settings table to SCHEMA
scripts/refresh_market_data.py      # NEW — manual refresh CLI (replaces fetch_t10yie_poc.py)
```

### `AppSettings` — DB-backed secrets

API keys are **not** read from the environment or a `.env` file. They live in a
**singleton row** in SQLite (the existing gitignored `data/data.db`), separate from any
`Plan`:

- **Model** — `core.models.AppSettings` (Pydantic): `fred_api_key: str | None = None`,
  `eod_api_key: str | None = None` (the latter unused until Phase 3c). Blank strings
  normalize to `None`.
- **Schema** — `scripts/create_blank_db.py` gains an `app_settings` table with a single
  pinned row (`id INTEGER PRIMARY KEY CHECK (id = 1)`), columns nullable, **always empty
  in the committed `data.db.blank`**. The blank DB is regenerated; no real keys committed.
- **Repository** — `core.settings_repository.SettingsRepository` mirrors `PlanRepository`
  (constructed with an optional `db_path`): `get() -> AppSettings` (returns defaults when
  the row is empty) and `save(settings)`.

Why not on `Plan`: keys would duplicate across named plans (Phase 4), behave
inconsistently per plan, and leak into plan export / YAML import. Global app settings are
entered once and excluded from plan I/O.

### `fetch.py` — wire → pairs

- Owns the single FRED JSON API request (`series_id=T10YIE`, `file_type=json`,
  `observation_start` lookback, `Cache-Control: no-cache`, short timeout).
- Receives the API key as a **parameter** (`api_key: str`); it does not read the DB or the
  environment itself. The caller (web / CLI) loads it from `SettingsRepository`.
- Applies the guarded `truststore` import (macOS SSL) exactly as the PoC does.
- Returns normalized `list[tuple[date, Decimal]]`; skips unparseable rows (the `"."`
  holiday value, e.g. `2023-05-29`). Raises a typed error on transport/HTTP/JSON failure.
- No disk access, no fallback logic — pure wire→pairs.

### Web settings form (minimal)

- A small `editor_settings.html` partial with a masked password input for the FRED key,
  `PATCH`ing a new `PLAN_SETTINGS` route, following the existing section-form pattern
  (`forms.py` DTO → `apply_to` → `SettingsRepository.save`).
- The current value is **never** echoed into HTML; the field renders empty with a
  placeholder like `•••• set ••••` when a key is stored, and saving blank leaves the
  stored key unchanged (explicit "clear" affordance to remove it).
- This is the only UI in 3a+; the full advanced editor stays Phase 4.

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
  an optional `api_key: str | None = None`, and an injected `fetcher` (defaulting to the
  real `fetch.fred_observations`).
- `_suggested_annual` and the manual-mode path are **unchanged**; only the read path now
  selects between cache and vendored via `cache.resolve_read_path()`.
- `simulation` does not load `AppSettings`; the caller passes `api_key` in. The web layer
  reads it from `SettingsRepository` and forwards it on a real run.

---

## 4. Control flow

```
# web/CLI boundary:
#   settings = SettingsRepository(db_path).get()
#   resolve_inflation(plan, today=…, allow_refresh=True, api_key=settings.fred_api_key)

resolve_inflation(plan, *, today, allow_refresh=False, now=None, api_key=None, fetcher=...)
├─ manual mode → return configured rate                       (UNCHANGED)
└─ suggested mode
   ├─ if allow_refresh and api_key and cache.is_stale(now):
   │     try:
   │         pairs = fetcher(api_key=api_key, observation_start=...)   # short timeout
   │         cache.write(pairs, now=now, source="fred_api")
   │     except Exception:
   │         pass                                              # best-effort; log a warning
   └─ path  = cache.resolve_read_path()                       # cache if present, else vendored
      annual = _suggested_annual(today, path)                 # EXISTING reader
      return InflationResolved(annual, monthly, source="suggested")
```

### Refresh trigger (all three required)

1. `allow_refresh=True` (app/CLI passes this; tests never do), **and**
2. `api_key` is non-empty (loaded from `AppSettings` by the caller), **and**
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

The CLI loads the FRED key from `SettingsRepository` (the same DB the app uses); no
environment variable or `.env` is consulted.

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
| `resolve_inflation` gating | `allow_refresh=False` (default) **or** `api_key=None` → fetcher (a spy) is **never** called; manual mode unchanged. |
| `AppSettings` model | Blank key strings normalize to `None`; round-trips through Pydantic. |
| `SettingsRepository` | `save` then `get` round-trips keys against a temp DB (repo-root `db_path` fixture); empty row → defaults. |
| Web settings form | `PATCH` saves the key via the repository; response never contains the stored key value (masked). |
| Refresh failure swallow | Injected fetcher raises → resolve still returns the vendored value, no exception. |

**Not tested in CI:** the live FRED call and `--update-vendored`. Documented as
manual/maintainer actions in `AGENTS.md` and `PROVENANCE.md`. Tests use a temp DB with no
keys and never pass `allow_refresh=True` to a real fetcher.

---

## 7. Dependencies

**No new package dependencies.** Secrets use the existing `sqlite3` + Pydantic stack;
there is no `python-dotenv`.

`truststore` stays a **guarded, dev-only import** (`try: import truststore;
truststore.inject_into_ssl() except ImportError: pass`). The refresh feature is opt-in
and best-effort; a missing `truststore` on some macOS builds simply degrades to the
vendored fallback — the designed behavior. No new runtime dependency in `simulation`.

API keys live in a singleton `AppSettings` row in the gitignored `data/data.db`; the
committed `data.db.blank` carries the empty `app_settings` table only. Keys never appear
in plan JSON, plan export/import, git, or CI.

---

## 8. Out of scope (deferred)

- Live SP500 / EOD equity data, CAPE regression, expected-return presets → Phase 3c
  (reuses the `AppSettings.eod_api_key` field added here).
- Fully wired Treasury real-yield cache/fallback → Phase 3c (PoC smoke test only here).
- Per-run bootstrapped inflation paths → [#186](https://github.com/chriskelly/LifeFinances/issues/186).
- Sampling / inflation editor UI and the **full** advanced settings section → Phase 4
  (3a+ ships only the minimal masked API-key form).

---

## 9. Schema change note

The `app_settings` table is additive. Regenerate the committed blank DB after editing
`scripts/create_blank_db.py`:

```bash
uv run python scripts/create_blank_db.py   # rewrites data/data.db.blank (empty app_settings)
```

Existing personal `data/data.db` files predating 3a+ need the new table; the
implementation plan covers a tiny idempotent `CREATE TABLE IF NOT EXISTS` applied on
`SettingsRepository` access (or a one-line migration in `init_db.py`) so older DBs keep
working without losing plan data.

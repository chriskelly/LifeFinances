# Phase 3c-1 — Networked S&P + Treasury Feeds Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add best-effort live refresh of the S&P 500 price level (EOD `GSPC.INDX`) and the Treasury TIPS real-yield curve, each with a gitignored cache + committed vendored fallback, so Phase 3c-2's expected-return presets have a data source that stays fully offline-safe.

**Architecture:** Reuse the Phase 3a+ inflation pattern verbatim — pure wire→rows fetchers in `fetch.py` (injected `opener`), a canonical CSV cache with a `.meta.json` TTL sidecar in `cache.py`, and per-source resolver modules (`sp500.py`, `treasury.py`) that run a cache→vendored read ladder plus an opt-in, fail-silent refresh. Nothing consumes these feeds yet; this PR is purely additive.

**Tech Stack:** Python 3.14, `urllib` (+ guarded `truststore`), `csv`/`json`/`Decimal` stdlib, pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-07-05-phase-3c-1-simulation-market-feeds-design.md`

---

## Testing policy (AGENTS.md)

Every task follows the same TDD loop. **Do not skip the scaffolding step or commit on a structural failure.**

| Step | Action | Expected failure / outcome |
| ---- | ------ | -------------------------- |
| 1 | Write failing test(s) | — |
| 2 | Run test | **Structural** (`ImportError`, `AttributeError`, `ModuleNotFoundError`) |
| 3 | Add minimal scaffolding (`NotImplementedError`, stub return) | — |
| 4 | Run test | **Logical** (`AssertionError`, `NotImplementedError`) — required before implementing |
| 5 | Implement behavior | — |
| 6 | Run test | PASS |
| 7 | Commit | — |

**Rules applied in every test block below:**

- **One behavior per test** — name tests after behavior (`test_refresh_does_not_call_fetcher_without_api_key`), not methods.
- **No fragile values** — bind a shared literal once (arrange) and reference it in assert; never duplicate the same number/string in both places.
- **Pull constants from source** — import `EOD_SP500_SYMBOL`, `TREASURY_TENORS`, `CACHE_TTL`, `DEFAULT_*_VENDORED_PATH`, etc. from production modules; do not copy drift-prone literals.
- **Inject clocks and dependencies** — pass explicit `today=` / `now=`; inject fetcher/opener spies; never assert against wall-clock time.
- **Test our logic only** — no Pydantic/trivial `isinstance` checks; no tests that only prove a dataclass exists.

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| `packages/simulation/simulation/market_data/fetch.py` | MODIFY — add EOD + Treasury fetchers/parsers beside the existing FRED client, reusing the shared `_default_opener`/`UrlOpener`. |
| `packages/simulation/simulation/market_data/cache.py` | MODIFY — add generic read-path/staleness names + S&P/Treasury cache writers and default paths (existing T10YIE names kept as aliases). |
| `packages/simulation/simulation/market_data/sp500.py` | CREATE — `resolve_latest_sp500_close` (cache→vendored + refresh). |
| `packages/simulation/simulation/market_data/treasury.py` | CREATE — `resolve_treasury_real_yields` (cache→vendored + refresh). |
| `packages/simulation/simulation/market_data/data/sp500_close.csv` | CREATE — vendored S&P close snapshot. |
| `packages/simulation/simulation/market_data/data/treasury_real_yield.csv` | CREATE — vendored TIPS real-yield snapshot. |
| `packages/simulation/simulation/market_data/data/PROVENANCE.md` | MODIFY — add EOD + Treasury source entries. |
| `packages/simulation/simulation/market_data/__init__.py` | MODIFY — export the two resolvers + result dataclasses. |
| `scripts/refresh_market_data.py` | MODIFY — warm the two new caches; extend `--update-vendored`. |
| `packages/simulation/tests/market_data/test_fetch.py` | MODIFY — parser + request tests for both fetchers. |
| `packages/simulation/tests/market_data/test_cache.py` | MODIFY — S&P/Treasury cache writer tests. |
| `packages/simulation/tests/market_data/test_sp500.py` | CREATE — resolver tests. |
| `packages/simulation/tests/market_data/test_treasury.py` | CREATE — resolver tests. |
| `tests/test_refresh_market_data.py` | MODIFY — extend the existing repo-root CLI test with S&P/Treasury cases. |

---

## Task 1: EOD `GSPC.INDX` close fetcher

**Files:**
- Modify: `packages/simulation/simulation/market_data/fetch.py`
- Test: `packages/simulation/tests/market_data/test_fetch.py`

- [ ] **Step 1: Write the failing parser + request tests**

Append to `packages/simulation/tests/market_data/test_fetch.py`:

```python
def test_parse_eod_close_reads_close_and_skips_bad_rows() -> None:
    from simulation.market_data.fetch import parse_eod_close

    good_date = date(2026, 1, 2)
    good_close = Decimal("4700.10")
    skipped_date = date(2026, 1, 5)
    second_good_date = date(2026, 1, 6)
    second_good_close = Decimal("4725.50")
    payload = json.dumps(
        [
            {"date": good_date.isoformat(), "close": float(good_close), "adjusted_close": float(good_close)},
            {"date": skipped_date.isoformat(), "close": "bad", "adjusted_close": 4725.50},
            {"date": second_good_date.isoformat(), "close": float(second_good_close), "adjusted_close": float(second_good_close)},
        ]
    )

    pairs = parse_eod_close(payload)

    assert pairs == [
        (good_date, good_close),
        (second_good_date, second_good_close),
    ]


def test_eod_gspc_close_builds_request() -> None:
    from simulation.market_data.fetch import EOD_SP500_SYMBOL, eod_gspc_close

    captured: dict[str, object] = {}
    expected_key = "eod-request-key"
    from_date = date(2026, 1, 1)
    observed = date(2026, 1, 2)
    expected_close = Decimal("4700.10")
    payload = json.dumps(
        [{"date": observed.isoformat(), "close": float(expected_close), "adjusted_close": float(expected_close)}]
    )

    def opener(request: Request, timeout: float):
        captured["url"] = request.full_url
        return _FakeResponse(payload)

    pairs = eod_gspc_close(api_key=expected_key, from_date=from_date, opener=opener)

    assert pairs == [(observed, expected_close)]
    assert EOD_SP500_SYMBOL in str(captured["url"])
    assert f"api_token={expected_key}" in str(captured["url"])
    assert "fmt=json" in str(captured["url"])
    assert f"from={from_date.isoformat()}" in str(captured["url"])
```

- [ ] **Step 2: Run tests — expect structural failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "eod" -v`
Expected: FAIL with `ImportError` / `cannot import name 'parse_eod_close'`.

- [ ] **Step 3: Add minimal scaffolding**

Add stubs to `fetch.py` so imports resolve but logic is absent:

```python
EOD_BASE_URL = "https://eodhistoricaldata.com/api/eod"
EOD_SP500_SYMBOL = "GSPC.INDX"


def parse_eod_close(payload: str) -> list[tuple[date, Decimal]]:
    raise NotImplementedError


def eod_gspc_close(*, api_key: str, from_date: date, timeout_seconds: float = 10.0, opener: UrlOpener = _default_opener) -> list[tuple[date, Decimal]]:
    raise NotImplementedError
```

- [ ] **Step 4: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "eod" -v`
Expected: FAIL with `NotImplementedError` (not structural).

- [ ] **Step 5: Implement the EOD fetcher**

Add to `packages/simulation/simulation/market_data/fetch.py` (after the FRED code):

```python
EOD_BASE_URL = "https://eodhistoricaldata.com/api/eod"
EOD_SP500_SYMBOL = "GSPC.INDX"


def parse_eod_close(payload: str) -> list[tuple[date, Decimal]]:
    try:
        rows = json.loads(payload)
    except json.JSONDecodeError:
        logger.exception("EOD %s response was not valid JSON", EOD_SP500_SYMBOL)
        raise

    if not isinstance(rows, list):
        logger.warning("EOD %s response was not a JSON array", EOD_SP500_SYMBOL)
        return []

    pairs: list[tuple[date, Decimal]] = []
    for row in rows:
        try:
            observed = date.fromisoformat(row["date"])
            close = Decimal(str(row["close"]))
        except (KeyError, TypeError, ValueError, InvalidOperation):
            continue
        pairs.append((observed, close))
    return pairs


def eod_gspc_close(
    *,
    api_key: str,
    from_date: date,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, Decimal]]:
    params = {
        "api_token": api_key,
        "fmt": "json",
        "period": "d",
        "order": "a",
        "from": from_date.isoformat(),
    }
    request = Request(
        f"{EOD_BASE_URL}/{EOD_SP500_SYMBOL}?{urlencode(params)}",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with opener(request, timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        pairs = parse_eod_close(payload)
    except Exception:
        logger.exception("EOD %s fetch failed", EOD_SP500_SYMBOL)
        raise

    if not pairs:
        logger.warning("EOD %s fetch returned no usable rows", EOD_SP500_SYMBOL)
    return pairs
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "eod" -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/fetch.py packages/simulation/tests/market_data/test_fetch.py
git commit -m "feat(simulation): add EOD GSPC.INDX close fetcher"
```

---

## Task 2: Treasury real-yield-curve fetcher

**Files:**
- Modify: `packages/simulation/simulation/market_data/fetch.py`
- Test: `packages/simulation/tests/market_data/test_fetch.py`

- [ ] **Step 1: Write the failing parser + request tests**

Append to `packages/simulation/tests/market_data/test_fetch.py`:

```python
def test_parse_treasury_real_yields_normalizes_percent_to_decimal() -> None:
    from simulation.market_data.fetch import parse_treasury_real_yields

    observed = date(2026, 1, 2)
    # Percent strings from Treasury CSV → decimal yields keyed by tenor.
    percent_by_tenor = {"5": "1.85", "7": "1.90", "10": "1.95", "20": "2.05", "30": "2.15"}
    csv_text = "\n".join(
        [
            'Date,"5 YR","7 YR","10 YR","20 YR","30 YR"',
            f"01/02/2026,{percent_by_tenor['5']},{percent_by_tenor['7']},{percent_by_tenor['10']},{percent_by_tenor['20']},{percent_by_tenor['30']}",
        ]
    )

    rows = parse_treasury_real_yields(csv_text)

    expected_yields = {
        tenor: Decimal(value) / Decimal(100) for tenor, value in percent_by_tenor.items()
    }
    assert rows == [(observed, expected_yields)]


def test_parse_treasury_real_yields_skips_blank_cells() -> None:
    from simulation.market_data.fetch import parse_treasury_real_yields

    observed = date(2026, 1, 2)
    twenty_yr_percent = "2.05"
    csv_text = "\n".join(
        [
            'Date,"5 YR","7 YR","10 YR","20 YR","30 YR"',
            f"01/02/2026,1.85,1.90,1.95,{twenty_yr_percent},",
        ]
    )

    rows = parse_treasury_real_yields(csv_text)

    assert rows[0][0] == observed
    assert rows[0][1]["20"] == Decimal(twenty_yr_percent) / Decimal(100)
    assert "30" not in rows[0][1]


def test_treasury_real_yield_curve_builds_request() -> None:
    from simulation.market_data.fetch import (
        TREASURY_REAL_YIELD_TYPE,
        treasury_real_yield_curve,
    )

    captured: dict[str, object] = {}
    year = 2026
    observed = date(2026, 1, 2)
    csv_text = "\n".join(
        [
            'Date,"5 YR","7 YR","10 YR","20 YR","30 YR"',
            "01/02/2026,1.85,1.90,1.95,2.05,2.15",
        ]
    )

    def opener(request: Request, timeout: float):
        captured["url"] = request.full_url
        return _FakeResponse(csv_text)

    rows = treasury_real_yield_curve(year=year, opener=opener)

    assert rows[0][0] == observed
    assert f"/{year}/all" in str(captured["url"])
    assert f"type={TREASURY_REAL_YIELD_TYPE}" in str(captured["url"])
```

- [ ] **Step 2: Run tests — expect structural failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "treasury" -v`
Expected: FAIL importing `parse_treasury_real_yields`.

- [ ] **Step 3: Add minimal scaffolding**

Add stubs to `fetch.py`:

```python
TREASURY_REAL_YIELD_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/daily-treasury-rates.csv"
)
TREASURY_REAL_YIELD_TYPE = "daily_treasury_real_yield_curve"


def parse_treasury_real_yields(csv_text: str) -> list[tuple[date, dict[str, Decimal]]]:
    raise NotImplementedError


def treasury_real_yield_curve(*, year: int, timeout_seconds: float = 10.0, opener: UrlOpener = _default_opener) -> list[tuple[date, dict[str, Decimal]]]:
    raise NotImplementedError
```

- [ ] **Step 4: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "treasury" -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement the Treasury fetcher**

Add to `packages/simulation/simulation/market_data/fetch.py`. Add `import csv` and `from datetime import datetime` at the top of the module (next to the existing `from datetime import date`):

```python
TREASURY_REAL_YIELD_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/daily-treasury-rates.csv"
)
TREASURY_REAL_YIELD_TYPE = "daily_treasury_real_yield_curve"
# Treasury CSV column label -> tenor key we expose.
_TREASURY_COLUMNS = {
    "5 YR": "5",
    "7 YR": "7",
    "10 YR": "10",
    "20 YR": "20",
    "30 YR": "30",
}


def parse_treasury_real_yields(csv_text: str) -> list[tuple[date, dict[str, Decimal]]]:
    reader = csv.reader(csv_text.splitlines())
    try:
        header = next(reader)
    except StopIteration:
        return []

    tenor_by_index = {
        index: _TREASURY_COLUMNS[label]
        for index, label in enumerate(header)
        if label in _TREASURY_COLUMNS
    }

    rows: list[tuple[date, dict[str, Decimal]]] = []
    for cols in reader:
        if not cols:
            continue
        try:
            observed = datetime.strptime(cols[0], "%m/%d/%Y").date()
        except ValueError:
            continue
        yields: dict[str, Decimal] = {}
        for index, tenor in tenor_by_index.items():
            if index >= len(cols):
                continue
            try:
                yields[tenor] = Decimal(cols[index]) / Decimal(100)
            except InvalidOperation:
                continue
        if yields:
            rows.append((observed, yields))
    return rows


def treasury_real_yield_curve(
    *,
    year: int,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, dict[str, Decimal]]]:
    params = {"type": TREASURY_REAL_YIELD_TYPE, "field_tdr_date_value": str(year)}
    request = Request(
        f"{TREASURY_REAL_YIELD_URL}/{year}/all?{urlencode(params)}",
        headers={"Cache-Control": "no-cache"},
    )
    try:
        with opener(request, timeout_seconds) as response:
            csv_text = response.read().decode("utf-8")
        rows = parse_treasury_real_yields(csv_text)
    except Exception:
        logger.exception("Treasury real-yield fetch failed for %s", year)
        raise

    if not rows:
        logger.warning("Treasury real-yield fetch returned no usable rows for %s", year)
    return rows
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_fetch.py -k "treasury" -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/fetch.py packages/simulation/tests/market_data/test_fetch.py
git commit -m "feat(simulation): add Treasury real-yield-curve fetcher"
```

---

## Task 3: Generalize the cache module

**Files:**
- Modify: `packages/simulation/simulation/market_data/cache.py`
- Test: `packages/simulation/tests/market_data/test_cache.py`

- [ ] **Step 1: Write the failing cache-writer tests**

Append to `packages/simulation/tests/market_data/test_cache.py`:

```python
def test_write_sp500_cache_shape(tmp_path: Path) -> None:
    from simulation.market_data.cache import write_sp500_cache

    cache_path = tmp_path / "sp500_close.csv"
    meta_path = tmp_path / "sp500_close.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    observed = date(2026, 6, 27)
    close = Decimal("5762.48")
    pairs = [(observed, close)]

    write_sp500_cache(pairs, now=fetched_at, cache_path=cache_path, meta_path=meta_path)

    assert (
        cache_path.read_text(encoding="utf-8")
        == f"observation_date,close\n{observed.isoformat()},{close}\n"
    )
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["fetched_at"] == fetched_at.isoformat()
    assert meta["source"] == "eod_api"


def test_write_treasury_cache_shape(tmp_path: Path) -> None:
    from simulation.market_data.cache import TREASURY_TENORS, write_treasury_cache

    cache_path = tmp_path / "treasury_real_yield.csv"
    meta_path = tmp_path / "treasury_real_yield.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    observed = date(2026, 6, 27)
    yield_values = [
        Decimal("0.0185"),
        Decimal("0.0190"),
        Decimal("0.0195"),
        Decimal("0.0205"),
        Decimal("0.0215"),
    ]
    yields = dict(zip(TREASURY_TENORS, yield_values, strict=True))
    row = (observed, yields)

    write_treasury_cache([row], now=fetched_at, cache_path=cache_path, meta_path=meta_path)

    header = ",".join(["observation_date", *TREASURY_TENORS])
    values = ",".join(str(yields[t]) for t in TREASURY_TENORS)
    assert cache_path.read_text(encoding="utf-8") == f"{header}\n{observed.isoformat()},{values}\n"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["source"] == "treasury_csv"
```

- [ ] **Step 2: Run tests — expect structural failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_cache.py -k "sp500 or treasury" -v`
Expected: FAIL importing `write_sp500_cache`.

- [ ] **Step 3: Add minimal scaffolding**

Add stub writers and path constants to `cache.py` (return immediately / `raise NotImplementedError`):

```python
DEFAULT_SP500_VENDORED_PATH = _DATA_DIR / "sp500_close.csv"
DEFAULT_SP500_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.csv"
DEFAULT_SP500_META_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.meta.json"
DEFAULT_TREASURY_VENDORED_PATH = _DATA_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_META_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.meta.json"
TREASURY_TENORS = ("5", "7", "10", "20", "30")
resolve_cache_read_path = resolve_t10yie_read_path
is_cache_stale = is_t10yie_cache_stale


def write_sp500_cache(*args, **kwargs) -> None:
    raise NotImplementedError


def write_treasury_cache(*args, **kwargs) -> None:
    raise NotImplementedError
```

- [ ] **Step 4: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_cache.py -k "sp500 or treasury" -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement the generalizations**

In `packages/simulation/simulation/market_data/cache.py`:

(a) Add generic aliases right after the existing `resolve_t10yie_read_path` and
`is_t10yie_cache_stale` definitions so new modules use source-agnostic names:

```python
resolve_cache_read_path = resolve_t10yie_read_path
is_cache_stale = is_t10yie_cache_stale
```

(b) Add default paths + writers (the `TREASURY_TENORS` order pins the column layout):

```python
DEFAULT_SP500_VENDORED_PATH = _DATA_DIR / "sp500_close.csv"
DEFAULT_SP500_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.csv"
DEFAULT_SP500_META_PATH = DEFAULT_MARKET_CACHE_DIR / "sp500_close.meta.json"

DEFAULT_TREASURY_VENDORED_PATH = _DATA_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.csv"
DEFAULT_TREASURY_META_PATH = DEFAULT_MARKET_CACHE_DIR / "treasury_real_yield.meta.json"

TREASURY_TENORS = ("5", "7", "10", "20", "30")


def _write_meta(meta_path: Path, *, now: datetime, source: str) -> None:
    meta_path.write_text(
        json.dumps(
            {"fetched_at": now.isoformat(), "source": source},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def write_sp500_cache(
    pairs: list[tuple[date, Decimal]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_SP500_CACHE_PATH,
    meta_path: Path = DEFAULT_SP500_META_PATH,
    source: str = "eod_api",
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", "close"])
        for observed, close in sorted(pairs, key=lambda item: item[0]):
            writer.writerow([observed.isoformat(), str(close)])
    _write_meta(meta_path, now=now, source=source)


def write_treasury_cache(
    rows: list[tuple[date, dict[str, Decimal]]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_TREASURY_CACHE_PATH,
    meta_path: Path = DEFAULT_TREASURY_META_PATH,
    source: str = "treasury_csv",
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", *TREASURY_TENORS])
        for observed, yields in sorted(rows, key=lambda item: item[0]):
            writer.writerow(
                [observed.isoformat(), *(str(yields[t]) for t in TREASURY_TENORS)]
            )
    _write_meta(meta_path, now=now, source=source)
```

Note: `write_treasury_cache` assumes each written row carries all five tenors; the
resolver only writes rows returned by the fetcher, and the fetcher-produced full rows
always contain them. (Rows missing a tenor are filtered by the resolver in Task 5.)

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_cache.py -v`
Expected: PASS (existing T10YIE tests + 2 new).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/cache.py packages/simulation/tests/market_data/test_cache.py
git commit -m "feat(simulation): add S&P/Treasury cache writers and generic cache names"
```

---

## Task 4: S&P 500 close resolver

**Files:**
- Create: `packages/simulation/simulation/market_data/sp500.py`
- Test: `packages/simulation/tests/market_data/test_sp500.py`

- [ ] **Step 1: Write the failing resolver tests**

Create `packages/simulation/tests/market_data/test_sp500.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from simulation.market_data.sp500 import resolve_latest_sp500_close


def _write_sp500(path: Path, rows: list[tuple[date, float]]) -> Path:
    lines = [f"{observed.isoformat()},{close}" for observed, close in rows]
    path.write_text("\n".join(["observation_date,close", *lines]) + "\n", encoding="utf-8")
    return path


def test_resolves_latest_close_at_or_before_today(tmp_path: Path) -> None:
    earlier = date(2026, 1, 1)
    earlier_close = 5000.0
    later = date(2026, 2, 1)
    later_close = 5100.0
    today = date(2026, 1, 15)
    vendored = _write_sp500(
        tmp_path / "v.csv",
        [(earlier, earlier_close), (later, later_close)],
    )

    resolved = resolve_latest_sp500_close(today=today, vendored_path=vendored)

    assert resolved.close == pytest.approx(earlier_close)
    assert resolved.observation_date == earlier


def test_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_latest_sp500_close(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        allow_refresh=False,
        api_key="eod-key",
        fetcher=fetcher,
    )

    assert calls == 0


def test_does_not_call_fetcher_without_api_key(tmp_path: Path) -> None:
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), 5000.0)])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_latest_sp500_close(
        today=date(2026, 1, 2),
        vendored_path=vendored,
        allow_refresh=True,
        api_key=None,
        fetcher=fetcher,
    )

    assert calls == 0


def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    live_observed = date(2026, 1, 3)
    live_close = Decimal("5200.0")
    today = date(2026, 1, 4)
    refresh_now = datetime(2026, 1, 4, 12, tzinfo=UTC)

    def fetcher(**kwargs):
        return [(live_observed, live_close)]

    resolved = resolve_latest_sp500_close(
        today=today,
        vendored_path=vendored,
        allow_refresh=True,
        now=refresh_now,
        api_key="eod-key",
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.close == pytest.approx(float(live_close))
    assert cache_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored_close = 5000.0
    vendored = _write_sp500(tmp_path / "v.csv", [(date(2026, 1, 1), vendored_close)])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_latest_sp500_close(
        today=date(2026, 1, 4),
        vendored_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="eod-key",
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.close == pytest.approx(vendored_close)
```

- [ ] **Step 2: Run tests — expect structural failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py -v`
Expected: FAIL importing `resolve_latest_sp500_close`.

- [ ] **Step 3: Add minimal scaffolding**

Create `sp500.py` with dataclass + stub resolver:

```python
@dataclass(frozen=True)
class SP500Resolved:
    close: float
    observation_date: date


def resolve_latest_sp500_close(**kwargs) -> SP500Resolved:
    raise NotImplementedError
```

- [ ] **Step 4: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement `sp500.py`**

Create `packages/simulation/simulation/market_data/sp500.py`:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Literal

from simulation.market_data.cache import (
    DEFAULT_SP500_CACHE_PATH,
    DEFAULT_SP500_META_PATH,
    DEFAULT_SP500_VENDORED_PATH,
    is_cache_stale,
    resolve_cache_read_path,
    write_sp500_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, EodCloseFetcher, eod_gspc_close


@dataclass(frozen=True)
class SP500Resolved:
    close: float
    observation_date: date


def _latest_close(today: date, path: Path) -> tuple[date, float]:
    best_date: date | None = None
    best_close: float | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"].strip())
                close = float(row["close"])
            except (KeyError, ValueError, AttributeError):
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_close = close
    if best_date is None or best_close is None:
        raise ValueError(f"no S&P close at or before {today.isoformat()}")
    return best_date, best_close


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
) -> SP500Resolved:
    today = today or date.today()
    read_path = resolve_cache_read_path(cache_path=cache_path, vendored_path=vendored_path)

    if allow_refresh and api_key:
        resolved_now = now or datetime.now(tz=UTC)
        if is_cache_stale(now=resolved_now, meta_path=meta_path):
            try:
                pairs = fetcher(
                    api_key=api_key,
                    from_date=resolved_now.date() - timedelta(days=lookback_days),
                )
                if pairs:
                    write_sp500_cache(
                        pairs, now=resolved_now, cache_path=cache_path, meta_path=meta_path
                    )
                    read_path = resolve_cache_read_path(
                        cache_path=cache_path, vendored_path=vendored_path
                    )
            except Exception:
                pass

    observed, close = _latest_close(today, read_path)
    return SP500Resolved(close=close, observation_date=observed)
```

Add to `fetch.py` (top-level, near the other type alias) so the fetcher type imports cleanly:

```python
EodCloseFetcher = Callable[..., list[tuple[date, Decimal]]]
```

and add `from collections.abc import Callable` to `fetch.py` imports if not present.

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/sp500.py packages/simulation/simulation/market_data/fetch.py packages/simulation/tests/market_data/test_sp500.py
git commit -m "feat(simulation): add S&P 500 close resolver with cache/vendored fallback"
```

---

## Task 5: Treasury real-yield resolver

**Files:**
- Create: `packages/simulation/simulation/market_data/treasury.py`
- Test: `packages/simulation/tests/market_data/test_treasury.py`

- [ ] **Step 1: Write the failing resolver tests**

Create `packages/simulation/tests/market_data/test_treasury.py`:

```python
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from simulation.market_data.cache import TREASURY_TENORS
from simulation.market_data.treasury import resolve_treasury_real_yields


def _write_treasury(path: Path, rows: list[tuple[date, dict[str, float]]]) -> Path:
    lines = []
    for observed, yields in rows:
        values = ",".join(str(yields[t]) for t in TREASURY_TENORS)
        lines.append(f"{observed.isoformat()},{values}")
    header = ",".join(["observation_date", *TREASURY_TENORS])
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return path


def test_resolves_latest_curve_at_or_before_today(tmp_path: Path) -> None:
    earlier = date(2026, 1, 1)
    earlier_twenty_yr = 0.021
    later = date(2026, 2, 1)
    today = date(2026, 1, 15)
    vendored = _write_treasury(
        tmp_path / "v.csv",
        [
            (earlier, {t: earlier_twenty_yr for t in TREASURY_TENORS}),
            (later, {t: 0.019 for t in TREASURY_TENORS}),
        ],
    )

    resolved = resolve_treasury_real_yields(today=today, vendored_path=vendored)

    assert resolved.yields["20"] == pytest.approx(earlier_twenty_yr)
    assert resolved.observation_date == earlier


def test_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    vendored = _write_treasury(
        tmp_path / "v.csv", [(date(2026, 1, 1), {t: 0.02 for t in TREASURY_TENORS})]
    )
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_treasury_real_yields(
        today=date(2026, 1, 2), vendored_path=vendored, allow_refresh=False, fetcher=fetcher
    )

    assert calls == 0


def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored = _write_treasury(
        tmp_path / "v.csv", [(date(2026, 1, 1), {t: 0.02 for t in TREASURY_TENORS})]
    )
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    live_observed = date(2026, 1, 3)
    live_twenty_yr = Decimal("0.013")
    today = date(2026, 1, 4)
    refresh_now = datetime(2026, 1, 4, 12, tzinfo=UTC)

    def fetcher(**kwargs):
        return [
            (
                live_observed,
                {t: live_twenty_yr for t in TREASURY_TENORS},
            )
        ]

    resolved = resolve_treasury_real_yields(
        today=today,
        vendored_path=vendored,
        allow_refresh=True,
        now=refresh_now,
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.yields["20"] == pytest.approx(float(live_twenty_yr))
    assert cache_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored_twenty_yr = 0.021
    vendored = _write_treasury(
        tmp_path / "v.csv",
        [(date(2026, 1, 1), {t: vendored_twenty_yr for t in TREASURY_TENORS})],
    )
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_treasury_real_yields(
        today=date(2026, 1, 4),
        vendored_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        fetcher=fetcher,
        cache_path=cache_path,
        meta_path=meta_path,
    )

    assert resolved.yields["20"] == pytest.approx(vendored_twenty_yr)
```

- [ ] **Step 2: Run tests — expect structural failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_treasury.py -v`
Expected: FAIL importing `resolve_treasury_real_yields`.

- [ ] **Step 3: Add minimal scaffolding**

Create `treasury.py` with dataclass + stub resolver (same pattern as Task 4).

- [ ] **Step 4: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_treasury.py -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement `treasury.py`**

Create `packages/simulation/simulation/market_data/treasury.py`:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from simulation.market_data.cache import (
    DEFAULT_TREASURY_CACHE_PATH,
    DEFAULT_TREASURY_META_PATH,
    DEFAULT_TREASURY_VENDORED_PATH,
    TREASURY_TENORS,
    is_cache_stale,
    resolve_cache_read_path,
    write_treasury_cache,
)
from simulation.market_data.fetch import TreasuryFetcher, treasury_real_yield_curve


@dataclass(frozen=True)
class TreasuryYieldsResolved:
    yields: dict[str, float]
    observation_date: date


def _latest_curve(today: date, path: Path) -> tuple[date, dict[str, float]]:
    best_date: date | None = None
    best_yields: dict[str, float] | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                observed = date.fromisoformat(row["observation_date"].strip())
            except (KeyError, ValueError, AttributeError):
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                yields: dict[str, float] = {}
                for tenor in TREASURY_TENORS:
                    cell = row.get(tenor, "")
                    if cell:
                        try:
                            yields[tenor] = float(cell)
                        except ValueError:
                            continue
                best_date = observed
                best_yields = yields
    if best_date is None or best_yields is None:
        raise ValueError(f"no Treasury curve at or before {today.isoformat()}")
    return best_date, best_yields


def resolve_treasury_real_yields(
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fetcher: TreasuryFetcher = treasury_real_yield_curve,
    cache_path: Path = DEFAULT_TREASURY_CACHE_PATH,
    meta_path: Path = DEFAULT_TREASURY_META_PATH,
    vendored_path: Path = DEFAULT_TREASURY_VENDORED_PATH,
) -> TreasuryYieldsResolved:
    today = today or date.today()
    read_path = resolve_cache_read_path(cache_path=cache_path, vendored_path=vendored_path)

    if allow_refresh:
        resolved_now = now or datetime.now(tz=UTC)
        if is_cache_stale(now=resolved_now, meta_path=meta_path):
            try:
                rows = [
                    row
                    for row in fetcher(year=resolved_now.year)
                    if all(tenor in row[1] for tenor in TREASURY_TENORS)
                ]
                if rows:
                    write_treasury_cache(
                        rows, now=resolved_now, cache_path=cache_path, meta_path=meta_path
                    )
                    read_path = resolve_cache_read_path(
                        cache_path=cache_path, vendored_path=vendored_path
                    )
            except Exception:
                pass

    observed, yields = _latest_curve(today, read_path)
    return TreasuryYieldsResolved(yields=yields, observation_date=observed)
```

Add to `fetch.py` (near `EodCloseFetcher`):

```python
TreasuryFetcher = Callable[..., list[tuple[date, dict[str, Decimal]]]]
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_treasury.py -v`
Expected: PASS (4 tests).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/treasury.py packages/simulation/simulation/market_data/fetch.py packages/simulation/tests/market_data/test_treasury.py
git commit -m "feat(simulation): add Treasury real-yield resolver with cache/vendored fallback"
```

---

## Task 6: Vendored snapshots, provenance, and package exports

> **Shortened TDD loop:** Resolvers already exist from Tasks 4–5, so this task skips scaffolding
> (Steps 3–4). Flow: write smoke tests → run (logical fail, missing CSV) → add data/exports → pass.

**Files:**
- Create: `packages/simulation/simulation/market_data/data/sp500_close.csv`
- Create: `packages/simulation/simulation/market_data/data/treasury_real_yield.csv`
- Modify: `packages/simulation/simulation/market_data/data/PROVENANCE.md`
- Modify: `packages/simulation/simulation/market_data/__init__.py`
- Test: `packages/simulation/tests/market_data/test_sp500.py`, `.../test_treasury.py`

- [ ] **Step 1: Write failing integration smoke tests (vendored fallback)**

Append to `test_sp500.py`:

```python
def test_vendored_snapshot_resolves_latest_committed_row() -> None:
    import csv

    from simulation.market_data.cache import DEFAULT_SP500_VENDORED_PATH

    today = date(2026, 6, 30)
    with DEFAULT_SP500_VENDORED_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    expected_row = max(rows, key=lambda row: row["observation_date"])
    expected_close = float(expected_row["close"])
    expected_date = date.fromisoformat(expected_row["observation_date"])

    resolved = resolve_latest_sp500_close(today=today)

    assert resolved.close == pytest.approx(expected_close)
    assert resolved.observation_date == expected_date
```

Append to `test_treasury.py`:

```python
def test_vendored_snapshot_resolves_latest_committed_curve() -> None:
    import csv

    from simulation.market_data.cache import DEFAULT_TREASURY_VENDORED_PATH, TREASURY_TENORS

    today = date(2026, 6, 30)
    with DEFAULT_TREASURY_VENDORED_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    expected_row = max(rows, key=lambda row: row["observation_date"])
    expected_twenty_yr = float(expected_row["20"])
    expected_date = date.fromisoformat(expected_row["observation_date"])

    resolved = resolve_treasury_real_yields(today=today)

    assert resolved.yields["20"] == pytest.approx(expected_twenty_yr)
    assert resolved.observation_date == expected_date
    assert set(resolved.yields) == set(TREASURY_TENORS)
```

These read expected values from the committed CSV (single source of truth), not duplicated literals.

- [ ] **Step 2: Run tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py::test_vendored_snapshot_resolves_latest_committed_row packages/simulation/tests/market_data/test_treasury.py::test_vendored_snapshot_resolves_latest_committed_curve -v`
Expected: FAIL with `ValueError: no S&P close ...` / `FileNotFoundError` (vendored files absent).

- [ ] **Step 3: Create the vendored snapshots**

Create `packages/simulation/simulation/market_data/data/sp500_close.csv` (monthly close
values sourced manually from public S&P 500 index data; refresh via the maintainer command
in Task 7):

```
observation_date,close
2026-03-31,5700.00
2026-04-30,5760.00
2026-05-29,5820.00
2026-06-30,5880.00
```

Create `packages/simulation/simulation/market_data/data/treasury_real_yield.csv`
(month-end 5/7/10/20/30-yr TIPS real yields as decimals, sourced manually from the
Treasury real-yield curve; refresh via the maintainer command):

```
observation_date,5,7,10,20,30
2026-03-31,0.0155,0.0166,0.0178,0.0210,0.0228
2026-04-30,0.0158,0.0169,0.0181,0.0213,0.0231
2026-05-29,0.0160,0.0171,0.0183,0.0215,0.0233
2026-06-30,0.0162,0.0173,0.0185,0.0217,0.0235
```

> Implementer note: these are seeded month-end reference values committed so the offline
> fallback resolves. A maintainer should run `scripts/refresh_market_data.py --update-vendored`
> (Task 7) with live keys to replace them with an authoritative pull before release, and
> update the download date in `PROVENANCE.md`.

- [ ] **Step 4: Add PROVENANCE entries**

Append to `packages/simulation/simulation/market_data/data/PROVENANCE.md`:

```markdown
## sp500_close.csv

- **Source:** EOD Historical Data (EODHD) `GSPC.INDX` daily `close`
  (https://eodhistoricaldata.com/api/eod/GSPC.INDX). Used unadjusted (price, for CAPE).
- **Seeded:** 2026-07-05 (month-end reference values, manual public-source snapshot).
- **Columns:** `observation_date` (`YYYY-MM-DD`), `close` (index level).
- **Use:** latest close at or before `today` feeds the Phase 3c-2 1/CAPE regression presets.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (requires `EOD_API_KEY`).

## treasury_real_yield.csv

- **Source:** U.S. Treasury daily TIPS real-yield curve
  (https://home.treasury.gov/.../daily-treasury-rates.csv, `daily_treasury_real_yield_curve`).
- **Seeded:** 2026-07-05 (month-end reference values, manual public-source snapshot).
- **Columns:** `observation_date` (`YYYY-MM-DD`), `5,7,10,20,30` real yields as **decimals**
  (e.g. `0.0217` = 2.17%).
- **Use:** latest curve at or before `today`; the 20-yr yield is the Phase 3c-2 bond preset.
- **Refresh:** `scripts/refresh_market_data.py --update-vendored` (no API key required).
```

- [ ] **Step 5: Export the resolvers**

Replace `packages/simulation/simulation/market_data/__init__.py` with:

```python
"""Market data: vendored historical returns, bootstrap sampler, inflation, live feeds."""

from simulation.market_data.bootstrap import ReturnPaths, build_return_paths
from simulation.market_data.inflation import InflationResolved, resolve_inflation
from simulation.market_data.returns import HistoricalReturns, load_historical_returns
from simulation.market_data.sp500 import SP500Resolved, resolve_latest_sp500_close
from simulation.market_data.treasury import (
    TreasuryYieldsResolved,
    resolve_treasury_real_yields,
)

__all__ = [
    "HistoricalReturns",
    "InflationResolved",
    "ReturnPaths",
    "SP500Resolved",
    "TreasuryYieldsResolved",
    "build_return_paths",
    "load_historical_returns",
    "resolve_inflation",
    "resolve_latest_sp500_close",
    "resolve_treasury_real_yields",
]
```

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest packages/simulation/tests/market_data/ -v`
Expected: PASS (all market_data tests, including the two vendored smoke tests).

- [ ] **Step 7: Commit**

```bash
git add packages/simulation/simulation/market_data/data/ packages/simulation/simulation/market_data/__init__.py packages/simulation/tests/market_data/
git commit -m "feat(simulation): vendor S&P/Treasury snapshots and export live-feed resolvers"
```

---

## Task 7: Extend the manual refresh CLI

**Files:**
- Modify: `scripts/refresh_market_data.py`
- Test: `tests/test_refresh_market_data.py` (extend the existing repo-root test file)

> **Back-compat contract:** The existing CLI is FRED-only, hard-errors (exit `2`) when the
> FRED key is missing, and prints `"FRED API key is not configured"` / `"Wrote T10YIE cache"`
> / `"Update PROVENANCE.md"`. Three existing tests in `tests/test_refresh_market_data.py`
> pin these exact messages/codes and inject the FRED fetcher via the `fetcher=` kwarg. The
> refactor MUST keep the **default (no `--only`/`--all`) behavior and those messages/kwarg
> name unchanged**, so those tests keep passing untouched. New sources are opt-in.

- [ ] **Step 1: Write the failing CLI tests (extend the existing file)**

Append to `tests/test_refresh_market_data.py` (the file already does the
`sys.path.insert(SCRIPTS)` + `import refresh_market_data` dance and has `db_path` from the
repo-root `conftest.py`):

```python
def test_refresh_only_sp500_writes_cache(tmp_path, db_path) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key="eod-cli-key"))
    cache_path = tmp_path / "sp500_close.csv"
    meta_path = tmp_path / "sp500_close.meta.json"
    live_observed = date(2026, 1, 3)
    live_close = Decimal("5200.0")

    def eod_fetcher(**kwargs):
        return [(live_observed, live_close)]

    exit_code = refresh_market_data.main(
        [
            "--db-path", str(db_path),
            "--only", "sp500",
            "--sp500-cache-path", str(cache_path),
            "--sp500-meta-path", str(meta_path),
        ],
        eod_fetcher=eod_fetcher,
    )

    assert exit_code == 0
    assert str(live_close) in cache_path.read_text(encoding="utf-8")


def test_refresh_only_treasury_needs_no_key(tmp_path, db_path) -> None:
    from simulation.market_data.cache import TREASURY_TENORS

    SettingsRepository(db_path=db_path).save(AppSettings())  # no keys
    cache_path = tmp_path / "treasury_real_yield.csv"
    meta_path = tmp_path / "treasury_real_yield.meta.json"
    live_observed = date(2026, 1, 3)
    live_yield = Decimal("0.02")

    def treasury_fetcher(**kwargs):
        return [(live_observed, {t: live_yield for t in TREASURY_TENORS})]

    exit_code = refresh_market_data.main(
        [
            "--db-path", str(db_path),
            "--only", "treasury",
            "--treasury-cache-path", str(cache_path),
            "--treasury-meta-path", str(meta_path),
        ],
        treasury_fetcher=treasury_fetcher,
    )

    assert exit_code == 0
    assert cache_path.is_file()


def test_refresh_only_sp500_without_key_returns_two(db_path, capsys) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings())  # no EOD key

    exit_code = refresh_market_data.main(["--db-path", str(db_path), "--only", "sp500"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "EOD API key is not configured" in captured.err
```

- [ ] **Step 2: Run tests — expect structural/logical failure**

Run: `uv run pytest tests/test_refresh_market_data.py -v`
Expected: the three **new** tests FAIL (`--only` / `eod_fetcher` not implemented). The three **existing** T10YIE tests must still PASS.

- [ ] **Step 3: Add minimal scaffolding**

Extend `_parser()` with `--only` / `--all` and new path args; extend `main()` signature with
`eod_fetcher` / `treasury_fetcher` kwargs but leave warmers as `raise NotImplementedError`.

- [ ] **Step 4: Run new tests — expect logical failure**

Run: `uv run pytest tests/test_refresh_market_data.py -k "sp500 or treasury" -v`
Expected: FAIL with `NotImplementedError` (existing T10YIE tests still pass when run in full file).

- [ ] **Step 5: Implement the CLI refactor (legacy default preserved)**

In `scripts/refresh_market_data.py`, add imports and `Callable`
(`from collections.abc import Callable`), and add the new default paths + writers +
fetchers:

```python
from simulation.market_data.cache import (
    DEFAULT_SP500_CACHE_PATH,
    DEFAULT_SP500_META_PATH,
    DEFAULT_SP500_VENDORED_PATH,
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    DEFAULT_T10YIE_VENDORED_PATH,
    DEFAULT_TREASURY_CACHE_PATH,
    DEFAULT_TREASURY_META_PATH,
    DEFAULT_TREASURY_VENDORED_PATH,
    write_sp500_cache,
    write_t10yie_cache,
    write_treasury_cache,
)
from simulation.market_data.fetch import (
    LOOKBACK_DAYS,
    eod_gspc_close,
    fred_observations,
    treasury_real_yield_curve,
)

SOURCES = ("t10yie", "sp500", "treasury")
```

Extend `_parser()` with `--only`, `--all`, and the S&P/Treasury path args (keep the existing
`--cache-path/--meta-path/--vendored-path` for T10YIE):

```python
    parser.add_argument("--only", choices=SOURCES, default=None)
    parser.add_argument("--all", action="store_true", help="warm every source")
    parser.add_argument("--sp500-cache-path", type=Path, default=DEFAULT_SP500_CACHE_PATH)
    parser.add_argument("--sp500-meta-path", type=Path, default=DEFAULT_SP500_META_PATH)
    parser.add_argument("--sp500-vendored-path", type=Path, default=DEFAULT_SP500_VENDORED_PATH)
    parser.add_argument("--treasury-cache-path", type=Path, default=DEFAULT_TREASURY_CACHE_PATH)
    parser.add_argument("--treasury-meta-path", type=Path, default=DEFAULT_TREASURY_META_PATH)
    parser.add_argument(
        "--treasury-vendored-path", type=Path, default=DEFAULT_TREASURY_VENDORED_PATH
    )
```

Replace the `main()` body. Keep the `fetcher=fred_observations` kwarg name for back-compat,
and add `eod_fetcher`/`treasury_fetcher`. Default selection (neither `--only` nor `--all`) is
`["t10yie"]`, preserving legacy behavior; `--all` warms every source; `--only X` warms one:

```python
def main(
    argv: list[str] | None = None,
    *,
    fetcher: Fetcher = fred_observations,
    eod_fetcher: Callable[..., list] = eod_gspc_close,
    treasury_fetcher: Callable[..., list] = treasury_real_yield_curve,
) -> int:
    args = _parser().parse_args(argv)
    settings = SettingsRepository(db_path=args.db_path).get()
    now = datetime.now(tz=UTC)
    if args.only:
        selected = [args.only]
    elif args.all:
        selected = list(SOURCES)
    else:
        selected = ["t10yie"]

    worst = 0
    if "t10yie" in selected:
        worst = max(worst, _warm_t10yie(args, settings, now, fetcher))
    if "sp500" in selected:
        worst = max(worst, _warm_sp500(args, settings, now, eod_fetcher))
    if "treasury" in selected:
        worst = max(worst, _warm_treasury(args, now, treasury_fetcher))
    return worst
```

Add the warmers. `_warm_t10yie` reproduces the **exact** legacy messages/codes the existing
tests assert:

```python
def _warm_t10yie(args, settings, now, fetcher) -> int:
    if not settings.fred_api_key:
        print("FRED API key is not configured in Settings.", file=sys.stderr)
        return 2
    observation_start = (
        None if args.update_vendored else now.date() - timedelta(days=LOOKBACK_DAYS)
    )
    pairs = fetcher(api_key=settings.fred_api_key, observation_start=observation_start)
    if not pairs:
        print("FRED returned no usable T10YIE observations.", file=sys.stderr)
        return 1
    if args.update_vendored:
        write_t10yie_cache(
            pairs, now=now, cache_path=args.vendored_path,
            meta_path=args.vendored_path.with_suffix(".meta.json"),
            source="fred_api_full_series",
        )
        args.vendored_path.with_suffix(".meta.json").unlink(missing_ok=True)
        print(f"Wrote vendored T10YIE CSV to {args.vendored_path}")
        print("Update PROVENANCE.md download date before committing.")
        return 0
    write_t10yie_cache(pairs, now=now, cache_path=args.cache_path, meta_path=args.meta_path)
    latest_date = max(observed for observed, _ in pairs)
    print(f"Wrote T10YIE cache to {args.cache_path} (latest {latest_date.isoformat()})")
    return 0


def _warm_sp500(args, settings, now, fetcher) -> int:
    if not settings.eod_api_key:
        print("EOD API key is not configured in Settings.", file=sys.stderr)
        return 2
    from_date = (
        date(1990, 1, 1)
        if args.update_vendored
        else now.date() - timedelta(days=LOOKBACK_DAYS)
    )
    pairs = fetcher(api_key=settings.eod_api_key, from_date=from_date)
    if not pairs:
        print("EOD returned no usable S&P rows.", file=sys.stderr)
        return 1
    target = args.sp500_vendored_path if args.update_vendored else args.sp500_cache_path
    meta = target.with_suffix(".meta.json") if args.update_vendored else args.sp500_meta_path
    write_sp500_cache(pairs, now=now, cache_path=target, meta_path=meta)
    if args.update_vendored:
        meta.unlink(missing_ok=True)
        print("Update PROVENANCE.md download date before committing.")
    print(f"Wrote S&P close to {target}")
    return 0


def _warm_treasury(args, now, fetcher) -> int:
    rows = fetcher(year=now.year)
    if not rows:
        print("Treasury returned no usable rows.", file=sys.stderr)
        return 1
    target = (
        args.treasury_vendored_path if args.update_vendored else args.treasury_cache_path
    )
    meta = (
        target.with_suffix(".meta.json")
        if args.update_vendored
        else args.treasury_meta_path
    )
    write_treasury_cache(rows, now=now, cache_path=target, meta_path=meta)
    if args.update_vendored:
        meta.unlink(missing_ok=True)
        print("Update PROVENANCE.md download date before committing.")
    print(f"Wrote Treasury real yields to {target}")
    return 0
```

Update the module header comment block to document `--only`, `--all`, and the S&P/Treasury
path flags, and note S&P `--update-vendored` uses a long `from` date while Treasury pulls
the current year.

- [ ] **Step 6: Run tests — expect pass**

Run: `uv run pytest tests/test_refresh_market_data.py -v`
Expected: PASS (3 existing T10YIE tests unchanged + 3 new).

- [ ] **Step 7: Commit**

```bash
git add scripts/refresh_market_data.py tests/test_refresh_market_data.py
git commit -m "feat(simulation): warm S&P/Treasury caches in refresh CLI"
```

---

## Task 8: Full verification

- [ ] **Step 1: Run the whole suite + lint**

Run: `make`
Expected: PASS (ruff check + format + pyright + pytest across all packages).

- [ ] **Step 2: Fix any lint/type findings**

If pyright flags the loosely-typed `Callable[..., list]` params in the CLI or the resolver
`fetcher` seams, tighten them to the `EodCloseFetcher` / `TreasuryFetcher` aliases from
`fetch.py`. Do not add `# type: ignore`. Re-run `make`.

- [ ] **Step 3: Confirm the feeds are unconsumed (additive check)**

Run: `git grep -n "resolve_latest_sp500_close\|resolve_treasury_real_yields" -- packages ':!packages/simulation'`
Expected: no matches — only Phase 3c-2 will consume them.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "chore(simulation): tidy types after Phase 3c-1 feeds"
```

---

## Self-Review Notes

- **Spec coverage:** EOD fetcher (Task 1) ✓, Treasury fetcher (Task 2) ✓, cache generalization (Task 3) ✓, `sp500.py`/`treasury.py` resolvers with cache→vendored + fail-silent refresh (Tasks 4–5) ✓, vendored snapshots + PROVENANCE + exports (Task 6) ✓, CLI warming + `--update-vendored` (Task 7) ✓, network-free/injected tests throughout ✓, purely additive verified (Task 8 Step 3) ✓.
- **VT/BND:** intentionally absent (dropped in spec §1).
- **Type consistency:** `EodCloseFetcher` / `TreasuryFetcher` aliases defined in `fetch.py` (Tasks 4–5) and reused by resolvers + CLI. `SP500Resolved.close: float`, `TreasuryYieldsResolved.yields: dict[str, float]` used consistently in resolvers and tests.
- **Cache names:** `resolve_cache_read_path` / `is_cache_stale` are the generic canonical names (aliases of the existing T10YIE functions), used by both new resolvers; existing T10YIE imports keep working.
- **AGENTS.md testing policy:** every code task uses the 7-step structural→logical TDD loop; tests bind shared literals once, import production constants (`TREASURY_TENORS`, `DEFAULT_*_VENDORED_PATH`, `EOD_SP500_SYMBOL`), inject `today`/`now`/fetchers, and avoid trivial `isinstance`/framework-only assertions.

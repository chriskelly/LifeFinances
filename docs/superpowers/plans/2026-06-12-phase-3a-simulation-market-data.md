# Phase 3a — Simulation: Market Data and Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the stochastic foundation for the TPAW engine — vendored historical real monthly returns turned into reproducible block-bootstrapped log-return paths, plus a resolved scalar inflation rate — without running the withdrawal loop.

**Architecture:** A new `packages/simulation/simulation/market_data/` subpackage with three modules (`returns.py`, `bootstrap.py`, `inflation.py`) and a vendored `data/` directory. Two config models (`SamplingConfig`, `InflationConfig`) land on `core.Plan` so sampling/inflation choices persist with the plan. The public API exposes `build_return_paths(...)` and `resolve_inflation(...)`; these are tested building blocks consumed by the Phase 3b engine (not wired into `run_simulation` yet).

**Tech Stack:** Python 3.14, numpy (new dep), pydantic, pytest. Ports algorithms from `tpaw/packages/simulator-rust`.

**Spec:** [`docs/superpowers/specs/2026-06-25-phase-3a-simulation-market-data-design.md`](../specs/2026-06-25-phase-3a-simulation-market-data-design.md)

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| `packages/simulation/pyproject.toml` | Add `numpy` dependency (via `uv add`). |
| `packages/core/core/models.py` | Add `SamplingConfig`, `InflationConfig`; add `sampling` / `inflation` fields to `Plan`. |
| `packages/simulation/simulation/market_data/__init__.py` | Re-export public API + types. |
| `packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv` | Vendored tpaw v7 raw real monthly returns. |
| `packages/simulation/simulation/market_data/data/t10yie_daily.csv` | Vendored FRED `T10YIE` breakeven inflation. |
| `packages/simulation/simulation/market_data/data/PROVENANCE.md` | Source, version, dates, attribution for both CSVs. |
| `packages/simulation/simulation/market_data/returns.py` | Load CSV → log returns; `HistoricalReturns`; faithful-port guard. |
| `packages/simulation/simulation/market_data/bootstrap.py` | Staggered block-bootstrap index sequences; `build_return_paths`; `ReturnPaths`. |
| `packages/simulation/simulation/market_data/inflation.py` | Suggested (`T10YIE`) / manual resolution; `resolve_inflation`; `InflationResolved`. |
| `packages/simulation/simulation/__init__.py` | Re-export market-data API from the package root. |
| `packages/simulation/tests/market_data/test_returns.py` | Returns load + log + guard tests. |
| `packages/simulation/tests/market_data/test_bootstrap.py` | Sampler tests. |
| `packages/simulation/tests/market_data/test_inflation.py` | Inflation tests. |
| `packages/core/tests/test_sampling_inflation_config.py` | Config model tests. |
| `docs/superpowers/plans/2026-06-12-rebuild-index.md` | Update Phase 3a exit criteria (§9 divergence). |

**Conventions to follow (from existing code):**
- `from __future__ import annotations` at the top of every new module (matches `core/models.py`, `simulation/stub.py`).
- Named/keyword-only parameters for multi-arg functions (`*,` after the first positional), per `AGENTS.md`.
- `Decimal` for money in `core`; `float`/numpy for returns and rates in `simulation`.
- Tests import constants/defaults from source — never re-hardcode them in both arrange and assert.
- Run all commands from the **repo root** `/Users/chris/Projects/life-finances-workspace/LifeFInances`.

---

## Task 1: Add numpy dependency to the simulation package

**Files:**
- Modify: `packages/simulation/pyproject.toml` (dependencies list)
- Modify: `uv.lock` (auto, via `uv`)

- [ ] **Step 1: Add numpy via uv (never hand-edit the lockfile)**

Run:

```bash
uv add --package life-finances-simulation numpy
```

- [ ] **Step 2: Verify it resolved and imports**

Run:

```bash
uv run python -c "import numpy; print(numpy.__version__)"
```

Expected: prints a numpy version (e.g. `2.x.x`), no error.

- [ ] **Step 3: Confirm the dependency landed in the package, not the root**

Read `packages/simulation/pyproject.toml` and confirm `numpy` now appears in `[project].dependencies`. Expected: the `dependencies` list contains `life-finances-core`, `life-finances-domain`, and `numpy`.

- [ ] **Step 4: Commit**

```bash
git add packages/simulation/pyproject.toml uv.lock
git commit -m "build(simulation): add numpy dependency for market-data bootstrap"
```

---

## Task 2: Config models in core (`SamplingConfig`, `InflationConfig`)

These persist on `Plan`. Defaults mirror tpaw constants so existing plans and `data.db.blank` load without migration.

**Files:**
- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_sampling_inflation_config.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_sampling_inflation_config.py`:

```python
from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import (
    InflationConfig,
    Plan,
    SamplingConfig,
)
from pydantic import ValidationError


def test_sampling_rejects_non_positive_block_size() -> None:
    with pytest.raises(ValidationError):
        SamplingConfig(block_size_months=0)


def test_sampling_rejects_non_positive_num_runs() -> None:
    with pytest.raises(ValidationError):
        SamplingConfig(num_runs=0)


def test_inflation_defaults_to_suggested() -> None:
    config = InflationConfig()

    assert config.mode == "suggested"
    assert config.manual_annual_rate is None


def test_inflation_manual_requires_rate() -> None:
    with pytest.raises(ValidationError):
        InflationConfig(mode="manual")


def test_inflation_manual_accepts_rate() -> None:
    expected_rate = Decimal("0.025")

    config = InflationConfig(mode="manual", manual_annual_rate=expected_rate)

    assert config.manual_annual_rate == expected_rate


def test_plan_gets_default_sampling_and_inflation() -> None:
    plan = default_plan()

    assert plan.sampling == SamplingConfig()
    assert plan.inflation == InflationConfig()


def test_older_plan_json_without_configs_fills_defaults() -> None:
    plan = default_plan()
    payload = plan.model_dump()
    del payload["sampling"]
    del payload["inflation"]

    rehydrated = Plan.model_validate(payload)

    assert rehydrated.sampling == SamplingConfig()
    assert rehydrated.inflation == InflationConfig()
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a LOGICAL failure**

Add to `packages/core/core/models.py` (constants near the top, models before `Plan`):

```python
DEFAULT_BLOCK_SIZE_MONTHS = 60  # tpaw blockSize.inMonths = 12 * 5
DEFAULT_NUM_RUNS = 500  # tpaw numOfSimulationForMonteCarloSampling
DEFAULT_STAGGER_RUN_STARTS = True  # tpaw staggerRunStarts
DEFAULT_SAMPLING_SEED = 1_234_567  # LifeFinances default for reproducibility


class SamplingConfig(BaseModel):
    pass


class InflationConfig(BaseModel):
    pass
```

Run:

```bash
uv run pytest packages/core/tests/test_sampling_inflation_config.py -v
```

Expected: tests FAIL on assertions / validation (logical), e.g. `AttributeError` is structural — if you see `AttributeError`/`ImportError`, the scaffolding is incomplete; add the missing names until failures are `AssertionError` or "did not raise ValidationError". Confirm the failure type is **logical** before implementing.

- [ ] **Step 3: Implement the models and wire them onto `Plan`**

Replace the scaffolding in `packages/core/core/models.py` with the full implementation:

```python
class SamplingConfig(BaseModel):
    block_size_months: int = Field(default=DEFAULT_BLOCK_SIZE_MONTHS, ge=1)
    num_runs: int = Field(default=DEFAULT_NUM_RUNS, ge=1)
    stagger_run_starts: bool = DEFAULT_STAGGER_RUN_STARTS
    seed: int = DEFAULT_SAMPLING_SEED


class InflationConfig(BaseModel):
    mode: Literal["suggested", "manual"] = "suggested"
    manual_annual_rate: Decimal | None = None

    @model_validator(mode="after")
    def _require_manual_rate(self) -> InflationConfig:
        if self.mode == "manual" and self.manual_annual_rate is None:
            raise ValueError("manual_annual_rate is required when mode == 'manual'")
        return self
```

Add the two fields to `Plan` (after `manual_income_streams`):

```python
class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    manual_income_streams: list[TimedStream] = Field(default_factory=list)
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    inflation: InflationConfig = Field(default_factory=InflationConfig)
```

- [ ] **Step 4: Run the tests — must pass**

Run:

```bash
uv run pytest packages/core/tests/test_sampling_inflation_config.py -v
```

Expected: PASS (all 8 tests).

- [ ] **Step 5: Confirm no regressions in core + repo round-trip still works**

Run:

```bash
uv run pytest packages/core -q
```

Expected: PASS. (The repository persists `Plan` via `model_dump_json`; new fields serialize automatically.)

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_sampling_inflation_config.py
git commit -m "feat(core): add SamplingConfig and InflationConfig to Plan"
```

---

## Task 3: Vendor the historical returns CSV + provenance

The source of truth is tpaw v7 raw real monthly returns. We vendor the CSV unchanged (it includes a `CAPE` column we ignore in 3a) and the loader strips it.

**Files:**
- Create: `packages/simulation/simulation/market_data/__init__.py` (empty placeholder for now)
- Create: `packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv` (copied)
- Create: `packages/simulation/simulation/market_data/data/PROVENANCE.md`

- [ ] **Step 1: Create the subpackage directory and copy the CSV**

Run (the `tpaw` repo is a sibling of this repo):

```bash
mkdir -p packages/simulation/simulation/market_data/data
cp ../tpaw/packages/simulator-rust/src/lib/historical_monthly_returns/data/v7/v7_raw_data.csv \
   packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv
```

- [ ] **Step 2: Verify the vendored file shape (1857 data rows, BOM header, no trailing newline)**

Run:

```bash
head -3 packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv
wc -l packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv
```

Expected: header `year,month,CAPE,stock real return,bond real return` (note: file begins with a UTF-8 BOM); `wc -l` reports `1857` (last row has no trailing newline → 1 header + 1857 data rows).

- [ ] **Step 3: Create the empty subpackage marker**

Create `packages/simulation/simulation/market_data/__init__.py` with a single line (re-exports come in Task 8):

```python
"""Market data: vendored historical returns, bootstrap sampler, inflation."""
```

- [ ] **Step 4: Write provenance**

Create `packages/simulation/simulation/market_data/data/PROVENANCE.md`:

```markdown
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
- **Downloaded:** <FILL IN download date when Task 6 runs>.
- **Columns:** first column is the observation date (`YYYY-MM-DD`), second column is the
  breakeven rate in **percent** (e.g. `2.35`). Missing observations appear as `.`.
- **Use:** "suggested" inflation = latest observation at or before `today`, parsed
  percent → decimal, rounded to 3 dp (mirrors tpaw `T10YIE` handling).
```

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/market_data/__init__.py \
        packages/simulation/simulation/market_data/data/v7_real_monthly_returns.csv \
        packages/simulation/simulation/market_data/data/PROVENANCE.md
git commit -m "chore(simulation): vendor tpaw v7 historical returns CSV with provenance"
```

---

## Task 4: `returns.py` — load CSV → log returns + faithful-port guard

**Files:**
- Create: `packages/simulation/simulation/market_data/returns.py`
- Test: `packages/simulation/tests/market_data/test_returns.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/simulation/tests/market_data/__init__.py` (empty) and `packages/simulation/tests/market_data/test_returns.py`:

```python
from __future__ import annotations

from pathlib import Path

import numpy as np
from simulation.market_data.returns import (
    HistoricalReturns,
    load_historical_returns,
    _load_from_csv,
)

# Pinned contract values copied from tpaw's source of truth
# (v7_raw_monthly_non_log_series.rs / v7_raw_data.csv). These lock the vendored
# CSV to tpaw's data; update only when intentionally bumping the dataset version.
PINNED_START = (1871, 1)
PINNED_LENGTH = 1857
PINNED_FIRST_STOCK_NON_LOG = -0.0117810825569089
PINNED_FIRST_BOND_NON_LOG = -0.025576313862529
PINNED_LAST_STOCK_NON_LOG = 0.0227344987950218
PINNED_LAST_BOND_NON_LOG = 0.00704720957728999


def _write_csv(path: Path, rows: list[str]) -> Path:
    header = "year,month,CAPE,stock real return,bond real return"
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return path


def test_log_conversion_round_trips_to_source_non_log_values(tmp_path: Path) -> None:
    stock_non_log = 0.05
    bond_non_log = -0.02
    csv = _write_csv(tmp_path / "tiny.csv", [f"2000,1,NA,{stock_non_log},{bond_non_log}"])

    hist = _load_from_csv(csv)

    assert np.isclose(np.expm1(hist.stocks_log[0]), stock_non_log)
    assert np.isclose(np.expm1(hist.bonds_log[0]), bond_non_log)


def test_load_reports_length_and_start(tmp_path: Path) -> None:
    rows = ["2000,1,NA,0.01,0.01", "2000,2,NA,0.02,0.02"]
    csv = _write_csv(tmp_path / "two.csv", rows)

    hist = _load_from_csv(csv)

    assert hist.length == len(rows)
    assert hist.start == (2000, 1)


def test_default_load_is_memoized() -> None:
    first = load_historical_returns()
    second = load_historical_returns()

    assert first is second


def test_vendored_csv_is_faithful_port_of_tpaw_source() -> None:
    hist = load_historical_returns()

    assert hist.start == PINNED_START
    assert hist.length == PINNED_LENGTH
    # f32-precision tolerance: tpaw bakes the .rs array as f32 literals.
    tol = 1e-7
    assert np.isclose(np.expm1(hist.stocks_log[0]), PINNED_FIRST_STOCK_NON_LOG, atol=tol)
    assert np.isclose(np.expm1(hist.bonds_log[0]), PINNED_FIRST_BOND_NON_LOG, atol=tol)
    assert np.isclose(np.expm1(hist.stocks_log[-1]), PINNED_LAST_STOCK_NON_LOG, atol=tol)
    assert np.isclose(np.expm1(hist.bonds_log[-1]), PINNED_LAST_BOND_NON_LOG, atol=tol)


def test_history_is_frozen() -> None:
    hist = load_historical_returns()

    try:
        hist.stocks_log = np.array([0.0])  # type: ignore[misc]
    except (AttributeError, TypeError):
        return
    raise AssertionError("HistoricalReturns should be immutable")
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a LOGICAL failure**

Create `packages/simulation/simulation/market_data/returns.py` with structure but stub logic:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_RETURNS_CSV = _DATA_DIR / "v7_real_monthly_returns.csv"
V7_EFFECTIVE_DATE = date(2026, 1, 15)


@dataclass(frozen=True, eq=False)
class HistoricalReturns:
    stocks_log: np.ndarray
    bonds_log: np.ndarray
    start: tuple[int, int]
    effective_date: date

    @property
    def length(self) -> int:
        return int(self.stocks_log.shape[0])


def _load_from_csv(path: Path) -> HistoricalReturns:
    raise NotImplementedError


@lru_cache(maxsize=1)
def load_historical_returns() -> HistoricalReturns:
    return _load_from_csv(_DEFAULT_RETURNS_CSV)
```

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_returns.py -v
```

Expected: FAIL with `NotImplementedError` (logical), not `ImportError`/`AttributeError`. If structural, fix names first.

- [ ] **Step 3: Implement `_load_from_csv`**

Replace the `_load_from_csv` body in `returns.py`:

```python
def _load_from_csv(path: Path) -> HistoricalReturns:
    import csv

    years: list[int] = []
    months: list[int] = []
    stocks: list[float] = []
    bonds: list[float] = []
    # utf-8-sig strips the BOM present in the vendored tpaw CSV.
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            years.append(int(row["year"]))
            months.append(int(row["month"]))
            stocks.append(float(row["stock real return"]))
            bonds.append(float(row["bond real return"]))

    stocks_non_log = np.asarray(stocks, dtype=np.float64)
    bonds_non_log = np.asarray(bonds, dtype=np.float64)
    return HistoricalReturns(
        stocks_log=np.log1p(stocks_non_log),
        bonds_log=np.log1p(bonds_non_log),
        start=(years[0], months[0]),
        effective_date=V7_EFFECTIVE_DATE,
    )
```

- [ ] **Step 4: Run the tests — must pass**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_returns.py -v
```

Expected: PASS (all 5 tests, including the faithful-port guard against the real vendored CSV).

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/market_data/returns.py \
        packages/simulation/tests/market_data/__init__.py \
        packages/simulation/tests/market_data/test_returns.py
git commit -m "feat(simulation): load vendored historical returns as log series"
```

---

## Task 5: `bootstrap.py` — staggered block-bootstrap sampler

Port of tpaw `generate_random_index_sequences` (`utils/random.rs`). `build_index_sequences` is exposed separately so tests can assert on indices directly; `build_return_paths` gathers from the historical log series.

**Files:**
- Create: `packages/simulation/simulation/market_data/bootstrap.py`
- Test: `packages/simulation/tests/market_data/test_bootstrap.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/simulation/tests/market_data/test_bootstrap.py`:

```python
from __future__ import annotations

import numpy as np
from core.defaults import default_plan
from core.models import SamplingConfig
from simulation.market_data.bootstrap import (
    ReturnPaths,
    build_index_sequences,
    build_return_paths,
)
from simulation.market_data.returns import load_historical_returns


def _sequences(*, seed: int, num_runs: int, months: int, block_size: int, length: int,
               stagger: bool = True) -> np.ndarray:
    return build_index_sequences(
        seed=seed,
        num_runs=num_runs,
        months_per_run=months,
        block_size=block_size,
        length=length,
        stagger_run_starts=stagger,
    )


def test_sequence_shape_matches_runs_and_months() -> None:
    num_runs, months = 7, 40

    seqs = _sequences(seed=1, num_runs=num_runs, months=months, block_size=12, length=600)

    assert seqs.shape == (num_runs, months)


def test_same_seed_is_deterministic() -> None:
    kwargs = dict(num_runs=5, months=30, block_size=12, length=600)

    a = _sequences(seed=42, **kwargs)
    b = _sequences(seed=42, **kwargs)

    assert np.array_equal(a, b)


def test_different_seed_changes_sequences() -> None:
    kwargs = dict(num_runs=5, months=30, block_size=12, length=600)

    a = _sequences(seed=1, **kwargs)
    b = _sequences(seed=2, **kwargs)

    assert not np.array_equal(a, b)


def test_all_indices_are_within_series_bounds() -> None:
    length = 600

    seqs = _sequences(seed=3, num_runs=10, months=120, block_size=60, length=length)

    assert seqs.min() >= 0
    assert seqs.max() < length


def test_within_block_indices_are_consecutive_mod_length() -> None:
    length = 600
    block_size = 12
    # No staggering so block 0 spans months [0, block_size).
    seqs = _sequences(seed=4, num_runs=1, months=block_size, block_size=block_size,
                      length=length, stagger=False)

    run = seqs[0]
    steps = (run[1:] - run[:-1]) % length
    assert np.all(steps == 1)


def test_staggering_offsets_block_boundary_across_runs() -> None:
    length = 600
    block_size = 12
    # With stagger, run_index r starts at offset r % block_size into its first block,
    # so the first block boundary (where index jumps) shifts by run.
    seqs = _sequences(seed=5, num_runs=2, months=block_size * 2, block_size=block_size,
                      length=length, stagger=True)

    def first_break(run: np.ndarray) -> int:
        steps = (run[1:] - run[:-1]) % length
        return int(np.argmax(steps != 1))

    assert first_break(seqs[0]) != first_break(seqs[1])


def test_build_return_paths_gathers_both_assets_with_metadata() -> None:
    plan = default_plan()
    plan.sampling = SamplingConfig(num_runs=8, block_size_months=24, seed=99)
    months = 36

    paths = build_return_paths(plan, months_per_run=months)

    hist = load_historical_returns()
    assert isinstance(paths, ReturnPaths)
    assert paths.stocks_log.shape == (plan.sampling.num_runs, months)
    assert paths.bonds_log.shape == (plan.sampling.num_runs, months)
    assert paths.num_runs == plan.sampling.num_runs
    assert paths.months_per_run == months
    assert paths.block_size == plan.sampling.block_size_months
    assert paths.seed == plan.sampling.seed
    # Every sampled value is a member of the source log series.
    assert np.isin(paths.stocks_log, hist.stocks_log).all()


def test_build_return_paths_is_deterministic_under_same_seed() -> None:
    plan = default_plan()
    plan.sampling = SamplingConfig(num_runs=4, block_size_months=24, seed=7)

    a = build_return_paths(plan, months_per_run=24)
    b = build_return_paths(plan, months_per_run=24)

    assert np.array_equal(a.stocks_log, b.stocks_log)
    assert np.array_equal(a.bonds_log, b.bonds_log)
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a LOGICAL failure**

Create `packages/simulation/simulation/market_data/bootstrap.py`:

```python
from __future__ import annotations

from datetime import date

import numpy as np
from core.models import Plan
from pydantic import BaseModel, ConfigDict

from simulation.market_data.returns import load_historical_returns


class ReturnPaths(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    stocks_log: np.ndarray
    bonds_log: np.ndarray
    seed: int
    block_size: int
    num_runs: int
    months_per_run: int


def build_index_sequences(
    *,
    seed: int,
    num_runs: int,
    months_per_run: int,
    block_size: int,
    length: int,
    stagger_run_starts: bool,
) -> np.ndarray:
    raise NotImplementedError


def build_return_paths(
    plan: Plan,
    *,
    months_per_run: int,
    today: date | None = None,
) -> ReturnPaths:
    raise NotImplementedError
```

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_bootstrap.py -v
```

Expected: FAIL with `NotImplementedError` (logical). If structural (`ImportError`, etc.), fix scaffolding first.

- [ ] **Step 3: Implement the sampler**

Replace the two function bodies in `bootstrap.py`:

```python
def build_index_sequences(
    *,
    seed: int,
    num_runs: int,
    months_per_run: int,
    block_size: int,
    length: int,
    stagger_run_starts: bool,
) -> np.ndarray:
    # Two-level seeding mirrors tpaw: a parent RNG produces a per-run seed, then
    # each run draws its own block-start months. Algorithmic parity, our own
    # determinism (not bit-identical to tpaw's ChaCha8 streams).
    parent = np.random.default_rng(seed)
    run_seeds = parent.integers(0, np.iinfo(np.int64).max, size=num_runs)

    # One extra block for the remainder, one extra for staggering.
    num_blocks = months_per_run // block_size + 2
    month_offsets = np.arange(months_per_run)

    sequences = np.empty((num_runs, months_per_run), dtype=np.int64)
    for run_index in range(num_runs):
        run_rng = np.random.default_rng(int(run_seeds[run_index]))
        block_starts = run_rng.integers(0, length, size=num_blocks)
        stagger = run_index % block_size if stagger_run_starts else 0
        staggered = month_offsets + stagger
        block_index = staggered // block_size
        sequences[run_index] = (block_starts[block_index] + staggered % block_size) % length
    return sequences


def build_return_paths(
    plan: Plan,
    *,
    months_per_run: int,
    today: date | None = None,
) -> ReturnPaths:
    _ = today  # reserved: per-run inflation/return paths may key off today later
    hist = load_historical_returns()
    sampling = plan.sampling
    sequences = build_index_sequences(
        seed=sampling.seed,
        num_runs=sampling.num_runs,
        months_per_run=months_per_run,
        block_size=sampling.block_size_months,
        length=hist.length,
        stagger_run_starts=sampling.stagger_run_starts,
    )
    return ReturnPaths(
        stocks_log=hist.stocks_log[sequences],
        bonds_log=hist.bonds_log[sequences],
        seed=sampling.seed,
        block_size=sampling.block_size_months,
        num_runs=sampling.num_runs,
        months_per_run=months_per_run,
    )
```

- [ ] **Step 4: Run the tests — must pass**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_bootstrap.py -v
```

Expected: PASS (all 8 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/market_data/bootstrap.py \
        packages/simulation/tests/market_data/test_bootstrap.py
git commit -m "feat(simulation): port staggered block-bootstrap return sampler"
```

---

## Task 6: Vendor the FRED `T10YIE` CSV + provenance

**Files:**
- Create: `packages/simulation/simulation/market_data/data/t10yie_daily.csv` (downloaded)
- Modify: `packages/simulation/simulation/market_data/data/PROVENANCE.md` (fill download date)

- [ ] **Step 1: Download the FRED breakeven inflation series (no API key needed)**

Run:

```bash
curl -fsSL "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10YIE" \
  -o packages/simulation/simulation/market_data/data/t10yie_daily.csv
```

- [ ] **Step 2: Verify the file**

Run:

```bash
head -3 packages/simulation/simulation/market_data/data/t10yie_daily.csv
tail -2 packages/simulation/simulation/market_data/data/t10yie_daily.csv
```

Expected: a header line whose first column is the observation date and second is `T10YIE`; data rows like `2003-01-02,1.65`; some rows may have `.` for missing values. The loader (Task 7) reads columns positionally and skips the header + non-numeric values, so the exact header text does not matter.

- [ ] **Step 3: Fill in the download date in provenance**

Edit `packages/simulation/simulation/market_data/data/PROVENANCE.md` — replace `<FILL IN download date when Task 6 runs>` with today's date (e.g. `2026-06-27`).

- [ ] **Step 4: Commit**

```bash
git add packages/simulation/simulation/market_data/data/t10yie_daily.csv \
        packages/simulation/simulation/market_data/data/PROVENANCE.md
git commit -m "chore(simulation): vendor FRED T10YIE breakeven inflation series"
```

---

## Task 7: `inflation.py` — suggested / manual resolution

Port of tpaw's inflation handling: suggested = latest `T10YIE` at-or-before `today`, parsed percent → decimal, rounded to 3 dp (half away from zero, matching tpaw `RoundP`); manual = configured rate; annual → monthly via `(1 + annual) ** (1/12) - 1`.

**Files:**
- Create: `packages/simulation/simulation/market_data/inflation.py`
- Test: `packages/simulation/tests/market_data/test_inflation.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/simulation/tests/market_data/test_inflation.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from core.defaults import default_plan
from core.models import InflationConfig
from simulation.market_data.inflation import (
    InflationResolved,
    annual_to_monthly,
    resolve_inflation,
)


def _write_t10yie(path: Path, rows: list[str]) -> Path:
    path.write_text("\n".join(["observation_date,T10YIE", *rows]) + "\n", encoding="utf-8")
    return path


def _suggested_plan():
    plan = default_plan()
    plan.inflation = InflationConfig(mode="suggested")
    return plan


def test_annual_to_monthly_matches_compounding_formula() -> None:
    annual = 0.03

    monthly = annual_to_monthly(annual)

    assert (1 + monthly) ** 12 == pytest.approx(1 + annual)


def test_suggested_uses_latest_observation_at_or_before_today(tmp_path: Path) -> None:
    # second value is after the date used for today, so it's ignored
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,2.5"])

    resolved = resolve_inflation(_suggested_plan(), today=date(2026, 1, 15), t10yie_path=csv)

    assert resolved.source == "suggested"
    assert resolved.annual == pytest.approx(0.020)


def test_suggested_picks_exact_match_on_observation_date(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,2.5"])

    resolved = resolve_inflation(_suggested_plan(), today=date(2026, 2, 1), t10yie_path=csv)

    assert resolved.annual == pytest.approx(0.025)


def test_suggested_skips_non_numeric_rows(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.0", "2026-02-01,."])

    resolved = resolve_inflation(_suggested_plan(), today=date(2026, 2, 15), t10yie_path=csv)

    assert resolved.annual == pytest.approx(0.020)


def test_suggested_rounds_to_three_decimal_places(tmp_path: Path) -> None:
    # 2.37% -> 0.0237 -> round half-away to 3 dp -> 0.024
    csv = _write_t10yie(tmp_path / "t.csv", ["2026-01-01,2.37"])

    resolved = resolve_inflation(_suggested_plan(), today=date(2026, 1, 2), t10yie_path=csv)

    assert resolved.annual == pytest.approx(0.024)


def test_manual_mode_uses_configured_rate(tmp_path: Path) -> None:
    expected_annual = Decimal("0.031")
    plan = default_plan()
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=expected_annual)

    resolved = resolve_inflation(plan, today=date(2026, 1, 2))

    assert resolved.source == "manual"
    assert resolved.annual == pytest.approx(float(expected_annual))
    assert resolved.monthly == pytest.approx(annual_to_monthly(float(expected_annual)))


def test_resolve_returns_inflation_resolved_type() -> None:
    plan = default_plan()
    plan.inflation = InflationConfig(mode="manual", manual_annual_rate=Decimal("0.02"))

    resolved = resolve_inflation(plan, today=date(2026, 1, 2))

    assert isinstance(resolved, InflationResolved)
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a LOGICAL failure**

Create `packages/simulation/simulation/market_data/inflation.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from core.models import Plan

_DATA_DIR = Path(__file__).parent / "data"
_DEFAULT_T10YIE_CSV = _DATA_DIR / "t10yie_daily.csv"


@dataclass(frozen=True)
class InflationResolved:
    annual: float
    monthly: float
    source: Literal["suggested", "manual"]


def annual_to_monthly(annual: float) -> float:
    raise NotImplementedError


def resolve_inflation(
    plan: Plan,
    *,
    today: date | None = None,
    t10yie_path: Path | None = None,
) -> InflationResolved:
    raise NotImplementedError
```

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py -v
```

Expected: FAIL with `NotImplementedError` (logical), not structural.

- [ ] **Step 3: Implement resolution**

Replace the function bodies in `inflation.py`:

```python
import csv
from decimal import ROUND_HALF_UP, Decimal


def annual_to_monthly(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def _round_half_away(value: Decimal, places: str = "0.001") -> Decimal:
    # ROUND_HALF_UP rounds half away from zero, matching Rust f64::round (tpaw RoundP).
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _suggested_annual(today: date, path: Path) -> float:
    best_date: date | None = None
    best_value: Decimal | None = None
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)  # header
        for row in reader:
            if len(row) < 2:
                continue
            try:
                observed = date.fromisoformat(row[0].strip())
                percent = Decimal(row[1].strip())  # raises for "." / blanks
            except (ValueError, ArithmeticError):
                continue
            if observed > today:
                continue
            if best_date is None or observed > best_date:
                best_date = observed
                best_value = percent
    if best_value is None:
        raise ValueError(f"no T10YIE observation at or before {today.isoformat()}")
    return float(_round_half_away(best_value / Decimal(100)))


def resolve_inflation(
    plan: Plan,
    *,
    today: date | None = None,
    t10yie_path: Path | None = None,
) -> InflationResolved:
    today = today or date.today()
    if plan.inflation.mode == "manual":
        rate = plan.inflation.manual_annual_rate
        if rate is None:
            raise ValueError("manual inflation mode requires manual_annual_rate")
        annual = float(rate)
        source: Literal["suggested", "manual"] = "manual"
    else:
        annual = _suggested_annual(today, t10yie_path or _DEFAULT_T10YIE_CSV)
        source = "suggested"
    return InflationResolved(annual=annual, monthly=annual_to_monthly(annual), source=source)
```

Move the `import csv` and `from decimal import ...` lines to the top of the module with the other imports (keep them out of the function bodies).

- [ ] **Step 4: Run the tests — must pass**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py -v
```

Expected: PASS (all 8 tests).

- [ ] **Step 5: Sanity-check suggested resolution against the real vendored file**

Run:

```bash
uv run python -c "from datetime import date; from core.defaults import default_plan; from core.models import InflationConfig; from simulation.market_data.inflation import resolve_inflation; p=default_plan(); p.inflation=InflationConfig(mode='suggested'); print(resolve_inflation(p, today=date(2026,1,1)))"
```

Expected: prints an `InflationResolved(annual=..., monthly=..., source='suggested')` with a plausible annual rate (~0.02–0.03).

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/market_data/inflation.py \
        packages/simulation/tests/market_data/test_inflation.py
git commit -m "feat(simulation): resolve suggested/manual scalar inflation"
```

---

## Task 8: Public API re-exports

**Files:**
- Modify: `packages/simulation/simulation/market_data/__init__.py`
- Modify: `packages/simulation/simulation/__init__.py`
- Test: `packages/simulation/tests/market_data/test_public_api.py`

- [ ] **Step 1: Write the failing smoke test**

One integration smoke test exercises the package-root public API end-to-end (re-exports +
real implementations). Submodule unit tests in Tasks 4–7 cover behavior in depth; no
separate `is not None` / identity wiring tests.

Create `packages/simulation/tests/market_data/test_public_api.py`:

```python
from __future__ import annotations

from datetime import date

from core.defaults import default_plan
from simulation import build_return_paths, resolve_inflation


def test_public_api_smoke() -> None:
    plan = default_plan()
    months = 12

    paths = build_return_paths(plan, months_per_run=months)
    inflation = resolve_inflation(plan, today=date(2026, 1, 1))

    assert paths.stocks_log.shape == (plan.sampling.num_runs, months)
    assert inflation.source == "suggested"
```

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_public_api.py -v
```

Expected: FAIL with `ImportError` for the not-yet-exported names (structural failure
*is* the behavior under test until Step 3 wires `simulation/__init__.py`).

- [ ] **Step 2: Implement the market_data re-exports**

Replace `packages/simulation/simulation/market_data/__init__.py`:

```python
"""Market data: vendored historical returns, bootstrap sampler, inflation."""

from simulation.market_data.bootstrap import ReturnPaths, build_return_paths
from simulation.market_data.inflation import InflationResolved, resolve_inflation
from simulation.market_data.returns import HistoricalReturns, load_historical_returns

__all__ = [
    "HistoricalReturns",
    "InflationResolved",
    "ReturnPaths",
    "build_return_paths",
    "load_historical_returns",
    "resolve_inflation",
]
```

- [ ] **Step 3: Implement the package-root re-exports**

Modify `packages/simulation/simulation/__init__.py` to add the market-data API alongside the existing exports:

```python
"""Monthly TPAW simulation engine."""

from core.timeline import horizon_months, person_end_date

from simulation.market_data import (
    HistoricalReturns,
    InflationResolved,
    ReturnPaths,
    build_return_paths,
    load_historical_returns,
    resolve_inflation,
)
from simulation.result import STUB_VERSION, SimulationResult
from simulation.stub import run_simulation

__all__ = [
    "STUB_VERSION",
    "HistoricalReturns",
    "InflationResolved",
    "ReturnPaths",
    "SimulationResult",
    "build_return_paths",
    "horizon_months",
    "load_historical_returns",
    "person_end_date",
    "resolve_inflation",
    "run_simulation",
]
```

- [ ] **Step 4: Run the test — must pass**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_public_api.py -v
```

Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/market_data/__init__.py \
        packages/simulation/simulation/__init__.py \
        packages/simulation/tests/market_data/test_public_api.py
git commit -m "feat(simulation): expose market-data public API"
```

---

## Task 9: Update the rebuild index (divergence per spec §9)

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Update the Phase 3a "Delivers" line and exit criteria**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, locate the `### Phase 3a — Simulation: market data and bootstrap` section (around line 226).

Replace the `**Delivers:**` line:

```markdown
**Delivers:** Port tpaw historical monthly data; block-bootstrap real return paths; scalar inflation (suggested vendored breakeven + manual override).
```

Replace the exit-criteria checklist with:

```markdown
**Exit criteria:**

- [ ] tpaw v7 data vendored with attribution (returns CSV + FRED T10YIE)
- [ ] Block-bootstrap produces `(num_runs, months_per_run)` monthly log-return paths per asset
- [ ] Inflation: scalar suggested (vendored breakeven) + manual override; bootstrapped inflation paths deferred (interface left open, [#186](https://github.com/chriskelly/LifeFinances/issues/186))
- [ ] Sampling: tpaw defaults on `Plan` + advanced overrides (UI wiring deferred to Phase 4)
```

- [ ] **Step 2: Update the index "Current phase / Next action" header**

Near the top (around lines 37–39), update the status table so it no longer says the plan is unwritten:

```markdown
| **Current phase** | Phase 3a — execute                                          |
| **Active plan**   | `2026-06-12-phase-3a-simulation-market-data.md`             |
| **Next action**   | Execute Phase 3a plan task-by-task                          |
```

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "docs(plan): update Phase 3a exit criteria for scalar-inflation divergence"
```

---

## Task 10: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the whole simulation + core suite**

Run:

```bash
uv run pytest packages/simulation packages/core -q
```

Expected: PASS, no failures.

- [ ] **Step 2: Run the full project gate**

Run:

```bash
make
```

Expected: `make` runs `test` then `lint` (ruff check + ruff format check + pyright) and exits 0. If pyright flags numpy array typing on the pydantic `ReturnPaths` model, the `model_config = ConfigDict(arbitrary_types_allowed=True)` already permits it at runtime; if a type error remains, narrow the annotation (e.g. `np.ndarray`) rather than disabling the rule.

- [ ] **Step 3: Confirm no stray working-tree changes (e.g. `data/data.db`)**

Run:

```bash
git status
```

Expected: clean tree except intended commits; `data/data.db` must NOT be staged.

---

## Self-Review

**Spec coverage:**

| Spec section | Covered by |
| ------------ | ---------- |
| §3 Data vendoring & loading | Task 3 (vendor CSV + provenance), Task 4 (`returns.py` load + log) |
| §3 Faithful-port guard | Task 4 Step 1 (`test_vendored_csv_is_faithful_port_of_tpaw_source`) |
| §4 Block-bootstrap sampler + `ReturnPaths` | Task 5 |
| §4 Determinism | Task 5 (`test_same_seed_is_deterministic`, `test_build_return_paths_is_deterministic_under_same_seed`) |
| §5 Inflation suggested/manual + annual→monthly | Task 6 (vendor T10YIE), Task 7 (`inflation.py`) |
| §6 Config models on `Plan` | Task 2 |
| §7 Public API | Task 8 |
| §8 Testing | Tasks 2,4,5,7,8 (TDD throughout) |
| §9 Divergence from rebuild index | Task 9 |
| §10 Phase 3a+ networked data | Out of scope (deferred; no task — correct) |

**Type consistency check:**
- `HistoricalReturns` (frozen dataclass): `stocks_log`, `bonds_log`, `start`, `effective_date`, `.length` property — used consistently in Tasks 4, 5.
- `ReturnPaths` (pydantic): `stocks_log`, `bonds_log`, `seed`, `block_size`, `num_runs`, `months_per_run` — defined Task 5, asserted in Task 5 tests, re-exported Task 8.
- `InflationResolved` (frozen dataclass): `annual`, `monthly`, `source` — defined Task 7, used in Task 7 tests, re-exported Task 8.
- `SamplingConfig` fields: `block_size_months`, `num_runs`, `stagger_run_starts`, `seed` — defined Task 2, read in `build_return_paths` (Task 5) and tests.
- `InflationConfig` fields: `mode`, `manual_annual_rate` — defined Task 2, read in `resolve_inflation` (Task 7).
- `build_index_sequences(*, seed, num_runs, months_per_run, block_size, length, stagger_run_starts)` — same signature in Task 5 scaffolding, implementation, and tests' `_sequences` helper.
- `resolve_inflation(plan, *, today=None, t10yie_path=None)` and `annual_to_monthly(annual)` — consistent across Task 7 scaffolding, impl, tests.

**Placeholder scan:** No `TBD`/`implement later`/"add validation" placeholders; every code step shows complete code. The one intentional `<FILL IN download date>` is a provenance value that can only be known at download time (Task 6 Step 3 fills it).

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-12-phase-3a-simulation-market-data.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session with checkpoints for review.

Which approach?

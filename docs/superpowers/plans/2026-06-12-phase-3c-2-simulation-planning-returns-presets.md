# Phase 3c-2 — Planning-Returns Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Phase 3b's fixed/manual planning returns with full-tpaw-parity market-data-derived expected-return presets (CAPE regression, conservative estimate, 1/CAPE, historical, fixed-equity-premium, custom, fixed) plus empirical variance-by-block-size, consuming the Phase 3c-1 S&P/Treasury feeds with vendored fallback.

**Architecture:** Pure preset math in `simulation/presets.py` (I/O-free, doctest-golden testable) fed by vendored constants (v7 CAPE regression coefficients + Shiller earnings + variance-by-block table) and the already-loaded v7 historical series. `resolve_planning_returns` dispatches on the selected preset, lazily calling the Phase 3c-1 `resolve_latest_sp500_close` / `resolve_treasury_real_yields` resolvers (each cache→vendored) only when the preset needs them. The frozen `PlanningReturns` return shape is unchanged, so `preprocess`/`engine` downstream are untouched.

**Tech Stack:** Python 3.14+, uv workspace, numpy, Pydantic v2, pytest. Package boundary: `simulation → domain, core`; `simulation` never reads secrets (keys injected at the web/CLI boundary).

**Design spec:** `docs/superpowers/specs/2026-07-05-phase-3c-2-simulation-planning-returns-presets-design.md`

---

## Reference: verified tpaw parity facts

These are extracted from tpaw and MUST be reproduced exactly. Do not re-derive.

**v7 CAPE regression coefficients** (predict `annual_log_mean = slope·ln(1 + 1/CAPE) + intercept`), ordering `full` then `restricted`, each `[5, 10, 20, 30]`-year:

| key | slope | intercept |
| --- | ----- | --------- |
| full_5 | `1.0186750091739176` | `-0.0030196513070538944` |
| full_10 | `0.8872973208298874` | `0.003678563136717744` |
| full_20 | `0.6013906822070715` | `0.0209753430373825` |
| full_30 | `0.2534226892459835` | `0.044901708118683506` |
| restricted_5 | `0.9649252188371695` | `0.014643434263680727` |
| restricted_10 | `1.088798216190916` | `0.0007109393929390362` |
| restricted_20 | `0.8480459980120469` | `0.006791270853428094` |
| restricted_30 | `0.2658049833900813` | `0.04523120587150688` |

**Shiller 10-yr avg real earnings (latest v7 entry):** `170.80` (added 2026-01-15, `added_date_ms = 1768510800000`, ten-year window 2015-10 → 2025-09).

**Non-log conversion** (tpaw `get_empirical_annual_non_log_from_log_monthly_expected_value` with `block_size=None`, `scale=1.0` for the preset menu):

```
monthly_log_mean   = mean(v7 stock monthly log returns)              # self.log.stats.mean
annualized_non_log = mean(exp(rolling_12_sum(log returns)) - 1)      # annualized_stats.non_log.mean
correction         = (ln(1 + annualized_non_log) / 12 - monthly_log_mean) * scale**2   # scale=1.0
annual_non_log(annual_log_mean) = exp((annual_log_mean/12 + correction) * 12) - 1
```

`rolling_12_sum` = overlapping windows of 12 consecutive monthly log returns (tpaw `periodize_log_returns`; output length = n − 11).

**Preset definitions** (rounded to 3 dp, half-away-from-zero, matching tpaw `round_p(3)`, EXCEPT historical which tpaw leaves unrounded):

- `one_over_cape = shiller_10yr_real_earnings / sp500_close`; stock base = `round3(one_over_cape)`.
- 8 regression predictions = `annual_non_log(slope·ln(1+one_over_cape)+intercept)` for each coeff.
- `regression_prediction = round3(mean(8 regression predictions))`.
- `conservative_estimate = round3(mean(4 lowest of [one_over_cape, *8 regression predictions]))`.
- `historical_stocks` / `historical_bonds` = unrounded `annualized_non_log` (tpaw does not `round_p(3)` these).
- `tips_yield_20_year` = `round3(20-yr Treasury real yield)` (tpaw rounds in `source_rounded.bond_rates`).

**Planning variance (ALWAYS, every preset incl. `fixed`):**
`annual_stock_log_variance = variance_by_block[sampling.block_size_months] * stock_volatility_scale**2`.
tpaw v7 table: block 1 → `0.019750483`, block 60 → `0.03222578`, block 1440 → `0.03276835`.

**Golden preset outputs** for `sp500_close=7517.09`, `shiller=170.80`, `tips_20yr=0.026`, vendored v7 series:

| quantity | value |
| -------- | ----- |
| `one_over_cape` (raw) | `0.022721558475420674` |
| `round3(one_over_cape)` | `0.023` |
| `regression_prediction` | `0.05` |
| `conservative_estimate` | `0.035` |
| `historical_stocks` | `0.08714729363432962` (unrounded) |
| `historical_bonds` | `0.0277107658439772` (unrounded) |
| `monthly_log_mean` (v7 stocks) | `0.005697611027897666` |
| `annualized_non_log` (v7 stocks) | `0.08714729363432962` |

**Which resolver each preset needs:**

| preset | needs S&P | needs Treasury |
| ------ | --------- | -------------- |
| `regression_prediction` | yes | yes (20yr) |
| `conservative_estimate` | yes | yes (20yr) |
| `one_over_cape` | yes | yes (20yr) |
| `historical` | no | no |
| `fixed_equity_premium` | no | yes (20yr) |
| `custom` | only if a stock base ∈ {regression, conservative, one_over_cape} | only if bond base = 20yr TIPS |
| `fixed` | no | no |

---

## File Structure

- Create: `packages/simulation/simulation/market_data/data/cape_regression_v7.json` — vendored coeffs + Shiller earnings + provenance.
- Create: `packages/simulation/simulation/market_data/data/stock_log_variance_by_block.csv` — vendored v7 variance table (1440 rows).
- Create: `packages/simulation/simulation/market_data/presets_data.py` — loaders for the two new vendored files.
- Create: `packages/simulation/simulation/presets.py` — pure preset math.
- Modify: `packages/core/core/models.py` — expand `PlanningReturnsConfig` + validators + constants.
- Modify: `packages/simulation/simulation/planning_returns.py` — preset dispatch + injected seam; table-based variance.
- Modify: `packages/simulation/simulation/preprocess.py` — thread `allow_refresh`/`now`/keys into both resolvers.
- Modify: `packages/simulation/simulation/stub.py` — thread `allow_refresh`/keys into `preprocess`.
- Modify: `packages/web/web/app.py` — forward `AppSettings` keys as live-refresh on `home`/`results` routes.
- Modify: `packages/simulation/simulation/market_data/data/PROVENANCE.md` — new source entries.
- Modify tests: `packages/simulation/tests/test_planning_returns.py`, `packages/simulation/tests/test_preprocess.py`, `packages/web/tests/test_app.py` (one integration smoke test in Task 9).
- Create tests: `packages/simulation/tests/test_presets.py`.
- Modify: `packages/core/tests/test_risk_and_planning_returns_config.py` — add preset-mode validator tests only.
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` — correct Phase 3c exit criteria.
- Modify: `packages/simulation/OVERVIEW.md` — record preset parity status.

---

## Testing policy (AGENTS.md §108–126)

Apply on every task that adds or changes tests:

1. **Our logic only** — no tests for Pydantic defaults, trivial field assignment, `isinstance` checks, or framework wiring. Validator rules we write (`_require_mode_fields`), preset math, dispatch, resolver fallback, and preprocess guards are in scope.
2. **Avoid fragile values** — bind any literal used in both arrange and assert to one variable (or derive the expected value from the same inputs via a helper).
3. **Pull constants from source** — import defaults, `REGRESSION_KEYS`, `DEFAULT_BLOCK_SIZE_MONTHS`, loader outputs, and helper functions from production code. Inline literals only in **contract tests** pinned to tpaw; comment `# pinned: tpaw …` and keep inputs/outputs in one named block at the top of the test module.
4. **TDD flow per task** — write failing test → add minimal scaffolding until failure is **logical** (`AssertionError`, `NotImplementedError`, `ValidationError`), not structural → implement → run green. Do not checklist a separate "structural failure" pytest run as its own step.

**Contract-test module:** `packages/simulation/tests/tpaw_preset_contract.py` holds the single pinned input tuple (`sp500_close`, `tips_20yr`) and expected rounded preset outputs for tpaw v7 parity. `test_presets.py` imports from it — golden values are not scattered across tests.

**Loader tests:** folded into `test_presets.py` (smoke that loaders feed the math) — no separate `test_presets_data.py` that only re-asserts vendored file literals.

---

## Task 1: Vendor CAPE regression coefficients + Shiller earnings

**Files:**
- Create: `packages/simulation/simulation/market_data/data/cape_regression_v7.json`
- Modify: `packages/simulation/simulation/market_data/data/PROVENANCE.md`

- [ ] **Step 1: Write the vendored JSON**

Create `packages/simulation/simulation/market_data/data/cape_regression_v7.json` with exactly:

```json
{
  "version": "v7",
  "effective_date": "2026-01-15",
  "effective_timestamp_ms": 1768510800000,
  "shiller_10yr_real_earnings": 170.80,
  "shiller_window": { "start": "2015-10", "end": "2025-09" },
  "regression_coeffs": {
    "full_5": [1.0186750091739176, -0.0030196513070538944],
    "full_10": [0.8872973208298874, 0.003678563136717744],
    "full_20": [0.6013906822070715, 0.0209753430373825],
    "full_30": [0.2534226892459835, 0.044901708118683506],
    "restricted_5": [0.9649252188371695, 0.014643434263680727],
    "restricted_10": [1.088798216190916, 0.0007109393929390362],
    "restricted_20": [0.8480459980120469, 0.006791270853428094],
    "restricted_30": [0.2658049833900813, 0.04523120587150688]
  }
}
```

- [ ] **Step 2: Append the provenance entry**

Add to `packages/simulation/simulation/market_data/data/PROVENANCE.md`:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add packages/simulation/simulation/market_data/data/cape_regression_v7.json packages/simulation/simulation/market_data/data/PROVENANCE.md
git commit -m "feat(simulation): vendor v7 CAPE regression coefficients and Shiller earnings"
```

---

## Task 2: Vendor v7 stock variance-by-block-size table

**Files:**
- Create: `packages/simulation/simulation/market_data/data/stock_log_variance_by_block.csv`
- Modify: `packages/simulation/simulation/market_data/data/PROVENANCE.md`

- [ ] **Step 1: Extract the table from tpaw (maintainer one-off)**

Run this from the repo root; it reads tpaw's `.rs` array and writes the vendored CSV. It skips index 0 (tpaw's dummy placeholder) so `block_size` runs 1..1440:

```bash
uv run python - <<'PY'
import re
from pathlib import Path

src = Path("../tpaw/packages/simulator-rust/src/lib/historical_monthly_returns/data/v7/v7_empirical_stats_by_block_size_stocks.rs")
text = src.read_text()
# EmpiricalStats32::new(annual_non_log_returns_mean, annual_log_returns_variance)
matches = re.findall(r"EmpiricalStats32::new\(\s*([-\d.eE]+)\s*,\s*([-\d.eE]+)\s*\)", text)
assert len(matches) == 1441, f"expected 1441 entries (index 0..1440), got {len(matches)}"

out = Path("packages/simulation/simulation/market_data/data/stock_log_variance_by_block.csv")
with out.open("w", newline="") as f:
    f.write("block_size,annual_log_returns_variance\n")
    for i, (_mean, var) in enumerate(matches):
        if i == 0:
            continue  # tpaw dummy placeholder
        f.write(f"{i},{var}\n")

# Verify pinned values.
rows = out.read_text().splitlines()
assert rows[1] == "1,0.019750483", rows[1]
assert any(r == "60,0.03222578" for r in rows), "block 60 variance mismatch"
assert rows[-1] == "1440,0.03276835", rows[-1]
assert len(rows) == 1441, f"expected header + 1440 rows, got {len(rows)}"
print("wrote", out, "rows:", len(rows) - 1)
PY
```

Expected output: `wrote .../stock_log_variance_by_block.csv rows: 1440`

- [ ] **Step 2: Append the provenance entry**

Add to `PROVENANCE.md`:

```markdown
## stock_log_variance_by_block.csv

- **Source:** TPAW simulator-rust `v7_empirical_stats_by_block_size_stocks.rs`
  (`annual_log_returns_variance` column; `annual_non_log_returns_mean` not vendored).
- **Version:** v7 (effective 2026-01-15).
- **Generation (upstream):** 500,000-run block-bootstrap, 600 months/run, staggered
  starts, fixed seed — precomputed by tpaw, copied verbatim (index 0 dummy dropped).
- **Columns:** `block_size` (1..1440 months), `annual_log_returns_variance`.
- **Use:** Phase 3c-2 planning stock variance = `table[sampling.block_size_months] × stock_volatility_scale²`.
- **Attribution:** TPAW by Ben Mathew (https://tpawplanner.com).
```

- [ ] **Step 3: Commit**

```bash
git add packages/simulation/simulation/market_data/data/stock_log_variance_by_block.csv packages/simulation/simulation/market_data/data/PROVENANCE.md
git commit -m "feat(simulation): vendor v7 stock log variance-by-block-size table"
```

---

## Task 3: Expand `PlanningReturnsConfig` (full-parity model)

**Files:**
- Modify: `packages/core/core/models.py:31-32,74-76`
- Modify: `packages/core/tests/test_risk_and_planning_returns_config.py` — add validator tests only

- [ ] **Step 1: Write the failing tests**

Append to `packages/core/tests/test_risk_and_planning_returns_config.py` (do **not** add default/field-assignment tests — those are Pydantic wiring, out of scope per AGENTS.md):

```python
import pytest
from pydantic import ValidationError

from core.models import PlanningReturnsConfig


def test_fixed_equity_premium_preset_requires_premium_field():
    with pytest.raises(ValidationError, match="fixed_equity_premium"):
        PlanningReturnsConfig(preset="fixed_equity_premium")


def test_custom_preset_requires_both_bases():
    with pytest.raises(ValidationError, match="custom"):
        PlanningReturnsConfig(preset="custom", custom_stocks_base="historical")
```

- [ ] **Step 2: Run test — expect logical failure after scaffolding**

Run: `uv run pytest packages/core/tests/test_risk_and_planning_returns_config.py::test_fixed_equity_premium_preset_requires_premium_field packages/core/tests/test_risk_and_planning_returns_config.py::test_custom_preset_requires_both_bases -q`

First run may be structural (`ImportError` for new `preset` field) — add minimal `PlanningReturnsConfig` scaffolding (`preset` field + stub validator) until pytest fails with `ValidationError` not raised (logical). Then implement the validator in Step 3.

- [ ] **Step 3: Implement the model**

In `packages/core/core/models.py`, replace the constants block near line 31-32 to add the default preset, and replace the `PlanningReturnsConfig` class (lines 74-76):

```python
DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS = Decimal("0.05")
DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS = Decimal("0.02")
DEFAULT_PLANNING_PRESET = "regression_prediction"

StockPresetBase = Literal[
    "regression_prediction", "conservative_estimate", "one_over_cape", "historical"
]
BondPresetBase = Literal["twenty_year_tips_yield", "historical"]
PlanningPreset = Literal[
    "regression_prediction",
    "conservative_estimate",
    "one_over_cape",
    "historical",
    "fixed_equity_premium",
    "custom",
    "fixed",
]
```

Then the class (place where the old `PlanningReturnsConfig` was):

```python
class PlanningReturnsConfig(BaseModel):
    preset: PlanningPreset = DEFAULT_PLANNING_PRESET

    fixed_equity_premium: Decimal | None = None
    custom_stocks_base: StockPresetBase | None = None
    custom_bonds_base: BondPresetBase | None = None
    custom_stocks_delta: Decimal = Decimal(0)
    custom_bonds_delta: Decimal = Decimal(0)

    expected_annual_return_stocks: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS
    expected_annual_return_bonds: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS

    stock_volatility_scale: Decimal = Field(default=Decimal(1), gt=0)

    @model_validator(mode="after")
    def _require_mode_fields(self) -> PlanningReturnsConfig:
        if self.preset == "fixed_equity_premium" and self.fixed_equity_premium is None:
            raise ValueError(
                "fixed_equity_premium is required when preset == 'fixed_equity_premium'"
            )
        if self.preset == "custom" and (
            self.custom_stocks_base is None or self.custom_bonds_base is None
        ):
            raise ValueError(
                "custom preset requires custom_stocks_base and custom_bonds_base"
            )
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_risk_and_planning_returns_config.py -q`
Expected: PASS (existing + new validator tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_risk_and_planning_returns_config.py
git commit -m "feat(core): full-parity PlanningReturnsConfig preset model"
```

---

## Task 4: Vendored-constant loaders (`presets_data.py`)

**Files:**
- Create: `packages/simulation/simulation/market_data/presets_data.py`
- No separate test file — loader smoke covered in Task 5 `test_presets.py`

- [ ] **Step 1: Implement the loaders** (no test-first; loaders are thin JSON/CSV readers verified indirectly by preset math tests in Task 5)

Create `packages/simulation/simulation/market_data/presets_data.py`:

```python
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"
_CAPE_REGRESSION_PATH = _DATA_DIR / "cape_regression_v7.json"
_VARIANCE_TABLE_PATH = _DATA_DIR / "stock_log_variance_by_block.csv"

# tpaw ordering: full then restricted, each [5, 10, 20, 30]-year.
REGRESSION_KEYS = (
    "full_5",
    "full_10",
    "full_20",
    "full_30",
    "restricted_5",
    "restricted_10",
    "restricted_20",
    "restricted_30",
)


@dataclass(frozen=True)
class CapeRegression:
    shiller_10yr_real_earnings: float
    pairs: dict[str, tuple[float, float]]  # key -> (slope, intercept)
    effective_date: str


@lru_cache(maxsize=1)
def load_cape_regression() -> CapeRegression:
    data = json.loads(_CAPE_REGRESSION_PATH.read_text(encoding="utf-8"))
    raw = data["regression_coeffs"]
    pairs = {key: (float(raw[key][0]), float(raw[key][1])) for key in REGRESSION_KEYS}
    return CapeRegression(
        shiller_10yr_real_earnings=float(data["shiller_10yr_real_earnings"]),
        pairs=pairs,
        effective_date=str(data["effective_date"]),
    )


@lru_cache(maxsize=1)
def load_stock_log_variance_by_block() -> dict[int, float]:
    table: dict[int, float] = {}
    with _VARIANCE_TABLE_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[int(row["block_size"])] = float(row["annual_log_returns_variance"])
    return table
```

- [ ] **Step 2: Commit**

```bash
git add packages/simulation/simulation/market_data/presets_data.py
git commit -m "feat(simulation): load vendored CAPE regression and variance table"
```

---

## Task 5: Pure preset math (`presets.py`)

**Files:**
- Create: `packages/simulation/simulation/presets.py`
- Create: `packages/simulation/tests/tpaw_preset_contract.py` — single pinned contract block
- Test: `packages/simulation/tests/test_presets.py`

- [ ] **Step 1: Add the contract fixture module**

Create `packages/simulation/tests/tpaw_preset_contract.py` — one place for pinned tpaw v7 inputs/outputs (comment every literal):

```python
# pinned: tpaw v7 preset outputs for sp500_close + Shiller earnings below (round_p(3) stocks;
# raw tips_20yr). See plan reference table.

SP500_CLOSE = 7517.09
TIPS_20YR = 0.026

EXPECTED_ONE_OVER_CAPE_ROUNDED = 0.023
EXPECTED_REGRESSION_PREDICTION = 0.05
EXPECTED_CONSERVATIVE_ESTIMATE = 0.035
EXPECTED_HISTORICAL_STOCKS = 0.087
EXPECTED_HISTORICAL_BONDS = 0.028
```

- [ ] **Step 2: Write the failing tests**

Create `packages/simulation/tests/test_presets.py`:

```python
import pytest

from simulation.market_data import load_historical_returns
from simulation.market_data.presets_data import (
    REGRESSION_KEYS,
    load_cape_regression,
    load_stock_log_variance_by_block,
)
from simulation.presets import (
    conservative_estimate,
    historical_annual_return,
    one_over_cape,
    regression_prediction,
    round3,
    stock_estimates,
    stock_log_variance,
)
from .tpaw_preset_contract import (
    EXPECTED_CONSERVATIVE_ESTIMATE,
    EXPECTED_HISTORICAL_BONDS,
    EXPECTED_HISTORICAL_STOCKS,
    EXPECTED_ONE_OVER_CAPE_ROUNDED,
    EXPECTED_REGRESSION_PREDICTION,
    SP500_CLOSE,
)

SHILLER = load_cape_regression().shiller_10yr_real_earnings


def test_loaders_feed_preset_math():
    coeffs = load_cape_regression()
    table = load_stock_log_variance_by_block()

    assert list(coeffs.pairs.keys()) == list(REGRESSION_KEYS)
    assert set(table.keys()) == set(range(1, 1441))


def test_one_over_cape_is_earnings_over_price():
    expected = SHILLER / SP500_CLOSE

    assert one_over_cape(sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER) == (
        expected
    )


def test_round3_matches_tpaw_round_p():
    # pinned: half-away-from-zero at 3 dp
    assert round3(0.0225) == EXPECTED_ONE_OVER_CAPE_ROUNDED


@pytest.mark.parametrize(
    ("fn", "expected"),
    [
        (regression_prediction, EXPECTED_REGRESSION_PREDICTION),
        (conservative_estimate, EXPECTED_CONSERVATIVE_ESTIMATE),
    ],
)
def test_stock_presets_match_tpaw_contract(fn, expected):
    ooc = one_over_cape(sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER)

    assert fn(ooc) == expected


def test_historical_returns_match_tpaw_contract():
    returns = load_historical_returns()

    assert historical_annual_return(returns.stocks_log) == EXPECTED_HISTORICAL_STOCKS
    assert historical_annual_return(returns.bonds_log) == EXPECTED_HISTORICAL_BONDS


def test_stock_estimates_bundle_derives_from_same_inputs():
    ooc = one_over_cape(sp500_close=SP500_CLOSE, shiller_10yr_real_earnings=SHILLER)
    estimates = stock_estimates(sp500_close=SP500_CLOSE)

    assert estimates.one_over_cape == round3(ooc)
    assert estimates.regression_prediction == regression_prediction(ooc)
    assert estimates.conservative_estimate == conservative_estimate(ooc)


def test_stock_log_variance_scales_table_entry():
    block_size = 60
    scale = 2.0
    table = load_stock_log_variance_by_block()

    assert stock_log_variance(block_size_months=block_size, volatility_scale=scale) == (
        table[block_size] * scale**2
    )


def test_stock_log_variance_rejects_unknown_block_size():
    with pytest.raises(ValueError, match="block size"):
        stock_log_variance(block_size_months=99999, volatility_scale=1.0)
```

- [ ] **Step 3: Run test — expect logical failure after scaffolding**

Run: `uv run pytest packages/simulation/tests/test_presets.py -q`

Add minimal `presets.py` stubs (`NotImplementedError` / wrong return) until failures are `AssertionError` on preset values, not import errors. Then implement full math in Step 4.

- [ ] **Step 4: Implement the pure math**

Create `packages/simulation/simulation/presets.py`:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache

import numpy as np

from simulation.market_data import load_historical_returns
from simulation.market_data.presets_data import (
    load_cape_regression,
    load_stock_log_variance_by_block,
)


def round3(value: float) -> float:
    # tpaw round_p(3): round half away from zero to 3 decimals.
    return float(Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def one_over_cape(*, sp500_close: float, shiller_10yr_real_earnings: float) -> float:
    return shiller_10yr_real_earnings / sp500_close


def _rolling_12_sum(log_returns: np.ndarray) -> np.ndarray:
    # tpaw periodize_log_returns: overlapping 12-month log-return sums.
    kernel = np.ones(12, dtype=np.float64)
    return np.convolve(log_returns, kernel, mode="valid")


def _annualized_non_log_mean(log_returns: np.ndarray) -> float:
    annualized_log = _rolling_12_sum(log_returns)
    return float(np.mean(np.expm1(annualized_log)))


def _shift_correction(log_returns: np.ndarray) -> float:
    # block_size=None, scale=1.0 (the preset-menu correction).
    monthly_log_mean = float(np.mean(log_returns))
    annualized_non_log = _annualized_non_log_mean(log_returns)
    return math.log1p(annualized_non_log) / 12.0 - monthly_log_mean


def _annual_non_log_from_annual_log(annual_log_mean: float, correction: float) -> float:
    return math.expm1((annual_log_mean / 12.0 + correction) * 12.0)


@lru_cache(maxsize=1)
def _stock_correction() -> float:
    return _shift_correction(load_historical_returns().stocks_log)


def _regression_predictions_raw(one_over_cape_value: float) -> list[float]:
    coeffs = load_cape_regression()
    correction = _stock_correction()
    x = math.log1p(one_over_cape_value)
    return [
        _annual_non_log_from_annual_log(slope * x + intercept, correction)
        for slope, intercept in coeffs.pairs.values()
    ]


def regression_prediction(one_over_cape_value: float) -> float:
    predictions = _regression_predictions_raw(one_over_cape_value)
    return round3(sum(predictions) / len(predictions))


def conservative_estimate(one_over_cape_value: float) -> float:
    pool = sorted([one_over_cape_value, *_regression_predictions_raw(one_over_cape_value)])
    lowest_four = pool[:4]
    return round3(sum(lowest_four) / len(lowest_four))


def historical_annual_return(log_returns: np.ndarray) -> float:
    return round3(_annualized_non_log_mean(log_returns))


@dataclass(frozen=True)
class StockEstimates:
    one_over_cape: float
    regression_prediction: float
    conservative_estimate: float
    historical: float


def stock_estimates(*, sp500_close: float) -> StockEstimates:
    coeffs = load_cape_regression()
    ooc = one_over_cape(
        sp500_close=sp500_close,
        shiller_10yr_real_earnings=coeffs.shiller_10yr_real_earnings,
    )
    return StockEstimates(
        one_over_cape=round3(ooc),
        regression_prediction=regression_prediction(ooc),
        conservative_estimate=conservative_estimate(ooc),
        historical=historical_annual_return(load_historical_returns().stocks_log),
    )


def historical_bond_return() -> float:
    return historical_annual_return(load_historical_returns().bonds_log)


def stock_log_variance(*, block_size_months: int, volatility_scale: float) -> float:
    table = load_stock_log_variance_by_block()
    if block_size_months not in table:
        raise ValueError(
            f"no vendored stock log variance for block size {block_size_months} "
            f"(table covers {min(table)}..{max(table)})"
        )
    return table[block_size_months] * volatility_scale**2
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/simulation/tests/test_presets.py -q`
Expected: PASS. If preset contract values fail, verify `_rolling_12_sum` uses `mode="valid"` and Shiller/coeffs come from the loader.

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/presets.py packages/simulation/tests/tpaw_preset_contract.py packages/simulation/tests/test_presets.py
git commit -m "feat(simulation): pure tpaw-parity preset math"
```

---

## Task 6: Preset dispatch in `resolve_planning_returns`

**Files:**
- Modify: `packages/simulation/simulation/planning_returns.py` (replace entirely)
- Test: `packages/simulation/tests/test_planning_returns.py` (replace)

- [ ] **Step 1: Write the failing tests**

Replace `packages/simulation/tests/test_planning_returns.py`. Tests cover **dispatch behavior** only — derive expected stocks/bonds from `presets` helpers and bind every shared literal once:

```python
from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.models import DEFAULT_BLOCK_SIZE_MONTHS
from simulation.market_data import load_historical_returns
from simulation.presets import (
    historical_annual_return,
    historical_bond_return,
    stock_estimates,
    stock_log_variance,
)
from simulation.planning_returns import resolve_planning_returns
from .tpaw_preset_contract import SP500_CLOSE, TIPS_20YR

TODAY = date(2026, 6, 1)


def _spy_resolver(value):
    calls = {"count": 0}

    def resolver(**kwargs):
        calls["count"] += 1
        return value

    return resolver, calls


class _SP500:
    def __init__(self, close):
        self.close = close


class _Treasury:
    def __init__(self, twenty):
        self.yields = {"20": twenty}


def test_fixed_preset_uses_literals_and_skips_resolvers():
    expected_stocks = 0.06
    expected_bonds = 0.025
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.expected_annual_return_stocks = Decimal(str(expected_stocks))
    plan.planning_returns.expected_annual_return_bonds = Decimal(str(expected_bonds))
    sp_resolver, sp_calls = _spy_resolver(_SP500(9999.0))
    tr_resolver, tr_calls = _spy_resolver(_Treasury(0.99))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks
    assert result.annual_bonds == expected_bonds
    assert result.annual_stock_log_variance == stock_log_variance(
        block_size_months=plan.sampling.block_size_months,
        volatility_scale=float(plan.planning_returns.stock_volatility_scale),
    )
    assert sp_calls["count"] == 0
    assert tr_calls["count"] == 0


def test_regression_preset_calls_resolvers_and_uses_preset_math():
    plan = default_plan()
    plan.planning_returns.preset = "regression_prediction"
    expected_stocks = stock_estimates(sp500_close=SP500_CLOSE).regression_prediction
    sp_resolver, sp_calls = _spy_resolver(_SP500(SP500_CLOSE))
    tr_resolver, tr_calls = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks
    assert result.annual_bonds == TIPS_20YR
    assert sp_calls["count"] == 1
    assert tr_calls["count"] == 1


def test_historical_preset_skips_resolvers():
    plan = default_plan()
    plan.planning_returns.preset = "historical"
    expected_stocks = historical_annual_return(load_historical_returns().stocks_log)
    expected_bonds = historical_bond_return()
    sp_resolver, sp_calls = _spy_resolver(_SP500(0.0))
    tr_resolver, tr_calls = _spy_resolver(_Treasury(0.0))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks
    assert result.annual_bonds == expected_bonds
    assert sp_calls["count"] == 0
    assert tr_calls["count"] == 0


def test_fixed_equity_premium_adds_configured_premium_to_tips():
    premium = Decimal("0.03")
    plan = default_plan()
    plan.planning_returns.preset = "fixed_equity_premium"
    plan.planning_returns.fixed_equity_premium = premium
    sp_resolver, sp_calls = _spy_resolver(_SP500(0.0))
    tr_resolver, _ = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_bonds == TIPS_20YR
    assert result.annual_stocks == TIPS_20YR + float(premium)
    assert sp_calls["count"] == 0


def test_custom_applies_bases_and_deltas():
    stocks_delta = Decimal("0.01")
    bonds_delta = Decimal("-0.002")
    plan = default_plan()
    plan.planning_returns.preset = "custom"
    plan.planning_returns.custom_stocks_base = "regression_prediction"
    plan.planning_returns.custom_bonds_base = "twenty_year_tips_yield"
    plan.planning_returns.custom_stocks_delta = stocks_delta
    plan.planning_returns.custom_bonds_delta = bonds_delta
    expected_stocks_base = stock_estimates(
        sp500_close=SP500_CLOSE
    ).regression_prediction
    sp_resolver, _ = _spy_resolver(_SP500(SP500_CLOSE))
    tr_resolver, _ = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks_base + float(stocks_delta)
    assert result.annual_bonds == TIPS_20YR + float(bonds_delta)


def test_variance_uses_block_size_table_and_scale():
    scale = Decimal("1.5")
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.stock_volatility_scale = scale
    expected_variance = stock_log_variance(
        block_size_months=DEFAULT_BLOCK_SIZE_MONTHS,
        volatility_scale=float(scale),
    )

    result = resolve_planning_returns(plan, today=TODAY)

    assert result.annual_stock_log_variance == expected_variance
```

- [ ] **Step 2: Run test — expect logical failure**

Run: `uv run pytest packages/simulation/tests/test_planning_returns.py -q`

Scaffold `resolve_planning_returns` signature/dispatch until failures are wrong return values or spy call counts, not import errors. Then implement Step 3.

- [ ] **Step 3: Rewrite `planning_returns.py`**

Replace `packages/simulation/simulation/planning_returns.py` entirely:

```python
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from core.models import Plan

from simulation.market_data import (
    SP500Resolved,
    TreasuryYieldsResolved,
    load_historical_returns,
    resolve_latest_sp500_close,
    resolve_treasury_real_yields,
)
from simulation.presets import (
    historical_annual_return,
    historical_bond_return,
    stock_estimates,
    stock_log_variance,
)

TWENTY_YEAR_TENOR = "20"

SP500Resolver = Callable[..., SP500Resolved]
TreasuryResolver = Callable[..., TreasuryYieldsResolved]


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float


def resolve_planning_returns(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    eod_api_key: str | None = None,
    sp500_resolver: SP500Resolver = resolve_latest_sp500_close,
    treasury_resolver: TreasuryResolver = resolve_treasury_real_yields,
) -> PlanningReturns:
    config = plan.planning_returns
    today = today or date.today()

    # Lazy resolvers: only hit the (cache/vendored) data for presets that need it.
    def sp500_close() -> float:
        return sp500_resolver(
            today=today, allow_refresh=allow_refresh, now=now, api_key=eod_api_key
        ).close

    def tips_20yr() -> float:
        return treasury_resolver(
            today=today, allow_refresh=allow_refresh, now=now
        ).yields[TWENTY_YEAR_TENOR]

    def stocks_from_base(base: str) -> float:
        if base == "historical":
            return historical_annual_return(load_historical_returns().stocks_log)
        estimates = stock_estimates(sp500_close=sp500_close())
        return {
            "regression_prediction": estimates.regression_prediction,
            "conservative_estimate": estimates.conservative_estimate,
            "one_over_cape": estimates.one_over_cape,
        }[base]

    def bonds_from_base(base: str) -> float:
        if base == "historical":
            return historical_bond_return()
        return tips_20yr()

    preset = config.preset
    if preset == "fixed":
        annual_stocks = float(config.expected_annual_return_stocks)
        annual_bonds = float(config.expected_annual_return_bonds)
    elif preset == "historical":
        annual_stocks = stocks_from_base("historical")
        annual_bonds = bonds_from_base("historical")
    elif preset == "fixed_equity_premium":
        if config.fixed_equity_premium is None:
            raise ValueError("fixed_equity_premium preset requires fixed_equity_premium")
        annual_bonds = tips_20yr()
        annual_stocks = annual_bonds + float(config.fixed_equity_premium)
    elif preset == "custom":
        if config.custom_stocks_base is None or config.custom_bonds_base is None:
            raise ValueError("custom preset requires both custom bases")
        annual_stocks = stocks_from_base(config.custom_stocks_base) + float(
            config.custom_stocks_delta
        )
        annual_bonds = bonds_from_base(config.custom_bonds_base) + float(
            config.custom_bonds_delta
        )
    else:
        # regression_prediction / conservative_estimate / one_over_cape -> stock base + 20yr TIPS
        annual_stocks = stocks_from_base(preset)
        annual_bonds = tips_20yr()

    variance = stock_log_variance(
        block_size_months=plan.sampling.block_size_months,
        volatility_scale=float(config.stock_volatility_scale),
    )
    return PlanningReturns(
        annual_stocks=annual_stocks,
        annual_bonds=annual_bonds,
        annual_stock_log_variance=variance,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/simulation/tests/test_planning_returns.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/planning_returns.py packages/simulation/tests/test_planning_returns.py
git commit -m "feat(simulation): resolve planning returns from presets"
```

---

## Task 7: Harden 3c-1 resolvers — vendored fallback on empty in-range read

The 3c-1 resolvers select the cache CSV whenever the file **exists**, then read the latest
row at/before `today`. A warm 30-day cache has no row for a backdated `today` (e.g. tests
using `2026-01-01`, or simulating a backdated plan), which raises instead of falling back
to the always-present vendored snapshot. Add that fallback so any `today` is robust
regardless of cache coverage. (CI has no cache dir, so this only bites locally today, but
it is a real correctness gap now that presets consume these resolvers.)

**Files:**
- Modify: `packages/simulation/simulation/market_data/sp500.py`
- Modify: `packages/simulation/simulation/market_data/treasury.py`
- Test: `packages/simulation/tests/market_data/test_sp500.py`, `.../test_treasury.py` (add cases)

- [ ] **Step 1: Write the failing tests**

Add to `packages/simulation/tests/market_data/test_sp500.py`:

```python
from datetime import date

from simulation.market_data.sp500 import resolve_latest_sp500_close


def test_falls_back_to_vendored_when_cache_lacks_in_range_row(tmp_path):
    today = date(2020, 6, 1)
    expected_close = 3200.0
    cache = tmp_path / "sp500_close.csv"
    cache.write_text("observation_date,close\n2026-06-10,7000.0\n", encoding="utf-8")
    vendored = tmp_path / "vendored.csv"
    vendored.write_text(
        f"observation_date,close\n2020-01-02,{expected_close}\n", encoding="utf-8"
    )

    result = resolve_latest_sp500_close(
        today=today,
        cache_path=cache,
        vendored_path=vendored,
    )

    assert result.close == expected_close
    assert result.source == "vendored"
```

Add the analogous case to `packages/simulation/tests/market_data/test_treasury.py`:

```python
from datetime import date

from simulation.market_data.treasury import resolve_treasury_real_yields


def test_falls_back_to_vendored_when_cache_lacks_in_range_row(tmp_path):
    today = date(2020, 6, 1)
    expected_yield_20 = 0.021
    header = "observation_date,5,7,10,20,30\n"
    cache = tmp_path / "treasury.csv"
    cache.write_text(header + "2026-06-10,0.01,0.01,0.01,0.01,0.01\n", encoding="utf-8")
    vendored = tmp_path / "vendored.csv"
    vendored.write_text(
        header + f"2020-01-02,0.02,0.02,0.02,{expected_yield_20},0.022\n",
        encoding="utf-8",
    )

    result = resolve_treasury_real_yields(
        today=today,
        cache_path=cache,
        vendored_path=vendored,
    )

    assert result.yields["20"] == expected_yield_20
    assert result.source == "vendored"
```

- [ ] **Step 2: Run test — expect logical failure**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py::test_falls_back_to_vendored_when_cache_lacks_in_range_row packages/simulation/tests/market_data/test_treasury.py::test_falls_back_to_vendored_when_cache_lacks_in_range_row -q`

Expected: `ValueError` (no in-range row on cache path) until Step 3 implements vendored fallback.

- [ ] **Step 3: Add the fallback in `sp500.py`**

In `resolve_latest_sp500_close`, replace the final read block (the `_latest_close(today, read_path)` call and `source` resolution) with:

```python
    try:
        observed, close = _latest_close(today, read_path)
    except ValueError:
        if read_path == vendored_path:
            raise
        read_path = vendored_path
        refreshed_live = False
        observed, close = _latest_close(today, read_path)
    source = _resolve_source(
        refreshed_live=refreshed_live,
        read_path=read_path,
        cache_path=cache_path,
    )
    return SP500Resolved(close=close, observation_date=observed, source=source)
```

- [ ] **Step 4: Add the fallback in `treasury.py`**

In `resolve_treasury_real_yields`, replace the final read block (`_latest_curve(today, read_path)` and `source`) with:

```python
    try:
        observed, yields = _latest_curve(today, read_path)
    except ValueError:
        if read_path == vendored_path:
            raise
        read_path = vendored_path
        refreshed_live = False
        observed, yields = _latest_curve(today, read_path)
    source = _resolve_source(
        refreshed_live=refreshed_live,
        read_path=read_path,
        cache_path=cache_path,
    )
    return TreasuryYieldsResolved(
        yields=yields, observation_date=observed, source=source
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest packages/simulation/tests/market_data/test_sp500.py packages/simulation/tests/market_data/test_treasury.py -q`
Expected: PASS (new fallback cases + all existing 3c-1 cases).

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/market_data/sp500.py packages/simulation/simulation/market_data/treasury.py packages/simulation/tests/market_data/test_sp500.py packages/simulation/tests/market_data/test_treasury.py
git commit -m "fix(simulation): fall back to vendored when cache lacks in-range row"
```

---

## Task 8: Wire `preprocess` + fix affected existing tests

`resolve_inflation` already exposes an `allow_refresh`/`api_key`/`fetcher` seam (Phase 3a+)
that `preprocess` never uses — it calls `resolve_inflation(plan, today=today)` with no
refresh gating. That gap is pre-existing tech debt, not an intentional design choice (the
3a+ design's own control-flow diagram shows the web/CLI boundary calling
`resolve_inflation(..., allow_refresh=True, api_key=...)`; that call was never wired up).
This task threads a single `allow_refresh` + key-bearing parameter through `preprocess` for
**both** resolvers so the gap doesn't get replicated for planning returns, and fixes it for
inflation too while we're in this function.

**Files:**
- Modify: `packages/simulation/simulation/preprocess.py:61-83`
- Modify: `packages/simulation/tests/test_preprocess.py:101-116`

**Testing policy (Tasks 8–9).** `preprocess`/`run_simulation` forwarding is pure
passthrough — no business logic. Per AGENTS.md, do **not** add spy/monkeypatch tests at
each layer that only assert kwargs were copied. Task 6 already covers resolver dispatch with
injected resolvers; market_data tests already cover `allow_refresh` gating on fetchers.
Task 9 includes **one** parametrized integration smoke test at the web boundary (the only
layer that loads `AppSettings`); that is the single allowed wiring test for this feature.

- [ ] **Step 1: Implement forwarding in `preprocess` (no new test here)**

In `packages/simulation/simulation/preprocess.py`, change the signature and the two
resolver calls:

```python
def preprocess(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> ProcessedPlan:
```

Add `from datetime import datetime` to the existing `from datetime import date` import line.
Replace the two resolver calls:

```python
    inflation = resolve_inflation(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        api_key=fred_api_key,
    )
    planning = resolve_planning_returns(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        eod_api_key=eod_api_key,
    )
```

This is the same fail-silent, offline-safe seam both resolvers already implement:
`allow_refresh=False` (the default, and the only value every existing test passes) means
neither resolver ever calls a fetcher.

- [ ] **Step 2: Fix the two negative-return guard tests**

The default preset no longer reads the literal `expected_annual_return_*` fields, so these
guards must select `preset="fixed"`. In `packages/simulation/tests/test_preprocess.py`,
update both tests. Bind the invalid rate once; inject `today`:

```python
def test_negative_planning_bond_return_raises_value_error():
    invalid_return = Decimal("-1.5")
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.expected_annual_return_bonds = invalid_return
    today = date(2026, 1, 1)

    with pytest.raises(ValueError, match="bond"):
        preprocess(plan, today=today)


def test_negative_planning_stock_return_raises_value_error():
    invalid_return = Decimal("-1.5")
    plan = default_plan()
    plan.planning_returns.preset = "fixed"
    plan.planning_returns.expected_annual_return_stocks = invalid_return
    today = date(2026, 1, 1)

    with pytest.raises(ValueError, match="stock"):
        preprocess(plan, today=today)
```

- [ ] **Step 3: Run the affected suites**

Run: `uv run pytest packages/simulation/tests/test_preprocess.py packages/simulation/tests/test_engine.py -q`
Expected: PASS. `test_preprocess_shapes_and_basic_invariants` uses `today=date(2026,1,1)`
with `allow_refresh` defaulting to `False`; the vendored S&P snapshot starts 2025-07-07 and
Treasury 2010, so the default `regression_prediction` preset resolves offline. Allocation
stays in `[0, 1]`.

- [ ] **Step 4: Commit**

```bash
git add packages/simulation/simulation/preprocess.py packages/simulation/tests/test_preprocess.py
git commit -m "feat(simulation): resolve planning-return presets in preprocess"
```

---

## Task 9: Wire live refresh through the web run path

Closes the gap identified in Task 8: `run_simulation` and the FastAPI routes never forward
`allow_refresh`/keys, so a user who enters an `EOD_API_KEY` (or `FRED_API_KEY`) in Settings
still gets vendored/cached data on every run until they manually run
`scripts/refresh_market_data.py`. This wires the settings-backed keys through
`run_simulation` → `preprocess`, matching the 3a+ design's original control-flow intent for
inflation and extending it to planning returns.

**Files:**
- Modify: `packages/simulation/simulation/stub.py`
- Modify: `packages/web/web/app.py:83-101,202-214`
- Test: `packages/web/tests/test_app.py` — one integration smoke test only (see Task 8 policy note)

- [ ] **Step 1: Thread the parameters through `run_simulation`**

In `packages/simulation/simulation/stub.py`, change the signature and the `preprocess` call:

```python
def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
    allow_refresh: bool = False,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> SimulationResult:
    _ = percentiles  # reserved for Phase 3d aggregation
    today = today or date.today()
    ran_at = ran_at or datetime.now()

    processed = preprocess(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        fred_api_key=fred_api_key,
        eod_api_key=eod_api_key,
    )
    paths = build_return_paths(plan, months_per_run=processed.months, today=today)
    return simulate_monthly(
        processed,
        stocks_return=paths.stocks_log_to_simple(),
        bonds_return=paths.bonds_log_to_simple(),
        ran_at=ran_at,
    )
```

No new test in `test_run_simulation.py` — passthrough only; covered by Step 2 smoke test.

- [ ] **Step 2: Write the failing integration smoke test**

Add to `packages/web/tests/test_app.py` (reuse existing `client`/`db_path` fixtures;
`AppSettings`, `HOME`, and `RESULTS` are already imported). This is the **single**
integration smoke test for the whole refresh-wiring feature — parametrized over both routes
that call `run_simulation`, with every shared literal bound once:

```python
@pytest.mark.parametrize("route", [HOME, RESULTS])
def test_real_run_passes_stored_keys_with_live_refresh_enabled(
    client: TestClient, db_path, monkeypatch, route: str
) -> None:
    import sys

    expected_fred_key = "fred-secret"
    expected_eod_key = "eod-secret"
    allow_live_refresh = True
    SettingsRepository(db_path=db_path).save(
        AppSettings(fred_api_key=expected_fred_key, eod_api_key=expected_eod_key)
    )

    app_module = sys.modules["web.app"]
    real_run_simulation = app_module.run_simulation
    captured: dict = {}

    def spy_run_simulation(plan, **kwargs):
        captured.update(kwargs)
        return real_run_simulation(plan, **kwargs)

    monkeypatch.setattr(app_module, "run_simulation", spy_run_simulation)

    client.get(route)

    assert captured.get("allow_refresh") is allow_live_refresh
    assert captured.get("fred_api_key") == expected_fred_key
    assert captured.get("eod_api_key") == expected_eod_key
```

- [ ] **Step 3: Run test — expect logical failure**

Run: `uv run pytest packages/web/tests/test_app.py::test_real_run_passes_stored_keys_with_live_refresh_enabled -q`

Expected: `KeyError`/`AssertionError` — `run_simulation` called without `allow_refresh`.
Implement Step 4.

- [ ] **Step 4: Forward settings keys from both routes**

In `packages/web/web/app.py`, update `home` (inside `_register_home_route`) and `results`
(inside `_register_results_route`) to forward settings-backed keys. `home` already loads
`settings` (for template display) — just reorder so it's available before the
`run_simulation` call and pass the keys through:

```python
def home(
    request: Request,
    repo: RepoDep,
) -> HTMLResponse:
    resolved_db_path = _resolve_db_path(request.app)
    if not resolved_db_path.exists():
        return templates.TemplateResponse(
            request,
            "error.html",
            {"message": _INIT_DB_MESSAGE},
        )

    _, plan = repo.get_or_create_default()
    settings = get_settings_repo(request).get()
    result = run_simulation(
        plan,
        allow_refresh=True,
        fred_api_key=settings.fred_api_key,
        eod_api_key=settings.eod_api_key,
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {"plan": plan, "result": result, "settings": settings},
    )
```

`results` had no prior settings lookup; add one:

```python
def results(
    request: Request,
    repo: RepoDep,
) -> HTMLResponse:
    _, plan = repo.get_or_create_default()
    settings = get_settings_repo(request).get()
    result = run_simulation(
        plan,
        allow_refresh=True,
        fred_api_key=settings.fred_api_key,
        eod_api_key=settings.eod_api_key,
    )
    return templates.TemplateResponse(
        request,
        "results_stub.html",
        {"result": result},
    )
```

Both routes already have `request` in scope, and `get_settings_repo` is a plain function
taking `request` (not a FastAPI-injected dependency) — no new dependency wiring is needed
to call it directly inside `results`.

- [ ] **Step 5: Run the web suite**

Run: `uv run pytest packages/web/tests/test_app.py -q`
Expected: PASS. Every other existing web test omits `allow_refresh` when calling through
HTTP (they don't call `run_simulation` directly), so this is additive: real runs now pass
`allow_refresh=True` with whatever keys are configured (possibly `None`), and both
resolvers stay fail-silent when a key is absent or a fetch fails — no behavior change for
users who haven't configured a key.

- [ ] **Step 6: Commit**

```bash
git add packages/simulation/simulation/stub.py packages/web/web/app.py packages/web/tests/test_app.py
git commit -m "feat(web): forward AppSettings keys as live-refresh on real simulation runs"
```

---

## Task 10: Docs, index correction, full verification

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md:311-319,433`
- Modify: `packages/simulation/OVERVIEW.md`

- [ ] **Step 1: Correct the rebuild index Phase 3c exit criteria**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, replace the Phase 3c exit-criteria block (lines ~311-319) with:

```markdown
**Exit criteria (delivered across 3c-1 feeds + 3c-2 presets):**

- [x] S&P (EOD `GSPC.INDX`) + Treasury 20-yr TIPS feeds with cache + vendored fallback (3c-1)
- [x] CAPE / stock expected-return presets (regression, conservative, 1/CAPE, historical,
      fixed-equity-premium, custom, fixed), replacing 3b's fixed/manual `PlanningReturnsConfig`
- [x] Empirical variance-by-block-size table replaces the full-sample `var×12`
- [x] Bonds via 20-yr TIPS yield (tpaw default); `VT.US`/`BND.US` dropped (never fed presets)
- [x] `EOD_API_KEY` stored in `AppSettings` (3a+ form); injected at the web/CLI boundary; no key path in CI
- [x] **Dropped:** "stock-allocation glide path from the live preset feed" — tpaw fixes
      expected returns at month 0; the RRA allocation glide already shipped in 3b

*(RRA-on-total-portfolio allocation and PV of future income were delivered in Phase 3b.)*
```

Also add to the Completed plans table (line ~433):

```markdown
| Phase 3c-1 | `2026-06-12-phase-3c-1-simulation-market-feeds.md` | complete |
| Phase 3c-2 | `2026-06-12-phase-3c-2-simulation-planning-returns-presets.md` | complete |
```

And update the **Active phase** table to point at Phase 3d.

- [ ] **Step 2: Record parity status in the simulation OVERVIEW**

Append a Phase 3c-2 entry to `packages/simulation/OVERVIEW.md` noting: preset menu at full tpaw parity; expected returns from vendored v7 CAPE regression + Shiller earnings + live/vendored S&P and 20-yr TIPS; variance from the vendored block-size table × `stock_volatility_scale²`; expected-return glide path intentionally absent (tpaw fixes returns at month 0).

- [ ] **Step 3: Run the full gate**

Run: `make`
Expected: ruff + pyright + pytest all pass.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md packages/simulation/OVERVIEW.md
git commit -m "docs(simulation): record Phase 3c-2 preset parity and correct index"
```

---

## Notes

- **Live refresh on real runs (Tasks 8–9).** The Phase 3a+ design's own control-flow diagram
  specified `resolve_inflation(..., allow_refresh=True, api_key=...)` at the web/CLI
  boundary, but that call was never wired past the settings form + CLI — `run_simulation`
  and the FastAPI routes never forwarded keys. Tasks 8–9 close that pre-existing gap for
  **both** resolvers (inflation and planning returns) rather than let 3c-2 replicate it for
  a second resolver. `simulation` still never reads the DB directly; keys are loaded by
  `web/app.py` from `SettingsRepository` and injected. Every unit test in `simulation` and
  `core` keeps `allow_refresh=False` (the default) and never passes it to a real fetcher —
  only the single parametrized integration smoke test in Task 9 exercises the web→settings→
  `run_simulation` call chain.
- **Variance is preset-independent.** Every preset (including `fixed`) uses the vendored block-size variance table; only expected returns vary by preset. This matches tpaw (`get_target_empirical_annual_log_variance` keyed by sampling block size).

---

## Self-review checklist (completed during authoring)

- **Spec coverage:** config model (Task 3), preset math (Task 5) + vendored constants (Tasks 1-2, 4), resolution dispatch (Task 6), resolver vendored-fallback hardening (Task 7), preprocess wiring (Task 8), live-refresh web wiring (Task 9), index correction (Task 10), variance table (Tasks 2, 5, 6). ✅
- **Testing policy:** no Pydantic-default/trivial tests; no per-layer kwargs-forwarding spy
  tests (Tasks 8–9 passthrough covered by one parametrized web integration smoke test);
  contract literals centralized in `tpaw_preset_contract.py`; arrange/assert literals bound;
  constants imported from `core.models` / `presets_data` / `presets`; TDD steps folded (no
  separate structural-failure checklist). ✅
- **Type consistency:** `stock_estimates(...)` → `StockEstimates`; `resolve_planning_returns` kwargs consistent across Tasks 5-9; `preprocess`/`run_simulation` new kwargs (`allow_refresh`, `now`, `fred_api_key`, `eod_api_key`) consistent between Task 8 and Task 9; `PlanningReturns` shape unchanged. ✅
- **No placeholders:** all constants, coefficients, golden values, and commands are concrete. ✅

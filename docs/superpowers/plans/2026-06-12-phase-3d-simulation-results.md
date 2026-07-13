# Phase 3d — Simulation Results Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `run_simulation` return a chart-ready public `SimulationResult` (percentile-reduced series + tax-prorated wealth composition by income source), with percentiles configured via `plan.advanced.percentiles`.

**Architecture:** Engine keeps emitting private `RawSimulationResult` (`num_runs × months`). New `aggregate.py` reduces along the run axis with `numpy.percentile`. New `composition.py` builds deterministic remaining-income NPV bands (job / SS / pension / manual) after tax proration. `run_simulation` resolves percentiles (kwarg → plan), aggregates, attaches composition + `start_month`, and returns the public result. No web chart work.

**Tech Stack:** Python 3.14+, uv workspace, NumPy, Pydantic v2, pytest. Package boundary: `simulation → domain, core`.

**Design spec:** `docs/superpowers/specs/2026-07-10-phase-3d-simulation-results-design.md`

**Note:** Spec was approved uncommitted; include it in the first implementation commit (or the PR that lands 3d).

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| Create: `packages/simulation/simulation/aggregate.py` | `aggregate_percentiles` + `build_public_result` |
| Create: `packages/simulation/simulation/composition.py` | Tax proration + per-source bond NPV wealth bands |
| Modify: `packages/simulation/simulation/result.py` | `RawSimulationResult` + public `SimulationResult`; bump `ENGINE_VERSION` |
| Modify: `packages/simulation/simulation/engine.py` | Return `RawSimulationResult` |
| Modify: `packages/simulation/simulation/stub.py` | Wire aggregate + composition; resolve percentiles |
| Modify: `packages/simulation/simulation/npv.py` | Add shared `backward_npv_including_current` |
| Modify: `packages/simulation/simulation/preprocess.py` | Use shared NPV helper for income (and essential) bond pass |
| Modify: `packages/core/core/models.py` | `DEFAULT_PERCENTILES`, `normalize_percentiles`, `AdvancedConfig`, `Plan.advanced` |
| Modify: `packages/simulation/simulation/__init__.py` | Export public `SimulationResult` only (not `RawSimulationResult`) |
| Create: `packages/simulation/tests/test_aggregate.py` | Aggregation wiring |
| Create: `packages/simulation/tests/test_composition.py` | Proration + NPV reconciliation |
| Create: `packages/core/tests/test_advanced_config.py` | `normalize_percentiles` behavior only |
| Modify: `packages/simulation/tests/test_result.py` | Public result shape / equality |
| Modify: `packages/simulation/tests/test_run_simulation.py` | Public contract + override + horizon |
| Modify: `packages/simulation/tests/test_engine.py` | Import/assert `RawSimulationResult` if needed |
| Modify: `packages/simulation/OVERVIEW.md`, `README.md` | Parity + public vs raw |
| Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` | Phase 3d exit criteria + active plan |

**No DB migration:** missing `advanced` on stored plan JSON fills via Pydantic default.

**Web stub:** `results_stub.html` uses `result.balance_start[0][0]` — still valid as first percentile × first month. No web code changes required.

---

## Testing policy (AGENTS.md §108–132)

Apply on every task that adds or changes tests:

1. **Our logic only** — do **not** add tests that only exercise Pydantic field defaults, trivial getters, or “`np.percentile` returns what `np.percentile` returns.” In scope: `normalize_percentiles`, field-mapping in `aggregate_percentiles`, tax proration invariants, composition↔preprocess NPV reconciliation, `run_simulation` shape/override/`start_month` contracts.
2. **Avoid fragile values** — bind any literal used in both arrange and assert to one variable.
3. **Pull constants from source** — import `DEFAULT_PERCENTILES`, `ENGINE_VERSION`, etc. from production code. Inline literals only when intentionally pinning a contract; comment why.
4. **TDD flow** — failing test → minimal scaffolding until failure is **logical** (`AssertionError`, `NotImplementedError`, `ValidationError`) → implement → green. Do not checklist a separate “structural failure” pytest run as its own step.

**Spec §9 item 6 (Plan validation):** covered by testing `normalize_percentiles` (shared by the Pydantic validator and the kwarg path) — not by a “default AdvancedConfig equals …” smoke test.

---

### Task 1: `normalize_percentiles` + `AdvancedConfig`

**Files:**
- Modify: `packages/core/core/models.py`
- Create: `packages/core/tests/test_advanced_config.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_advanced_config.py`:

```python
import pytest
from core.models import DEFAULT_PERCENTILES, normalize_percentiles
from pydantic import ValidationError
from core.models import AdvancedConfig


def test_normalize_percentiles_sorts_ascending():
    unsorted = [90, 5, 50]
    expected = sorted(unsorted)

    assert normalize_percentiles(unsorted) == expected


def test_normalize_percentiles_rejects_empty():
    with pytest.raises(ValueError, match="non-empty"):
        normalize_percentiles([])


def test_normalize_percentiles_rejects_out_of_range():
    with pytest.raises(ValueError, match="0..100"):
        normalize_percentiles([50, 101])


def test_advanced_config_uses_normalize_percentiles():
    # Our validator must apply the same normalization (sort), not leave input order.
    unsorted = [95, 5, 50]
    config = AdvancedConfig(percentiles=unsorted)

    assert config.percentiles == normalize_percentiles(unsorted)
    assert DEFAULT_PERCENTILES == [5, 50, 95]  # pinned: tpaw UI low/mid/high
```

- [ ] **Step 2: Run tests to verify logical failure**

Run: `uv run pytest packages/core/tests/test_advanced_config.py -v`

Expected: FAIL with `ImportError` / `AttributeError` until scaffolding, then `NotImplementedError` or `ValidationError` / assert failure — not a silent pass. Add empty stubs first if imports fail structurally:

```python
# scaffolding in models.py until Step 3
DEFAULT_PERCENTILES = [5, 50, 95]

def normalize_percentiles(value: list[int]) -> list[int]:
    raise NotImplementedError

class AdvancedConfig(BaseModel):
    percentiles: list[int] = Field(default_factory=lambda: list(DEFAULT_PERCENTILES))
```

Re-run until failure is logical (`NotImplementedError` or assertion).

- [ ] **Step 3: Implement**

In `packages/core/core/models.py` (near other config defaults):

```python
DEFAULT_PERCENTILES = [5, 50, 95]


def normalize_percentiles(value: list[int]) -> list[int]:
    if not value:
        raise ValueError("percentiles must be non-empty")
    if any(p < 0 or p > 100 for p in value):
        raise ValueError("each percentile must be in 0..100")
    return sorted(value)


class AdvancedConfig(BaseModel):
    percentiles: list[int] = Field(default_factory=lambda: list(DEFAULT_PERCENTILES))

    @field_validator("percentiles")
    @classmethod
    def _normalize_percentiles(cls, value: list[int]) -> list[int]:
        return normalize_percentiles(value)
```

Add to `Plan`:

```python
advanced: AdvancedConfig = Field(default_factory=AdvancedConfig)
```

Ensure `field_validator` is imported from pydantic if not already.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_advanced_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_advanced_config.py \
  docs/superpowers/specs/2026-07-10-phase-3d-simulation-results-design.md
git commit -m "$(cat <<'EOF'
feat(core): add plan.advanced.percentiles for simulation results

EOF
)"
```

---

### Task 2: Shared `backward_npv_including_current`

**Files:**
- Modify: `packages/simulation/simulation/npv.py`
- Modify: `packages/simulation/simulation/preprocess.py`
- Create: `packages/simulation/tests/test_backward_npv.py`

- [ ] **Step 1: Write the failing test**

Create `packages/simulation/tests/test_backward_npv.py`:

```python
import numpy as np
from simulation.npv import backward_npv_including_current


def test_backward_npv_including_current_matches_hand_recurrence():
    real_series = np.array([10.0, 20.0, 30.0], dtype=np.float64)
    one_over_1_plus_r = 0.5  # extreme rate so arithmetic is obvious

    # Hand recurrence (last month → first), same as preprocess income pass:
    # m2: 0 * 0.5 + 30 = 30
    # m1: 30 * 0.5 + 20 = 35
    # m0: 35 * 0.5 + 10 = 27.5
    expected = np.array([27.5, 35.0, 30.0], dtype=np.float64)

    result = backward_npv_including_current(
        real_series, one_over_1_plus_r=one_over_1_plus_r
    )

    np.testing.assert_allclose(result, expected)
```

- [ ] **Step 2: Run test to verify logical failure**

Run: `uv run pytest packages/simulation/tests/test_backward_npv.py -v`

Expected: logical failure (`ImportError` → stub `NotImplementedError`, or `AssertionError`).

Scaffold:

```python
def backward_npv_including_current(
    real_series: np.ndarray, *, one_over_1_plus_r: float
) -> np.ndarray:
    raise NotImplementedError
```

- [ ] **Step 3: Implement helper and switch preprocess income/essential**

In `npv.py`:

```python
def backward_npv_including_current(
    real_series: np.ndarray, *, one_over_1_plus_r: float
) -> np.ndarray:
    """NPV of `real_series[m:]` including month `m`, discounting at a constant rate."""
    months = real_series.shape[0]
    out = np.empty(months, dtype=np.float64)
    running = 0.0
    for month in range(months - 1, -1, -1):
        running = running * one_over_1_plus_r + float(real_series[month])
        out[month] = running
    return out
```

In `preprocess.py`, replace the income/essential running accumulators with:

```python
income_including = backward_npv_including_current(
    income_real, one_over_1_plus_r=one_over_1p_bonds
)
essential_including = backward_npv_including_current(
    essential_real, one_over_1_plus_r=one_over_1p_bonds
)
npv_income = income_including - income_real
npv_essential = essential_including - essential_real
```

Keep the discretionary / cumulative loop as-is (portfolio rate varies by month). Import `backward_npv_including_current` from `simulation.npv`.

- [ ] **Step 4: Run focused tests**

Run:

```bash
uv run pytest packages/simulation/tests/test_backward_npv.py \
  packages/simulation/tests/test_preprocess.py \
  packages/simulation/tests/test_engine.py -v
```

Expected: PASS (preprocess/engine behavior unchanged).

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/npv.py \
  packages/simulation/simulation/preprocess.py \
  packages/simulation/tests/test_backward_npv.py
git commit -m "$(cat <<'EOF'
refactor(simulation): extract shared bond NPV including current month

EOF
)"
```

---

### Task 3: Tax proration

**Files:**
- Create: `packages/simulation/simulation/composition.py`
- Create: `packages/simulation/tests/test_composition.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/simulation/tests/test_composition.py`:

```python
import numpy as np
from simulation.composition import prorate_net_income_by_source


def test_prorated_nets_sum_to_net_cashflow_when_gross_positive():
    gross_job = np.array([80.0], dtype=np.float64)
    gross_ss = np.array([20.0], dtype=np.float64)
    gross_pension = np.array([0.0], dtype=np.float64)
    gross_manual = np.array([0.0], dtype=np.float64)
    # Domain stores taxes as non-positive.
    taxes = np.array([-10.0], dtype=np.float64)
    total_gross = gross_job + gross_ss + gross_pension + gross_manual
    net_cashflow = total_gross + taxes

    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )

    summed = (
        nets["job"]
        + nets["social_security"]
        + nets["pension"]
        + nets["manual"]
    )
    np.testing.assert_allclose(summed, net_cashflow)


def test_proration_zero_gross_month_yields_zero_nets():
    zeros = np.array([0.0], dtype=np.float64)
    taxes = np.array([-5.0], dtype=np.float64)  # residual tax ignored for composition

    nets = prorate_net_income_by_source(
        gross_job=zeros,
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        taxes=taxes,
    )

    for series in nets.values():
        np.testing.assert_allclose(series, zeros)
```

- [ ] **Step 2: Run tests to verify logical failure**

Run: `uv run pytest packages/simulation/tests/test_composition.py -v`

Scaffold `prorate_net_income_by_source` raising `NotImplementedError`.

- [ ] **Step 3: Implement proration**

In `composition.py`:

```python
from __future__ import annotations

import numpy as np

_SOURCE_KEYS = ("job", "social_security", "pension", "manual")


def prorate_net_income_by_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
) -> dict[str, np.ndarray]:
    """Split net income by source. `taxes` are domain-signed (non-positive)."""
    gross = {
        "job": gross_job,
        "social_security": gross_social_security,
        "pension": gross_pension,
        "manual": gross_manual,
    }
    total_gross = (
        gross_job + gross_social_security + gross_pension + gross_manual
    )
    nets: dict[str, np.ndarray] = {}
    for key in _SOURCE_KEYS:
        net = np.zeros_like(total_gross, dtype=np.float64)
        positive = total_gross > 0.0
        share = np.zeros_like(total_gross, dtype=np.float64)
        share[positive] = gross[key][positive] / total_gross[positive]
        net[positive] = gross[key][positive] + taxes[positive] * share[positive]
        nets[key] = net
    return nets
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/simulation/tests/test_composition.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/composition.py \
  packages/simulation/tests/test_composition.py
git commit -m "$(cat <<'EOF'
feat(simulation): prorate net income by source for wealth composition

EOF
)"
```

---

### Task 4: Wealth composition NPV by source

**Files:**
- Modify: `packages/simulation/simulation/composition.py`
- Modify: `packages/simulation/tests/test_composition.py`

- [ ] **Step 1: Write the failing reconciliation test**

Append to `test_composition.py`:

```python
from simulation.composition import wealth_by_income_source
from simulation.npv import backward_npv_including_current


def test_wealth_by_source_sums_to_combined_income_wealth():
    months = 4
    gross_job = np.array([100.0, 100.0, 0.0, 0.0], dtype=np.float64)
    gross_ss = np.array([0.0, 0.0, 50.0, 50.0], dtype=np.float64)
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-20.0, -20.0, -5.0, -5.0], dtype=np.float64)
    monthly_inflation = 0.0
    monthly_bond = 0.01
    one_over = 1.0 / (1.0 + monthly_bond)

    wealth = wealth_by_income_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=zeros,
        gross_manual=zeros,
        taxes=taxes,
        monthly_inflation=monthly_inflation,
        monthly_bond_rate=monthly_bond,
    )

    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=zeros,
        gross_manual=zeros,
        taxes=taxes,
    )
    combined_nominal = sum(nets[k] for k in nets)
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    combined_real = combined_nominal / deflator
    expected_total = backward_npv_including_current(
        combined_real, one_over_1_plus_r=one_over
    )

    actual_total = (
        wealth.job
        + wealth.social_security
        + wealth.pension
        + wealth.manual
    )
    np.testing.assert_allclose(actual_total, expected_total)
```

- [ ] **Step 2: Run test to verify logical failure**

Run: `uv run pytest packages/simulation/tests/test_composition.py::test_wealth_by_source_sums_to_combined_income_wealth -v`

Scaffold:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class WealthBySource:
    job: np.ndarray
    social_security: np.ndarray
    pension: np.ndarray
    manual: np.ndarray


def wealth_by_income_source(...) -> WealthBySource:
    raise NotImplementedError
```

- [ ] **Step 3: Implement**

```python
from simulation.npv import backward_npv_including_current


def wealth_by_income_source(
    *,
    gross_job: np.ndarray,
    gross_social_security: np.ndarray,
    gross_pension: np.ndarray,
    gross_manual: np.ndarray,
    taxes: np.ndarray,
    monthly_inflation: float,
    monthly_bond_rate: float,
) -> WealthBySource:
    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )
    months = gross_job.shape[0]
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    one_over = 1.0 / (1.0 + monthly_bond_rate)
    bands = {
        key: backward_npv_including_current(
            nets[key] / deflator, one_over_1_plus_r=one_over
        )
        for key in _SOURCE_KEYS
    }
    return WealthBySource(
        job=bands["job"],
        social_security=bands["social_security"],
        pension=bands["pension"],
        manual=bands["manual"],
    )
```

- [ ] **Step 4: Run composition tests**

Run: `uv run pytest packages/simulation/tests/test_composition.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/composition.py \
  packages/simulation/tests/test_composition.py
git commit -m "$(cat <<'EOF'
feat(simulation): build tax-prorated wealth composition NPV by source

EOF
)"
```

---

### Task 5: Split result types + percentile aggregation

**Files:**
- Modify: `packages/simulation/simulation/result.py`
- Create: `packages/simulation/simulation/aggregate.py`
- Create: `packages/simulation/tests/test_aggregate.py`
- Modify: `packages/simulation/tests/test_result.py`
- Modify: `packages/simulation/simulation/engine.py` (return type name only)

- [ ] **Step 1: Write failing aggregation test**

Create `packages/simulation/tests/test_aggregate.py`:

```python
from datetime import datetime

import numpy as np
from simulation.aggregate import aggregate_percentiles
from simulation.result import RawSimulationResult


def _raw(*, balance_start: np.ndarray) -> RawSimulationResult:
    num_runs, months = balance_start.shape
    zeros = np.zeros((num_runs, months), dtype=np.float64)
    return RawSimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=balance_start,
        withdrawals_essential=zeros,
        withdrawals_discretionary=zeros,
        withdrawals_general=zeros,
        withdrawals_total=balance_start * 0.1,  # distinct from balance for mapping check
        savings_stock_allocation=zeros,
        num_runs_insufficient=0,
    )


def test_aggregate_percentiles_reduces_each_array_field_along_runs():
    # Column 0 values [1, 2, 3]; column 1 [10, 20, 30]
    balance_start = np.array(
        [[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float64
    )
    percentiles = [0, 50, 100]
    raw = _raw(balance_start=balance_start)

    reduced = aggregate_percentiles(raw, percentiles=percentiles)

    assert reduced.balance_start.shape == (len(percentiles), raw.horizon_months)
    np.testing.assert_allclose(
        reduced.balance_start,
        np.percentile(raw.balance_start, percentiles, axis=0),
    )
    np.testing.assert_allclose(
        reduced.withdrawals_total,
        np.percentile(raw.withdrawals_total, percentiles, axis=0),
    )
    assert reduced.percentiles == percentiles
    assert reduced.num_runs == raw.num_runs
```

This asserts **our field mapping** (each series reduced the same way), not NumPy in isolation.

- [ ] **Step 2: Run test to verify logical failure**

Run: `uv run pytest packages/simulation/tests/test_aggregate.py -v`

- [ ] **Step 3: Implement result split + aggregate**

In `result.py`:

1. Rename current class to `RawSimulationResult` (same fields; keep `_ARRAY_FIELDS` + `__eq__`).
2. Add public `SimulationResult` with:
   - same metadata as raw, plus `percentiles: list[int]`, `start_month: tuple[int, int]`
   - percentile arrays: `balance_start`, withdrawals_*, `savings_stock_allocation`
   - composition: `wealth_job`, `wealth_social_security`, `wealth_pension`, `wealth_manual` (1-D)
   - `_ARRAY_FIELDS` for equality covering all ndarray fields
3. Set `ENGINE_VERSION = "phase3d"`

In `aggregate.py`:

```python
from __future__ import annotations

import numpy as np
from simulation.composition import WealthBySource
from simulation.result import RawSimulationResult, SimulationResult

_RAW_SERIES = (
    "balance_start",
    "withdrawals_essential",
    "withdrawals_discretionary",
    "withdrawals_general",
    "withdrawals_total",
    "savings_stock_allocation",
)


def aggregate_percentiles(
    raw: RawSimulationResult, *, percentiles: list[int]
) -> SimulationResult:
    """Reduce raw run-major arrays to percentile-major; composition filled later."""
    reduced = {
        name: np.percentile(getattr(raw, name), percentiles, axis=0)
        for name in _RAW_SERIES
    }
    months = raw.horizon_months
    zeros = np.zeros(months, dtype=np.float64)
    return SimulationResult(
        ran_at=raw.ran_at,
        horizon_months=months,
        num_runs=raw.num_runs,
        percentiles=list(percentiles),
        start_month=(0, 0),  # placeholder; build_public_result sets real value
        balance_start=reduced["balance_start"],
        withdrawals_essential=reduced["withdrawals_essential"],
        withdrawals_discretionary=reduced["withdrawals_discretionary"],
        withdrawals_general=reduced["withdrawals_general"],
        withdrawals_total=reduced["withdrawals_total"],
        savings_stock_allocation=reduced["savings_stock_allocation"],
        wealth_job=zeros,
        wealth_social_security=zeros.copy(),
        wealth_pension=zeros.copy(),
        wealth_manual=zeros.copy(),
        num_runs_insufficient=raw.num_runs_insufficient,
    )


def build_public_result(
    raw: RawSimulationResult,
    *,
    percentiles: list[int],
    composition: WealthBySource,
    start_month: tuple[int, int],
) -> SimulationResult:
    result = aggregate_percentiles(raw, percentiles=percentiles)
    return result.model_copy(
        update={
            "start_month": start_month,
            "wealth_job": composition.job,
            "wealth_social_security": composition.social_security,
            "wealth_pension": composition.pension,
            "wealth_manual": composition.manual,
        }
    )
```

Prefer constructing `SimulationResult` once in `build_public_result` (no placeholder `start_month`) if that keeps types cleaner — either way is fine as long as tests pass.

Update `engine.py` to return `RawSimulationResult`.

Update `test_result.py` to construct public `SimulationResult` with percentile shapes + composition zeros + `percentiles` / `start_month`, **or** move array-equality tests to `RawSimulationResult` and add one public-shape smoke via aggregate tests. Prefer: keep equality tests on `RawSimulationResult`; delete obsolete public-as-raw tests.

- [ ] **Step 4: Fix engine tests + run**

`test_engine.py` indexes `result.withdrawals_general[0, 0]` — still valid on raw. Only change imports if they reference `SimulationResult`.

Run:

```bash
uv run pytest packages/simulation/tests/test_aggregate.py \
  packages/simulation/tests/test_result.py \
  packages/simulation/tests/test_engine.py -v
```

Expected: PASS for those. `test_run_simulation.py` may still fail until Task 6 — that is OK if you do not run it yet. Prefer running only the listed files.

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/result.py \
  packages/simulation/simulation/aggregate.py \
  packages/simulation/simulation/engine.py \
  packages/simulation/tests/test_aggregate.py \
  packages/simulation/tests/test_result.py
git commit -m "$(cat <<'EOF'
feat(simulation): add percentile aggregation and split raw/public results

EOF
)"
```

---

### Task 6: Wire `run_simulation`

**Files:**
- Modify: `packages/simulation/simulation/stub.py`
- Modify: `packages/simulation/simulation/__init__.py`
- Modify: `packages/simulation/tests/test_run_simulation.py`

- [ ] **Step 1: Rewrite failing public-contract tests**

Replace `packages/simulation/tests/test_run_simulation.py` with:

```python
from datetime import date, datetime

from core.defaults import default_plan
from core.models import DEFAULT_PERCENTILES, AdvancedConfig
from core.timeline import Timeline
from simulation.result import ENGINE_VERSION
from simulation import run_simulation


def test_run_simulation_returns_percentile_major_series():
    plan = default_plan()
    percentiles = [10, 50, 90]

    result = run_simulation(
        plan,
        percentiles=percentiles,
        today=date(2026, 1, 1),
        ran_at=datetime(2026, 1, 1),
    )

    assert result.engine_version == ENGINE_VERSION
    assert result.percentiles == percentiles
    assert result.num_runs == plan.sampling.num_runs
    assert result.balance_start.shape == (len(percentiles), result.horizon_months)
    assert result.withdrawals_total.shape == result.balance_start.shape
    assert result.wealth_job.shape == (result.horizon_months,)


def test_run_simulation_uses_plan_advanced_percentiles_when_kwarg_omitted():
    plan_percentiles = [5, 25, 75, 95]
    plan = default_plan().model_copy(
        update={"advanced": AdvancedConfig(percentiles=plan_percentiles)}
    )

    result = run_simulation(
        plan,
        today=date(2026, 1, 1),
        ran_at=datetime(2026, 1, 1),
    )

    assert result.percentiles == plan_percentiles


def test_run_simulation_kwarg_overrides_plan_percentiles():
    plan = default_plan()  # defaults to DEFAULT_PERCENTILES
    override = [1, 99]
    assert plan.advanced.percentiles == DEFAULT_PERCENTILES

    result = run_simulation(
        plan,
        percentiles=override,
        today=date(2026, 1, 1),
        ran_at=datetime(2026, 1, 1),
    )

    assert result.percentiles == sorted(override)


def test_run_simulation_start_month_and_horizon_match_timeline():
    today = date(2026, 6, 15)
    plan = default_plan()
    timeline = Timeline(plan, today=today)

    result = run_simulation(
        plan,
        today=today,
        ran_at=datetime(2026, 6, 15),
    )

    assert result.start_month == (today.year, today.month)
    assert result.horizon_months == timeline.horizon_months
```

- [ ] **Step 2: Run tests to verify logical failure**

Run: `uv run pytest packages/simulation/tests/test_run_simulation.py -v`

Expected: shape / attribute failures (still returning raw).

- [ ] **Step 3: Implement wiring**

In `stub.py`:

```python
from core.models import normalize_percentiles
from domain import build_monthly_cashflows
from simulation.aggregate import build_public_result
from simulation.composition import wealth_by_income_source
from simulation.engine import simulate_monthly
from simulation.market_data import build_return_paths, resolve_inflation
from simulation.preprocess import preprocess
from simulation.result import SimulationResult
import numpy as np


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> SimulationResult:
    today = today or date.today()
    ran_at = ran_at or datetime.now()
    resolved = normalize_percentiles(
        percentiles if percentiles is not None else plan.advanced.percentiles
    )

    processed = preprocess(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        fred_api_key=fred_api_key,
        eod_api_key=eod_api_key,
    )
    paths = build_return_paths(plan, months_per_run=processed.months, today=today)
    raw = simulate_monthly(
        processed,
        stocks_return=paths.stocks_log_to_simple(),
        bonds_return=paths.bonds_log_to_simple(),
        ran_at=ran_at,
    )

    cashflows = build_monthly_cashflows(plan, today=today)
    inflation = resolve_inflation(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        api_key=fred_api_key,
    )
    composition = wealth_by_income_source(
        gross_job=np.array([float(v) for v in cashflows.gross_job], dtype=np.float64),
        gross_social_security=np.array(
            [float(v) for v in cashflows.gross_social_security], dtype=np.float64
        ),
        gross_pension=np.array(
            [float(v) for v in cashflows.gross_pension], dtype=np.float64
        ),
        gross_manual=np.array(
            [float(v) for v in cashflows.gross_manual], dtype=np.float64
        ),
        taxes=np.array(
            [float(v) for v in cashflows.taxes.stored_total], dtype=np.float64
        ),
        monthly_inflation=inflation.monthly,
        monthly_bond_rate=processed.monthly_planning_bonds,
    )

    return build_public_result(
        raw,
        percentiles=resolved,
        composition=composition,
        start_month=(today.year, today.month),
    )
```

**Avoid double work if easy:** `preprocess` already builds cashflows and inflation.
Prefer threading composition inputs out of `preprocess` / `ProcessedPlan` when it is a
small additive change (e.g. stash `monthly_inflation` on `ProcessedPlan` and pass
gross/tax arrays already computed). Otherwise the double `build_monthly_cashflows` /
`resolve_inflation` call above is acceptable for 3d — same deterministic inputs; cost is
dwarfed by Monte Carlo. Do **not** invent a large refactor mid-task.

Ensure `__init__.py` still exports `SimulationResult` (public) and does **not** export `RawSimulationResult`.

- [ ] **Step 4: Run simulation + web smoke**

Run:

```bash
uv run pytest packages/simulation/tests/test_run_simulation.py \
  packages/web/tests/test_app.py -v
```

Expected: PASS (`balance_start[0][0]` stub still works).

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/stub.py \
  packages/simulation/simulation/__init__.py \
  packages/simulation/simulation/preprocess.py \
  packages/simulation/tests/test_run_simulation.py
git commit -m "$(cat <<'EOF'
feat(simulation): return percentile results and wealth composition from run_simulation

EOF
)"
```

---

### Task 7: Docs + rebuild index

**Files:**
- Modify: `packages/simulation/OVERVIEW.md`
- Modify: `packages/simulation/README.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Update OVERVIEW.md**

In the feature parity table:

- Set “Percentile aggregation …” to **Ported (Phase 3d)** → `simulation/aggregate.py`
- Add row: wealth composition (tax-prorated NPV by source) → **Ported (Phase 3d)** → `simulation/composition.py`
- List deferred series explicitly (withdrawal rate, total-portfolio stock allocation, spending-tilt series, ending-balance scalars)
- Remove the “percentiles accepted but unused” paragraph; note public result is percentile-reduced and raw is internal

- [ ] **Step 2: Update README.md**

Replace “raw results / Phase 3d” wording with: public `SimulationResult` is percentile-major; `RawSimulationResult` is engine-internal; composition bands support stacked total-portfolio charts in Phase 4.

- [ ] **Step 3: Update rebuild index**

- Active phase → Phase 4 (or keep 3d complete and set next action to write Phase 4 plan — match prior phase-completion pattern)
- Phase 3d exit criteria checkboxes aligned to spec §13 (all checked when done)
- Completed plans table: add Phase 3d plan file
- Active plan: Phase 4 plan *(to write)*

Phase 3d exit criteria text:

```markdown
- [x] Public `SimulationResult` is percentile-major (balance, withdrawals, savings allocation)
- [x] Aggregation via `numpy.percentile` along runs
- [x] `plan.advanced.percentiles` default `[5, 50, 95]`; kwarg overrides
- [x] Wealth composition (job/SS/pension/manual) tax-prorated NPV bands
- [x] `start_month` + horizon match `Timeline` (items 30–31)
```

- [ ] **Step 4: Commit**

```bash
git add packages/simulation/OVERVIEW.md packages/simulation/README.md \
  docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "$(cat <<'EOF'
docs(simulation): record Phase 3d results data layer parity

EOF
)"
```

---

### Task 8: Full verification

- [ ] **Step 1: Run `make`**

Run from repo root: `make`

Expected: lint + tests pass.

- [ ] **Step 2: Fix any failures**

If web or core tests fail on `Plan` construction missing `advanced`, they should not — `default_factory` applies. Fix real breakages only.

- [ ] **Step 3: Final commit only if Step 2 produced fixes**

---

## Spec coverage checklist

| Spec requirement | Task |
| ---------------- | ---- |
| `plan.advanced.percentiles` + default `[5, 50, 95]` | 1 |
| `normalize_percentiles` / validation | 1 |
| Shared bond NPV including current | 2 |
| Tax proration (signed taxes) | 3 |
| Wealth composition by source | 4 |
| `RawSimulationResult` private / public percentile result | 5 |
| `numpy.percentile` aggregation | 5 |
| `run_simulation` wiring + kwarg override | 6 |
| `start_month` + horizon vs `Timeline` | 6 |
| OVERVIEW / README / rebuild-index | 7 |
| `make` passes | 8 |
| No chart UI | (out of scope — no task) |
| Deferred tpaw series | documented in 7 |

---

## Placeholder / consistency notes

- Public composition field names: `wealth_job`, `wealth_social_security`, `wealth_pension`, `wealth_manual` (match spec).
- `WealthBySource` attributes: `job`, `social_security`, `pension`, `manual`.
- Engine returns `RawSimulationResult`; package export is public `SimulationResult` only.
- Do not re-export `RawSimulationResult` from `simulation.__init__`.

# Phase 3b — TPAW Monthly Withdrawal Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the full TPAW monthly withdrawal engine in `packages/simulation` — risk/RRA, Merton's formula, present-value precompute, and a vectorized forward monthly loop — producing raw per-run balance and withdrawal arrays.

**Architecture:** A `preprocess` step turns a `Plan` plus Phase 3a stochastic inputs (return paths + scalar inflation) into per-month risk/allocation/NPV arrays; a vectorized NumPy `engine` then runs the forward monthly loop with runs as the array axis and months sequential. Math primitives (RRA, Merton, NPV discounting, contributions/withdrawals, allocation) are pure functions pinned to tpaw's own doctest values.

**Tech Stack:** Python 3.14, NumPy (float64), Pydantic v2, pytest, ruff, pyright; uv workspace.

**Spec:** [2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md](../specs/2026-06-29-phase-3b-simulation-tpaw-withdrawals-design.md)

**tpaw references (read-only, in the `tpaw` workspace folder):**
- `packages/simulator-cuda/src/simulate/cuda_process_run_x_mfn_simulated_x_mfn/mertons_formula.h`
- `packages/simulator-rust/src/lib/simulate/process_plan_params_server/process_risk.rs`
- `packages/simulator-cuda/src/simulate/cuda_process_run_x_mfn_simulated_x_mfn/cuda_process_tpaw_run_x_mfn_simulated_x_mfn.cu`
- `packages/simulator-cuda/src/simulate/run/run_tpaw.cu`
- `packages/simulator-cuda/src/simulate/run/run_common.cu`

---

## File Structure

**Create:**
- `packages/simulation/simulation/risk.py` — risk-tolerance → RRA conversions + pinned constants
- `packages/simulation/simulation/mertons.py` — Merton's formula (stock allocation + spending tilt)
- `packages/simulation/simulation/planning_returns.py` — resolve planning expected returns + stock log-variance from vendored v7 series
- `packages/simulation/simulation/npv.py` — per-month NPV precompute helpers + amortization factor
- `packages/simulation/simulation/withdrawals.py` — `AccountForWithdrawal`, contributions/withdrawals, allocation primitives
- `packages/simulation/simulation/engine.py` — vectorized forward monthly loop
- `packages/simulation/simulation/preprocess.py` — assemble processed inputs
- `packages/simulation/README.md` — human-readable simulation flow
- `packages/simulation/OVERVIEW.md` — parity backlog + caveats
- Tests: `test_risk.py`, `test_mertons.py`, `test_planning_returns.py`, `test_npv.py`, `test_withdrawals.py`, `test_engine.py`, `test_preprocess.py`, `test_run_simulation.py` under `packages/simulation/tests/`

**Modify:**
- `packages/core/core/models.py` — add `RiskConfig`, `PlanningReturnsConfig`, spending fields, constants
- `packages/simulation/simulation/result.py` — expand `SimulationResult`
- `packages/simulation/simulation/stub.py` — replace stub body of `run_simulation` with real wiring (keep signature)
- `packages/simulation/simulation/__init__.py` — export new symbols
- `docs/superpowers/plans/2026-06-12-rebuild-index.md` — active phase + 3b/3c entries

**Shared numeric helper:** reuse `annual_to_monthly` from `simulation/market_data/inflation.py` (`(1+annual)**(1/12)-1`). Where a module must not import from `market_data`, define a local `_annual_to_monthly` (one-liner) — call this out in the task.

---

## Conventions for every task

- Run commands from the **repo root** `/Users/chris/Projects/life-finances-workspace/LifeFInances`.
- Run a single test file: `uv run pytest packages/simulation/tests/<file>.py -v`
- TDD: write the failing test, then add minimal scaffolding (stub functions/classes raising `NotImplementedError`) so the test *runs*. Run it once and confirm the failure is **logical** (`AssertionError`/`NotImplementedError`), not **structural** (`ImportError`/`AttributeError`/`ModuleNotFoundError`) — if structural, the scaffolding is incomplete; fix it before checklisting the run. Do not checklist a separate "run and confirm structural failure" step. Modules that are pure data/config (no branching logic to stub, e.g. Task 1's `Plan` fields, Task 7's `SimulationResult`) skip the scaffolding sub-step entirely: write the test, implement directly, then run once for PASS.
- **Fragile values:** never repeat the same literal in both arrange/act and assert — bind shared inputs to named variables and derive expected values from them. tpaw doctest goldens are the exception: pin the expected value once with a `# pinned: tpaw …` comment (contract tests).
- tpaw doctest goldens are **intentionally pinned literals** — keep the `# pinned: tpaw <test name>` comment on each.
- Final task runs `make` and must pass before the phase is claimed complete.

---

## Task 1: Core schema — risk, planning returns, spending fields

**Files:**
- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_risk_and_planning_returns_config.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# packages/core/tests/test_risk_and_planning_returns_config.py
from decimal import Decimal

from core.models import (
    DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT,
    DEFAULT_DELTA_AT_MAX_AGE,
    DEFAULT_LEGACY_DELTA_FROM_AT_20,
    DEFAULT_RISK_TOLERANCE_AT_20,
    DEFAULT_TIME_PREFERENCE,
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_NUM_VALUES,
    RISK_TOLERANCE_START_RRA,
    PlanningReturnsConfig,
    RiskConfig,
)
from core.models import Plan


def test_risk_config_defaults_match_constants():
    config = RiskConfig()

    assert config.risk_tolerance_at_20 == DEFAULT_RISK_TOLERANCE_AT_20
    assert config.delta_at_max_age == DEFAULT_DELTA_AT_MAX_AGE
    assert config.legacy_delta_from_at_20 == DEFAULT_LEGACY_DELTA_FROM_AT_20
    assert config.time_preference == DEFAULT_TIME_PREFERENCE
    assert config.additional_annual_spending_tilt == (
        DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT
    )


def test_pinned_rra_constants():
    # pinned: tpaw get_test_plan_params_server constants
    assert RISK_TOLERANCE_NUM_VALUES == 25
    assert RISK_TOLERANCE_START_RRA == 16.0
    assert RISK_TOLERANCE_END_RRA == 0.5


def test_plan_has_tpaw_blocks_with_defaults(make_plan):
    plan = make_plan()
    expected_legacy_target = Decimal(0)

    assert isinstance(plan.risk, RiskConfig)
    assert isinstance(plan.planning_returns, PlanningReturnsConfig)
    assert plan.extra_essential_spending == []
    assert plan.extra_discretionary_spending == []
    assert plan.legacy_target == expected_legacy_target
```

If no `make_plan` fixture exists in `packages/core/tests/conftest.py`, build a `Plan` inline using the same construction the existing core tests use (check `packages/core/tests/test_projection.py` for the minimal `Plan(...)` shape) instead of the fixture.

- [ ] **Step 2: Implement the config**

Pure data/config — no branching logic to scaffold separately, so implement directly (see Conventions).

In `packages/core/core/models.py`, add near the other module constants:

```python
DEFAULT_RISK_TOLERANCE_AT_20 = Decimal(12)  # tpaw default test plan "Moderate"
DEFAULT_DELTA_AT_MAX_AGE = Decimal(0)
DEFAULT_LEGACY_DELTA_FROM_AT_20 = Decimal(0)
DEFAULT_TIME_PREFERENCE = Decimal(0)
DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT = Decimal(0)

# Pinned tpaw risk-tolerance -> RRA scale constants. Not user-editable.
RISK_TOLERANCE_NUM_VALUES = 25
RISK_TOLERANCE_START_RRA = 16.0
RISK_TOLERANCE_END_RRA = 0.5

DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS = Decimal("0.05")
DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS = Decimal("0.02")
```

Add the models:

```python
class RiskConfig(BaseModel):
    risk_tolerance_at_20: Decimal = Field(default=DEFAULT_RISK_TOLERANCE_AT_20, ge=0)
    delta_at_max_age: Decimal = DEFAULT_DELTA_AT_MAX_AGE
    legacy_delta_from_at_20: Decimal = DEFAULT_LEGACY_DELTA_FROM_AT_20
    time_preference: Decimal = DEFAULT_TIME_PREFERENCE
    additional_annual_spending_tilt: Decimal = (
        DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT
    )


class PlanningReturnsConfig(BaseModel):
    expected_annual_return_stocks: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS
    expected_annual_return_bonds: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS
```

Extend `Plan` with the new fields (alongside `sampling` / `inflation`):

```python
    risk: RiskConfig = Field(default_factory=RiskConfig)
    planning_returns: PlanningReturnsConfig = Field(
        default_factory=PlanningReturnsConfig
    )
    extra_essential_spending: list[TimedStream] = Field(default_factory=list)
    extra_discretionary_spending: list[TimedStream] = Field(default_factory=list)
    legacy_target: Decimal = Field(default=Decimal(0), ge=0)
```

> Default expected-return numbers (`0.05` / `0.02`) match the tpaw bench/test values used in the doctest goldens; confirm against tpaw's default plan during implementation and adjust both here and the dependent goldens if they differ.

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_risk_and_planning_returns_config.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_risk_and_planning_returns_config.py
git commit -m "feat(core): add TPAW risk, planning-returns, and spending plan config"
```

---

## Task 2: Risk-tolerance → RRA conversions (`risk.py`)

Mirrors `process_risk.rs`. RRA = `1 / exp((risk_tolerance - 1) / scale + shift)` with `shift = ln(1/start_rra)`, `scale = (num_values - 2) / (ln(1/end_rra) - ln(1/start_rra))`; risk tolerance `0` → `inf`. Endpoints are exact by construction: rt `1`→`16.0`, rt `24`→`0.5`.

**Files:**
- Create: `packages/simulation/simulation/risk.py`
- Test: `packages/simulation/tests/test_risk.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/simulation/tests/test_risk.py
import math

import numpy as np
from core.models import (
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_START_RRA,
    RiskConfig,
)

from simulation.risk import (
    legacy_rra,
    risk_tolerance_to_rra,
    rra_by_month,
)


def test_endpoints_are_pinned_rra_values():
    # By construction rt=1 -> start_rra, rt=24 -> end_rra.
    conservative_tolerance = 1.0
    aggressive_tolerance = 24.0

    assert risk_tolerance_to_rra(conservative_tolerance) == RISK_TOLERANCE_START_RRA
    assert risk_tolerance_to_rra(aggressive_tolerance) == RISK_TOLERANCE_END_RRA


def test_zero_tolerance_is_infinite_rra():
    assert math.isinf(risk_tolerance_to_rra(0.0))


def test_rra_is_monotonic_decreasing_in_tolerance():
    values = [risk_tolerance_to_rra(rt) for rt in range(1, 25)]
    assert all(earlier > later for earlier, later in zip(values, values[1:]))


def test_rra_by_month_flat_when_no_age_delta():
    config = RiskConfig()  # delta_at_max_age == 0
    num_months = 12

    result = rra_by_month(
        config, num_months=num_months, current_age_months=360, max_age_months=1200
    )

    expected = risk_tolerance_to_rra(float(config.risk_tolerance_at_20))
    assert result.shape == (num_months,)
    assert np.allclose(result, expected)


def test_legacy_rra_uses_legacy_delta():
    risk_tolerance_at_20 = 12
    legacy_delta_from_at_20 = -4
    config = RiskConfig(risk_tolerance_at_20=risk_tolerance_at_20, legacy_delta_from_at_20=legacy_delta_from_at_20)

    assert legacy_rra(config) == risk_tolerance_to_rra(risk_tolerance_at_20 + legacy_delta_from_at_20)
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/risk.py
from __future__ import annotations

import numpy as np
from core.models import RiskConfig


def risk_tolerance_to_rra(risk_tolerance: float) -> float:
    raise NotImplementedError


def rra_by_month(
    config: RiskConfig, *, num_months: int, current_age_months: int, max_age_months: int
) -> np.ndarray:
    raise NotImplementedError


def legacy_rra(config: RiskConfig) -> float:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_risk.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `risk.py`**

```python
from __future__ import annotations

import math

import numpy as np
from core.models import (
    RISK_TOLERANCE_END_RRA,
    RISK_TOLERANCE_NUM_VALUES,
    RISK_TOLERANCE_START_RRA,
    RiskConfig,
)


def _ln_one_over(x: float) -> float:
    return math.log(1.0 / x)


def risk_tolerance_to_rra(risk_tolerance: float) -> float:
    """Map the user-facing risk tolerance slider (1–24) to relative risk aversion (RRA).

    Tolerance 0 maps to infinity (0% stocks). For 1–24, RRA is computed on a
    log scale pinned at two endpoints: tolerance 1 → start RRA (16.0),
    tolerance 24 → end RRA (0.5). ``shift`` anchors the curve at the conservative
    end; ``scale`` stretches the axis so the aggressive end lands on target.
  """
    if risk_tolerance == 0.0:
        return math.inf
    shift = _ln_one_over(RISK_TOLERANCE_START_RRA)
    scale = (RISK_TOLERANCE_NUM_VALUES - 2.0) / (
        _ln_one_over(RISK_TOLERANCE_END_RRA) - _ln_one_over(RISK_TOLERANCE_START_RRA)
    )
    return 1.0 / math.exp((risk_tolerance - 1.0) / scale + shift)


def _interpolate_risk_tolerance(
    config: RiskConfig,
    *,
    age_months: float,
    max_age_months: int,
) -> float:
    at_20 = float(config.risk_tolerance_at_20)
    if max_age_months <= 20 * 12:
        return max(0.0, at_20)
    at_max = at_20 + float(config.delta_at_max_age)
    fraction = (age_months - 20.0 * 12.0) / (max_age_months - 20.0 * 12.0)
    return max(0.0, at_20 + (at_max - at_20) * fraction)


def rra_by_month(
    config: RiskConfig,
    *,
    num_months: int,
    current_age_months: int,
    max_age_months: int,
) -> np.ndarray:
    result = np.empty(num_months, dtype=np.float64)
    for month in range(num_months):
        risk_tolerance = _interpolate_risk_tolerance(
            config,
            age_months=current_age_months + month,
            max_age_months=max_age_months,
        )
        result[month] = risk_tolerance_to_rra(risk_tolerance)
    return result


def legacy_rra(config: RiskConfig) -> float:
    risk_tolerance = float(config.risk_tolerance_at_20) + float(
        config.legacy_delta_from_at_20
    )
    return risk_tolerance_to_rra(risk_tolerance)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_risk.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/risk.py packages/simulation/tests/test_risk.py
git commit -m "feat(simulation): port tpaw risk-tolerance to RRA conversions"
```

---

## Task 3: Merton's formula (`mertons.py`)

Mirrors `mertons_formula.h`. Closure: `equity_premium_by_variance = ep/var`; `c1 = ep^2/(2*var)`; `c0 = bond_r - time_preference + c1`. Effective RRA clamps the equity premium to ≥ 0 and clamps RRA up to `rra_for_all_stocks = ep/var` (so allocation never exceeds 100%). Spending tilt is annual then converted to monthly via `(1+annual)**(1/12)-1`.

**Files:**
- Create: `packages/simulation/simulation/mertons.py`
- Test: `packages/simulation/tests/test_mertons.py`

- [ ] **Step 1: Write the failing test (tpaw doctest goldens)**

```python
# packages/simulation/tests/test_mertons.py
import math

import pytest

from simulation.mertons import (
    effective_mertons,
    get_rra_for_all_stocks,
    plain_mertons,
)

TOL = 1e-9


# Each case: (annual_stock, annual_bond, variance, rra, time_pref, add_tilt,
#             expected_stock_allocation, expected_monthly_spending_tilt)
# pinned: tpaw mertons_formula.cu plain_mertons_formula TEST_CASE
PLAIN_CASES = [
    # RRA=4
    (0.05, 0.03, 0.01, 4.0, 0.01, 0.0, 0.5000000000000001, 0.0009327004773649339),
    # RRA=0.04, Very low RRA → >100% raw equity allocation (50×)
    (0.05, 0.03, 0.01, 0.04, 0.01, 0.0, 50.00000000000001, 0.24962776727305425),
    # Infinite RRA → 0% stocks
    (0.05, 0.03, 0.01, math.inf, 0.01, 0.0, 0.0, 0.0),
    # Zero equity premium → 0% stocks
    (0.03, 0.03, 0.01, 4.0, 0.01, 0.0, 0.0, 0.00041571484472902043),
    # Negative time preference
    (0.05, 0.03, 0.01, 4.0, -0.1, 0.0, 0.5000000000000001, 0.003173196227570285),
    # additional spending tilt
    (0.05, 0.03, 0.01, 4.0, 0.01, 1.0, 0.5000000000000001, 0.059958441910258564),
    # effective floor for RRA (most aggressive equity allocation Merton allows without leverage)
    (0.05, 0.03, 0.01, 2.0000000000000004, 0.01, 0.0, 1.0, 0.002059836269842741),
]


@pytest.mark.parametrize(
    "stock,bond,var,rra,tp,tilt,exp_alloc,exp_tilt", PLAIN_CASES
)
def test_plain_mertons_matches_tpaw(stock, bond, var, rra, tp, tilt, exp_alloc, exp_tilt):
    result = plain_mertons(
        annual_bond_return=bond,
        annual_equity_premium=stock - bond,
        annual_variance_stocks=var,
        rra=rra,
        time_preference=tp,
        annual_additional_spending_tilt=tilt,
    )

    assert result.stock_allocation == pytest.approx(exp_alloc, abs=TOL)
    assert result.spending_tilt == pytest.approx(exp_tilt, abs=TOL)


# pinned: tpaw mertons_formula.cu effective_mertons_formula TEST_CASE
EFFECTIVE_CASES = [
    # passthru
    (0.05, 0.03, 0.01, 4.0, 0.01, 0.0, 0.5000000000000001, 0.0009327004773649339),
    # effective floor for rra
    (0.05, 0.03, 0.01, 2.0000000000000004, 0.01, 0.0, 1.0, 0.002059836269842741),
    # below the effective floor
    (0.05, 0.03, 0.01, 0.05, 0.01, 0.0, 1.0, 0.002059836269842741),
    # neg equity premium
    (0.02, 0.03, 0.01, 4.0, 0.01, 0.0, 0.0, 0.00041571484472902043),
]


@pytest.mark.parametrize(
    "stock,bond,var,rra,tp,tilt,exp_alloc,exp_tilt", EFFECTIVE_CASES
)
def test_effective_mertons_matches_tpaw(stock, bond, var, rra, tp, tilt, exp_alloc, exp_tilt):
    result = effective_mertons(
        annual_bond_return=bond,
        annual_equity_premium=stock - bond,
        annual_variance_stocks=var,
        rra=rra,
        time_preference=tp,
        annual_additional_spending_tilt=tilt,
    )

    assert result.stock_allocation == pytest.approx(exp_alloc, abs=TOL)
    assert result.spending_tilt == pytest.approx(exp_tilt, abs=TOL)


def test_get_rra_for_all_stocks():
    # pinned: tpaw mertons_formula.cu _get_rra_for_all_stocks TEST_CASE
    annual_stock = 0.05
    annual_bond = 0.03
    variance = 0.01
    equity_premium = annual_stock - annual_bond
    expected_rra_typical = 2.0000000000000004  # pinned contract value from tpaw doctest
    expected_rra_zero_premium = 0.0

    assert get_rra_for_all_stocks(equity_premium, variance) == pytest.approx(
        expected_rra_typical, abs=TOL
    )
    assert get_rra_for_all_stocks(annual_bond - annual_bond, variance) == pytest.approx(
        expected_rra_zero_premium, abs=TOL
    )
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/mertons.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MertonsResult:
    stock_allocation: float
    spending_tilt: float


def get_rra_for_all_stocks(annual_equity_premium: float, annual_variance: float) -> float:
    raise NotImplementedError


def plain_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    raise NotImplementedError


def effective_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_mertons.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `mertons.py`**

```python
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class MertonsResult:
    stock_allocation: float
    spending_tilt: float  # monthly


def _annual_to_monthly(annual: float) -> float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def get_rra_for_all_stocks(annual_equity_premium: float, annual_variance: float) -> float:
    """The RRA that would return 100% equity allocation"""
    return annual_equity_premium / annual_variance


def plain_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    ep_by_var = annual_equity_premium / annual_variance_stocks
    ep_pow2_by_2var = annual_equity_premium * ep_by_var * 0.5
    c0 = annual_bond_return - time_preference + ep_pow2_by_2var
    c1 = ep_pow2_by_2var

    if math.isinf(rra):
        return MertonsResult(
            stock_allocation=0.0,
            spending_tilt=_annual_to_monthly(annual_additional_spending_tilt),
        )

    one_over_gamma = 1.0 / rra
    stock_allocation = ep_by_var * one_over_gamma
    annual_spending_tilt = (
        one_over_gamma * c0
        + one_over_gamma * one_over_gamma * c1
        + annual_additional_spending_tilt
    )
    return MertonsResult(
        stock_allocation=stock_allocation,
        spending_tilt=_annual_to_monthly(annual_spending_tilt),
    )


def effective_mertons(
    *,
    annual_bond_return: float,
    annual_equity_premium: float,
    annual_variance_stocks: float,
    rra: float,
    time_preference: float,
    annual_additional_spending_tilt: float,
) -> MertonsResult:
    effective_equity_premium = max(0.0, annual_equity_premium)
    rra_for_all_stocks = get_rra_for_all_stocks(
        effective_equity_premium, annual_variance_stocks
    )
    effective_rra = max(rra_for_all_stocks, rra)
    result = plain_mertons(
        annual_bond_return=annual_bond_return,
        annual_equity_premium=effective_equity_premium,
        annual_variance_stocks=annual_variance_stocks,
        rra=effective_rra,
        time_preference=time_preference,
        annual_additional_spending_tilt=annual_additional_spending_tilt,
    )
    return MertonsResult(
        stock_allocation=min(1.0, max(0.0, result.stock_allocation)),
        spending_tilt=result.spending_tilt,
    )
```

> Note: the plain-formula `< min rra` case (rra=0.05) is only clamped in `effective_mertons`; `plain_mertons` returns the raw 50× value, matching tpaw.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_mertons.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/mertons.py packages/simulation/tests/test_mertons.py
git commit -m "feat(simulation): port tpaw Merton's formula (allocation + spending tilt)"
```

---

## Task 4: Planning returns + stock variance from vendored series (`planning_returns.py`)

Resolve scalar planning expected returns from the `Plan` and compute the annual stock log-variance from the vendored v7 series (`load_historical_returns().stocks_log`). tpaw's empirical-stats-by-block-size refinement is deferred to 3c; here we use the plain sample variance of monthly log returns annualized by ×12.

**Files:**
- Create: `packages/simulation/simulation/planning_returns.py`
- Test: `packages/simulation/tests/test_planning_returns.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/simulation/tests/test_planning_returns.py
from decimal import Decimal

import numpy as np

from simulation.market_data import load_historical_returns
from simulation.planning_returns import (
    PlanningReturns,
    annual_stock_log_variance,
    resolve_planning_returns,
)


def _plan_with_returns(make_plan, stocks, bonds):
    plan = make_plan()
    plan.planning_returns.expected_annual_return_stocks = stocks
    plan.planning_returns.expected_annual_return_bonds = bonds
    return plan


def test_resolves_expected_returns_from_plan(make_plan):
    expected_annual_stocks = 0.06
    expected_annual_bonds = 0.025
    plan = _plan_with_returns(
        make_plan,
        Decimal(str(expected_annual_stocks)),
        Decimal(str(expected_annual_bonds)),
    )

    result = resolve_planning_returns(plan)

    assert isinstance(result, PlanningReturns)
    assert result.annual_stocks == expected_annual_stocks
    assert result.annual_bonds == expected_annual_bonds


def test_stock_variance_matches_vendored_series():
    expected = float(np.var(load_historical_returns().stocks_log) * 12.0)

    assert annual_stock_log_variance() == expected
```

If `make_plan` is unavailable, construct a minimal `Plan` inline as in Task 1.

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/planning_returns.py
from __future__ import annotations

from dataclasses import dataclass

from core.models import Plan


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float


def annual_stock_log_variance() -> float:
    raise NotImplementedError


def resolve_planning_returns(plan: Plan) -> PlanningReturns:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_planning_returns.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `planning_returns.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from core.models import Plan

from simulation.market_data import load_historical_returns


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float


@lru_cache(maxsize=1)
def annual_stock_log_variance() -> float:
    stocks_log = load_historical_returns().stocks_log
    return float(np.var(stocks_log) * 12.0)


def resolve_planning_returns(plan: Plan) -> PlanningReturns:
    config = plan.planning_returns
    return PlanningReturns(
        annual_stocks=float(config.expected_annual_return_stocks),
        annual_bonds=float(config.expected_annual_return_bonds),
        annual_stock_log_variance=annual_stock_log_variance(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_planning_returns.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/planning_returns.py packages/simulation/tests/test_planning_returns.py
git commit -m "feat(simulation): resolve planning returns + vendored stock log-variance"
```

---

## Task 5: Withdrawal primitives (`withdrawals.py`)

Mirrors `run_common.cu`. `AccountForWithdrawal` clamps each draw to the running balance. `apply_contributions_and_withdrawals` adds income, subtracts essential→discretionary→general (clamped), computes the savings-portfolio withdrawal rate `(total - contributions) / starting_balance`, and flags insufficient funds. `apply_allocation` splits the post-withdrawal balance by stock fraction and applies returns. These are scalar/array-agnostic (work on floats or NumPy arrays via plain arithmetic); tests use floats against tpaw goldens.

**Files:**
- Create: `packages/simulation/simulation/withdrawals.py`
- Test: `packages/simulation/tests/test_withdrawals.py`

- [ ] **Step 1: Write the failing test (tpaw goldens)**

```python
# packages/simulation/tests/test_withdrawals.py
import pytest

from simulation.withdrawals import (
    apply_allocation,
    apply_contributions_and_withdrawals,
)

TOL = 1e-9


def test_contributions_and_withdrawals_sufficient():
    # pinned: tpaw run_common.cu apply_contributions_and_withdrawals sufficient_funds
    balance_starting = 10000.0
    contributions = 1000.0
    essential = 1000.0
    discretionary = 2000.0
    general = 3000.0

    result = apply_contributions_and_withdrawals(
        balance_starting=balance_starting,
        contributions=contributions,
        essential=essential,
        discretionary=discretionary,
        general=general,
    )

    expected_total = essential + discretionary + general
    assert result.essential == pytest.approx(essential, abs=TOL)
    assert result.discretionary == pytest.approx(discretionary, abs=TOL)
    assert result.general == pytest.approx(general, abs=TOL)
    assert result.total == pytest.approx(expected_total, abs=TOL)
    assert result.from_savings_rate == pytest.approx(
        (expected_total - contributions) / balance_starting, abs=TOL
    )
    assert result.balance == pytest.approx(
        balance_starting + contributions - expected_total, abs=TOL
    )
    assert result.insufficient is False


def test_contributions_and_withdrawals_insufficient():
    # pinned: tpaw run_common.cu apply_contributions_and_withdrawals insufficient_funds
    balance_starting = 3000.0
    contributions = 1000.0
    essential = 1000.0
    discretionary = 2000.0
    general = 3000.0

    result = apply_contributions_and_withdrawals(
        balance_starting=balance_starting,
        contributions=contributions,
        essential=essential,
        discretionary=discretionary,
        general=general,
    )

    expected_general = 1000.0  # pinned: clamped after essential + discretionary
    expected_total = essential + discretionary + expected_general

    assert result.general == pytest.approx(expected_general, abs=TOL)
    assert result.total == pytest.approx(expected_total, abs=TOL)
    assert result.from_savings_rate == pytest.approx(
        (expected_total - contributions) / balance_starting, abs=TOL
    )
    assert result.balance == pytest.approx(0.0, abs=TOL)
    assert result.insufficient is True


def test_apply_allocation_basic():
    # pinned: tpaw run_common.cu apply_allocation basic
    stock_allocation = 0.5
    stock_return = 0.05
    bond_return = 0.03
    balance = 1000.0
    npv_income = 100.0

    result = apply_allocation(
        stock_allocation=stock_allocation,
        stock_return=stock_return,
        bond_return=bond_return,
        balance=balance,
        npv_income_without_current_month=npv_income,
    )

    stocks_amount = balance * stock_allocation
    bonds_amount = balance - stocks_amount
    expected_balance = (
        stocks_amount * (1.0 + stock_return) + bonds_amount * (1.0 + bond_return)
    )
    total_portfolio = balance + npv_income

    assert result.balance == pytest.approx(expected_balance, abs=TOL)
    assert result.stock_allocation_on_total == pytest.approx(
        stocks_amount / total_portfolio, abs=TOL
    )
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/withdrawals.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContributionsAndWithdrawals:
    essential: float
    discretionary: float
    general: float
    total: float
    from_savings_rate: float
    balance: float
    insufficient: bool


@dataclass(frozen=True)
class AllocationResult:
    balance: float
    stock_allocation_on_total: float


def apply_contributions_and_withdrawals(
    *,
    balance_starting: float,
    contributions: float,
    essential: float,
    discretionary: float,
    general: float,
) -> ContributionsAndWithdrawals:
    raise NotImplementedError


def apply_allocation(
    *,
    stock_allocation: float,
    stock_return: float,
    bond_return: float,
    balance: float,
    npv_income_without_current_month: float,
) -> AllocationResult:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_withdrawals.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `withdrawals.py`**

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContributionsAndWithdrawals:
    essential: float
    discretionary: float
    general: float
    total: float
    from_savings_rate: float
    balance: float
    insufficient: bool


@dataclass(frozen=True)
class AllocationResult:
    balance: float
    stock_allocation_on_total: float


def _withdraw(balance: float, amount: float) -> tuple[float, float]:
    """Draw `amount` clamped to `balance`. Returns (withdrawn, remaining)."""
    withdrawn = amount if amount < balance else balance
    return withdrawn, balance - withdrawn


def apply_contributions_and_withdrawals(
    *,
    balance_starting: float,
    contributions: float,
    essential: float,
    discretionary: float,
    general: float,
) -> ContributionsAndWithdrawals:
    balance = balance_starting + contributions
    drawn_essential, balance = _withdraw(balance, essential)
    drawn_discretionary, balance = _withdraw(balance, discretionary)
    drawn_general, balance = _withdraw(balance, general)

    total = drawn_essential + drawn_discretionary + drawn_general
    requested = essential + discretionary + general
    from_savings_rate = (total - contributions) / balance_starting
    return ContributionsAndWithdrawals(
        essential=drawn_essential,
        discretionary=drawn_discretionary,
        general=drawn_general,
        total=total,
        from_savings_rate=from_savings_rate,
        balance=balance,
        insufficient=requested > balance_starting + contributions,
    )


def apply_allocation(
    *,
    stock_allocation: float,
    stock_return: float,
    bond_return: float,
    balance: float,
    npv_income_without_current_month: float,
) -> AllocationResult:
    stocks_amount = balance * stock_allocation
    bonds_amount = balance - stocks_amount
    ending_balance = stocks_amount * (1.0 + stock_return) + bonds_amount * (1.0 + bond_return)
    total_portfolio = balance + npv_income_without_current_month
    stock_on_total = (
        0.0 if total_portfolio == 0.0 else stocks_amount / total_portfolio
    )
    return AllocationResult(
        balance=ending_balance, stock_allocation_on_total=stock_on_total
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_withdrawals.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/withdrawals.py packages/simulation/tests/test_withdrawals.py
git commit -m "feat(simulation): port tpaw contributions/withdrawals and allocation primitives"
```

---

## Task 6: NPV precompute (`npv.py`)

Mirrors `_get_precomputation_at_start` and `_get_target_withdrawals_assuming_no_ceiling_or_floor` from `run_tpaw.cu`. These compute, given a wealth figure and the NPVs of essential/discretionary/legacy, the scaled-and-constrained spending pools and the target withdrawals. The full backward discounting pass (per-month NPV arrays) is assembled in `preprocess` (Task 8); this module provides the per-month pure helpers used by the forward loop.

**Files:**
- Create: `packages/simulation/simulation/npv.py`
- Test: `packages/simulation/tests/test_npv.py`

- [ ] **Step 1: Write the failing test (tpaw goldens)**

```python
# packages/simulation/tests/test_npv.py
import pytest

from simulation.npv import (
    expenses_scale_for_normal_run,
    precomputation_general_pool,
    target_general_withdrawal,
)

TOL = 1e-6


def test_expenses_scale_more_wealth():
    # pinned: tpaw run_tpaw.cu _get_precomputation_at_start "more wealth"
    balance = 100000.0
    npv_income = 40000.0
    current_income = 10000.0
    wealth = balance + npv_income + current_income
    scheduled_balance = 90000.0
    scheduled_npv_income = 50000.0
    scheduled_wealth = scheduled_balance + scheduled_npv_income
    elasticity_discretionary = 0.2
    elasticity_legacy = 0.5
    p_increase = (wealth - scheduled_wealth) / scheduled_wealth

    scale = expenses_scale_for_normal_run(
        wealth=wealth,
        scheduled_wealth=scheduled_wealth,
        elasticity_discretionary=elasticity_discretionary,
        elasticity_legacy=elasticity_legacy,
    )

    assert scale.discretionary == pytest.approx(
        p_increase * elasticity_discretionary + 1.0, abs=TOL
    )
    assert scale.legacy == pytest.approx(
        p_increase * elasticity_legacy + 1.0, abs=TOL
    )


def test_expenses_scale_clamped_to_zero():
    wealth = 0.0
    scheduled_wealth = 100000.0
    elasticity_discretionary = 10.0
    elasticity_legacy = 10.0

    scale = expenses_scale_for_normal_run(
        wealth=wealth,
        scheduled_wealth=scheduled_wealth,
        elasticity_discretionary=elasticity_discretionary,
        elasticity_legacy=elasticity_legacy,
    )

    assert scale.discretionary == 0.0
    assert scale.legacy == 0.0


def test_general_pool_is_wealth_minus_constrained_spending():
    # essential then discretionary*scale then legacy*scale, each clamped to balance.
    wealth = 150000.0

    pool = precomputation_general_pool(
        wealth=wealth,
        npv_essential=0.0,
        npv_discretionary=0.0,
        npv_legacy=0.0,
        scale_discretionary=1.0,
        scale_legacy=1.0,
    )

    assert pool == pytest.approx(wealth, abs=TOL)


def test_target_general_withdrawal_amortizes_pool():
    # pinned: tpaw run_tpaw.cu _get_target_withdrawals "withdrawal_started"
    general_pool = 50000.0
    cumulative = 0.05 # nonsense value, but matches tpaw

    result = target_general_withdrawal(
        withdrawal_started=True,
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
    )

    assert result == pytest.approx(general_pool / cumulative, abs=TOL)


def test_target_general_zero_before_withdrawal_start():
    general_pool = 50000.0
    cumulative = 0.05

    result = target_general_withdrawal(
        withdrawal_started=False,
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
    )

    assert result == 0.0
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/npv.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpensesScale:
    discretionary: float
    legacy: float


def expenses_scale_for_normal_run(
    *,
    wealth: float,
    scheduled_wealth: float,
    elasticity_discretionary: float,
    elasticity_legacy: float,
) -> ExpensesScale:
    raise NotImplementedError


def precomputation_general_pool(
    *,
    wealth: float,
    npv_essential: float,
    npv_discretionary: float,
    npv_legacy: float,
    scale_discretionary: float,
    scale_legacy: float,
) -> float:
    raise NotImplementedError


def target_general_withdrawal(
    *,
    withdrawal_started: bool,
    general_pool: float,
    cumulative_1_plus_g_over_1_plus_r: float,
) -> float:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_npv.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `npv.py`**

```python
from __future__ import annotations

from dataclasses import dataclass

from simulation.withdrawals import _withdraw


@dataclass(frozen=True)
class ExpensesScale:
    discretionary: float
    legacy: float


def expenses_scale_for_normal_run(
    *,
    wealth: float,
    scheduled_wealth: float,
    elasticity_discretionary: float,
    elasticity_legacy: float,
) -> ExpensesScale:
    if scheduled_wealth == 0.0:
        p_increase = 0.0
    else:
        p_increase = wealth / scheduled_wealth - 1.0
    return ExpensesScale(
        discretionary=max(0.0, p_increase * elasticity_discretionary + 1.0),
        legacy=max(0.0, p_increase * elasticity_legacy + 1.0),
    )


def precomputation_general_pool(
    *,
    wealth: float,
    npv_essential: float,
    npv_discretionary: float,
    npv_legacy: float,
    scale_discretionary: float,
    scale_legacy: float,
) -> float:
    balance = wealth
    _, balance = _withdraw(balance, npv_essential)
    _, balance = _withdraw(balance, npv_discretionary * scale_discretionary)
    _, balance = _withdraw(balance, npv_legacy * scale_legacy)
    return balance


def target_general_withdrawal(
    *,
    withdrawal_started: bool,
    general_pool: float,
    cumulative_1_plus_g_over_1_plus_r: float,
) -> float:
    if not withdrawal_started:
        return 0.0
    return general_pool / cumulative_1_plus_g_over_1_plus_r
```

> `_withdraw` is imported from `withdrawals.py` to keep the clamping rule DRY. These scalar helpers are the tpaw-pinned unit-test surface for the pool carve and spending-scale formulas (spec §7). The forward engine (Task 9) reimplements the same clamp as a vectorized `_carve_pools` (it needs array support plus the discretionary/legacy pools, not just the general remainder); the two must stay in sync — if you change the carve semantics here, update `engine._carve_pools` and vice versa.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_npv.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/npv.py packages/simulation/tests/test_npv.py
git commit -m "feat(simulation): port tpaw NPV precompute and general-withdrawal amortization"
```

---

## Task 7: Expanded result type (`result.py`)

**Files:**
- Modify: `packages/simulation/simulation/result.py`
- Test: `packages/simulation/tests/test_result.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# packages/simulation/tests/test_result.py
from datetime import datetime

import numpy as np

from simulation.result import SimulationResult


def test_simulation_result_holds_per_run_arrays():
    num_runs, months = 3, 4
    expected_insufficient = 0
    zeros = np.zeros((num_runs, months), dtype=np.float64)

    result = SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=zeros,
        withdrawals_essential=zeros,
        withdrawals_discretionary=zeros,
        withdrawals_general=zeros,
        withdrawals_total=zeros,
        savings_stock_allocation=zeros,
        num_runs_insufficient=expected_insufficient,
    )

    assert result.balance_start.shape == (num_runs, months)
    assert result.num_runs_insufficient == expected_insufficient
```

- [ ] **Step 2: Implement the expanded result**

Pure data model — no branching logic to scaffold separately, so implement directly (see Conventions).

Replace `packages/simulation/simulation/result.py` with:

```python
from __future__ import annotations

from datetime import datetime

import numpy as np
from pydantic import BaseModel, ConfigDict

ENGINE_VERSION = "phase3b"


class SimulationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ran_at: datetime
    horizon_months: int
    num_runs: int
    balance_start: np.ndarray
    withdrawals_essential: np.ndarray
    withdrawals_discretionary: np.ndarray
    withdrawals_general: np.ndarray
    withdrawals_total: np.ndarray
    savings_stock_allocation: np.ndarray
    num_runs_insufficient: int
    engine_version: str = ENGINE_VERSION
```

> This removes the Phase 1 `echo`/`STUB_VERSION` stub fields. Task 9 updates `run_simulation` and any remaining references (e.g. web results view, `__init__` exports) accordingly. Grep for `STUB_VERSION` and `.echo` before committing and fix all call sites in Task 9.

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_result.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add packages/simulation/simulation/result.py packages/simulation/tests/test_result.py
git commit -m "feat(simulation): expand SimulationResult to raw per-run arrays"
```

---

## Task 8: Preprocess — assemble per-month engine inputs (`preprocess.py`)

Builds the per-month arrays the forward loop consumes: real (inflation-adjusted) income / essential / discretionary series, per-month RRA, per-month Merton stock allocation + spending tilt (from planning returns), the legacy RRA + legacy stock allocation, and the backward NPV pass producing `npv_income_without_current_month`, `npv_essential_without_current_month`, `npv_discretionary_without_current_month`, `legacy_npv`, and `cumulative_1_plus_g_over_1_plus_r` per month. It also exposes the scalar monthly planning (expected) returns (`monthly_planning_stocks`, `monthly_planning_bonds`) so the engine's deterministic "expected run" advances balance at the same rates used for discounting. Mirrors `cuda_process_tpaw_run_x_mfn_simulated_x_mfn.cu` using the **planning (expected) returns** for discounting (3b uses scalar planning returns, so these are per-month, not per-run).

**Files:**
- Create: `packages/simulation/simulation/preprocess.py`
- Test: `packages/simulation/tests/test_preprocess.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/simulation/tests/test_preprocess.py
from datetime import date
from decimal import Decimal

import numpy as np

from simulation.preprocess import ProcessedPlan, preprocess


def test_preprocess_shapes_and_basic_invariants(make_plan):
    plan = make_plan()
    today = date(2026, 1, 1)

    processed = preprocess(plan, today=today)

    months = processed.months
    assert isinstance(processed, ProcessedPlan)
    assert processed.income_real.shape == (months,)
    assert processed.essential_real.shape == (months,)
    assert processed.discretionary_real.shape == (months,)
    assert processed.stock_allocation_total_portfolio.shape == (months,)
    assert processed.spending_tilt.shape == (months,)
    assert processed.cumulative_1_plus_g_over_1_plus_r.shape == (months,)
    # Allocation is a fraction in [0, 1].
    assert np.all(processed.stock_allocation_total_portfolio >= 0.0)
    assert np.all(processed.stock_allocation_total_portfolio <= 1.0)


def test_legacy_npv_zero_when_no_legacy_target(make_plan):
    plan = make_plan()
    expected_legacy_target = Decimal(0)
    plan.legacy_target = expected_legacy_target
    today = date(2026, 1, 1)

    processed = preprocess(plan, today=today)

    assert np.allclose(processed.legacy_npv, 0.0)
```

Use the existing `make_plan`/`repo` fixtures from the repo-root `conftest.py`; if a builder is needed, mirror the construction in `packages/simulation/tests/test_horizon.py`.

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/preprocess.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from core.models import Plan


@dataclass(frozen=True)
class ProcessedPlan:
    months: int
    starting_balance: float
    income_real: np.ndarray
    essential_real: np.ndarray
    discretionary_real: np.ndarray
    rra: np.ndarray
    stock_allocation_total_portfolio: np.ndarray
    legacy_stock_allocation: float
    spending_tilt: np.ndarray
    npv_income_without_current: np.ndarray
    npv_essential_without_current: np.ndarray
    npv_discretionary_without_current: np.ndarray
    legacy_npv: np.ndarray
    cumulative_1_plus_g_over_1_plus_r: np.ndarray
    # Scalar monthly planning (expected) returns — drive the deterministic
    # "expected run" balance trajectory that establishes scheduled wealth.
    monthly_planning_stocks: float
    monthly_planning_bonds: float


def preprocess(plan: Plan, *, today: date | None = None) -> ProcessedPlan:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_preprocess.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `preprocess.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from core.models import Plan
from core.timeline import Timeline, project_stream
from domain import build_monthly_cashflows

from simulation.market_data import resolve_inflation
from simulation.mertons import effective_mertons
from simulation.planning_returns import resolve_planning_returns
from simulation.risk import legacy_rra, rra_by_month


@dataclass(frozen=True)
class ProcessedPlan:
    months: int
    starting_balance: float
    income_real: np.ndarray
    essential_real: np.ndarray
    discretionary_real: np.ndarray
    rra: np.ndarray
    stock_allocation_total_portfolio: np.ndarray
    legacy_stock_allocation: float
    spending_tilt: np.ndarray
    npv_income_without_current: np.ndarray
    npv_essential_without_current: np.ndarray
    npv_discretionary_without_current: np.ndarray
    legacy_npv: np.ndarray
    cumulative_1_plus_g_over_1_plus_r: np.ndarray
    monthly_planning_stocks: float
    monthly_planning_bonds: float


def _sum_streams(streams, timeline) -> np.ndarray:
    months = timeline.horizon_months
    total = np.zeros(months, dtype=np.float64)
    for stream in streams:
        series = project_stream(stream, timeline)
        total += np.array([float(value) for value in series], dtype=np.float64)
    return total


def _current_age_months(person, today: date) -> int:
    return (today.year - person.birth_year) * 12 + (today.month - person.birth_month)


def preprocess(plan: Plan, *, today: date | None = None) -> ProcessedPlan:
    today = today or date.today()
    timeline = Timeline(plan, today=today)
    months = timeline.horizon_months

    cashflows = build_monthly_cashflows(plan, today=today)
    inflation = resolve_inflation(plan, today=today)
    planning = resolve_planning_returns(plan)

    # Real conversion: divide month t nominal by (1 + monthly_inflation) ** t.
    deflator = (1.0 + inflation.monthly) ** np.arange(months, dtype=np.float64)
    income_nominal = np.array(
        [float(value) for value in cashflows.net_cashflow], dtype=np.float64
    )
    income_real = income_nominal / deflator
    essential_real = _sum_streams(plan.extra_essential_spending, timeline) / deflator
    discretionary_real = (
        _sum_streams(plan.extra_discretionary_spending, timeline) / deflator
    )

    # Per-month RRA from the longer-lived person's age glide.
    people = plan.household.people
    longer = max(people, key=lambda p: p.max_age_years)
    rra = rra_by_month(
        plan.risk,
        num_months=months,
        current_age_months=_current_age_months(longer, today),
        max_age_months=longer.max_age_years * 12,
    )

    # Per-month Merton allocation + spending tilt using planning returns.
    equity_premium = planning.annual_stocks - planning.annual_bonds
    stock_alloc = np.empty(months, dtype=np.float64)
    spending_tilt = np.empty(months, dtype=np.float64)
    for month in range(months):
        merton = effective_mertons(
            annual_bond_return=planning.annual_bonds,
            annual_equity_premium=equity_premium,
            annual_variance_stocks=planning.annual_stock_log_variance,
            rra=float(rra[month]),
            time_preference=float(plan.risk.time_preference),
            annual_additional_spending_tilt=float(
                plan.risk.additional_annual_spending_tilt
            ),
        )
        stock_alloc[month] = merton.stock_allocation
        spending_tilt[month] = merton.spending_tilt

    legacy_alloc = effective_mertons(
        annual_bond_return=planning.annual_bonds,
        annual_equity_premium=equity_premium,
        annual_variance_stocks=planning.annual_stock_log_variance,
        rra=legacy_rra(plan.risk),
        time_preference=0.0,
        annual_additional_spending_tilt=0.0,
    ).stock_allocation

    monthly_bonds = (1.0 + planning.annual_bonds) ** (1.0 / 12.0) - 1.0
    monthly_stocks = (1.0 + planning.annual_stocks) ** (1.0 / 12.0) - 1.0
    one_over_1p_bonds = 1.0 / (1.0 + monthly_bonds)

    # Backward NPV pass
    npv_income = np.zeros(months, dtype=np.float64)
    npv_essential = np.zeros(months, dtype=np.float64)
    npv_discretionary = np.zeros(months, dtype=np.float64)
    cumulative = np.zeros(months, dtype=np.float64)

    income_with_current = 0.0
    essential_with_current = 0.0
    discretionary_with_current = 0.0
    for month in range(months - 1, -1, -1):
        monthly_premium = monthly_stocks - monthly_bonds
        one_plus_r_portfolio = 1.0 + (
            monthly_premium * stock_alloc[month] + monthly_bonds
        )
        one_over_r_portfolio = 1.0 / one_plus_r_portfolio

        # income/essential at bond rate; discretionary/general at portfolio rate
        income_with_current = income_with_current * one_over_1p_bonds + income_real[month]
        essential_with_current = essential_with_current * one_over_1p_bonds + essential_real[month]
        discretionary_with_current = (
            discretionary_with_current * one_over_r_portfolio + discretionary_real[month]
        )

        # cumulative_1_plus_g_over_1_plus_r accumulates the tilt
        cumulative_running = cumulative[month + 1] if month + 1 < months else 0.0
        one_plus_g_over_r = (spending_tilt[month] + 1.0) / one_plus_r_portfolio
        cumulative[month] = cumulative_running * one_plus_g_over_r + 1.0

        npv_income[month] = income_with_current - income_real[month]
        npv_essential[month] = essential_with_current - essential_real[month]
        npv_discretionary[month] = discretionary_with_current - discretionary_real[month]

    # Legacy NPV per month at the legacy portfolio rate.
    legacy_target = float(plan.legacy_target)
    months_left = np.arange(months, dtype=np.float64)[::-1]  # months-1 .. 0
    r_legacy = (monthly_stocks - monthly_bonds) * legacy_alloc + monthly_bonds
    legacy_npv = legacy_target / np.power(1.0 + r_legacy, months_left + 1.0)

    return ProcessedPlan(
        months=months,
        starting_balance=float(plan.portfolio.current_savings_balance),
        income_real=income_real,
        essential_real=essential_real,
        discretionary_real=discretionary_real,
        rra=rra,
        stock_allocation_total_portfolio=stock_alloc,
        legacy_stock_allocation=legacy_alloc,
        spending_tilt=spending_tilt,
        npv_income_without_current=npv_income,
        npv_essential_without_current=npv_essential,
        npv_discretionary_without_current=npv_discretionary,
        legacy_npv=legacy_npv,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
        monthly_planning_stocks=monthly_stocks,
        monthly_planning_bonds=monthly_bonds,
    )
```

> `build_monthly_cashflows` returns `MonthlyCashflows` with `net_cashflow: list[Decimal]` (see `packages/domain/domain/__init__.py`). If its horizon length differs from `timeline.horizon_months`, align by trusting the domain length and slicing/padding `deflator` to match; add an assertion `len(cashflows.net_cashflow) == months` and fix the smaller mismatch source rather than silently truncating.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/simulation/tests/test_preprocess.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/simulation/simulation/preprocess.py packages/simulation/tests/test_preprocess.py
git commit -m "feat(simulation): assemble per-month engine inputs (risk, merton, NPV)"
```

---

## Task 9: Forward monthly engine + `run_simulation` wiring (`engine.py`, `stub.py`)

Vectorized forward loop over months, runs as the array axis. Mirrors `run_tpaw.cu::_kernel` / `_single_month`, but driven by the per-month planning-return precompute from Task 8 and the per-run bootstrapped returns from Phase 3a. The "expected run" is the planning-return path; elasticities are derived from it once per month, then normal runs scale discretionary/legacy by wealth ratio.

**Files:**
- Create: `packages/simulation/simulation/engine.py`
- Modify: `packages/simulation/simulation/stub.py` (rename conceptually to real wiring; keep `run_simulation` signature)
- Modify: `packages/simulation/simulation/__init__.py`
- Test: `packages/simulation/tests/test_engine.py`, `packages/simulation/tests/test_run_simulation.py`

- [ ] **Step 1: Write the failing engine test (deterministic sanity)**

```python
# packages/simulation/tests/test_engine.py
import numpy as np
import pytest

from simulation.engine import simulate_monthly
from simulation.preprocess import ProcessedPlan


def _flat_processed(
    months: int,
    *,
    starting_balance: float,
    essential_real: np.ndarray | None = None,
) -> ProcessedPlan:
    zeros = np.zeros(months, dtype=np.float64)
    return ProcessedPlan(
        months=months,
        starting_balance=starting_balance,
        income_real=zeros.copy(),
        essential_real=zeros.copy() if essential_real is None else essential_real,
        discretionary_real=zeros.copy(),
        rra=np.full(months, 4.0),
        stock_allocation_total_portfolio=np.full(months, 0.5),
        legacy_stock_allocation=0.5,
        spending_tilt=zeros.copy(),
        npv_income_without_current=zeros.copy(),
        npv_essential_without_current=zeros.copy(),
        npv_discretionary_without_current=zeros.copy(),
        legacy_npv=zeros.copy(),
        cumulative_1_plus_g_over_1_plus_r=np.arange(months, 0, -1, dtype=np.float64),
        monthly_planning_stocks=0.0,
        monthly_planning_bonds=0.0,
    )


def test_zero_return_zero_income_spends_down_general_pool():
    months = 3
    starting_balance = 300.0
    processed = _flat_processed(months, starting_balance=starting_balance)
    # cumulative = [3, 2, 1]; with zero returns the general pool amortizes evenly.
    returns_stocks = np.zeros((1, months), dtype=np.float64)
    returns_bonds = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(
        processed, stocks_return=returns_stocks, bonds_return=returns_bonds
    )

    expected_monthly_withdrawal = starting_balance / months
    assert result.withdrawals_general[0, 0] == pytest.approx(expected_monthly_withdrawal)
    assert result.withdrawals_general[0, 1] == pytest.approx(expected_monthly_withdrawal)
    assert result.withdrawals_general[0, 2] == pytest.approx(expected_monthly_withdrawal)
    assert result.balance_start[0, 0] == pytest.approx(starting_balance)


def test_money_is_conserved_with_zero_returns():
    months = 4
    starting_balance = 1000.0
    processed = _flat_processed(months, starting_balance=starting_balance)
    z = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(processed, stocks_return=z, bonds_return=z.copy())

    # With zero income and zero returns, total withdrawals cannot exceed starting balance.
    assert result.withdrawals_total.sum() <= starting_balance + 1e-6


def test_current_month_essential_is_reserved_before_general_pool():
    # Regression guard: the wealth-based pool carve must reserve the *current*
    # month's essential expense (npv_essential_without_current + current), not
    # just the future NPV. Otherwise the general pool — and therefore the first
    # general withdrawal target — is overstated. With a single future-free
    # essential expense at month 0 and zero returns, the general pool is
    # (balance - essential) and month 0 amortizes it over `cumulative[0]`.
    months = 2
    starting_balance = 1000.0
    current_essential = 200.0
    essential_real = np.array([current_essential, 0.0], dtype=np.float64)
    processed = _flat_processed(
        months, starting_balance=starting_balance, essential_real=essential_real
    )
    # cumulative = [2, 1]; no future essential NPV, zero income, zero returns.
    z = np.zeros((1, months), dtype=np.float64)

    result = simulate_monthly(processed, stocks_return=z, bonds_return=z.copy())

    cumulative_month_0 = processed.cumulative_1_plus_g_over_1_plus_r[0]
    expected_general_month_0 = (starting_balance - current_essential) / cumulative_month_0
    assert result.withdrawals_essential[0, 0] == pytest.approx(current_essential)
    assert result.withdrawals_general[0, 0] == pytest.approx(expected_general_month_0)
    # Nothing is left unaccounted: essential + both general draws == starting balance.
    assert result.withdrawals_total.sum() == pytest.approx(starting_balance)
```

- [ ] **Step 2: Add minimal scaffolding, then run to confirm a logical failure**

```python
# packages/simulation/simulation/engine.py
from __future__ import annotations

from datetime import datetime

import numpy as np

from simulation.preprocess import ProcessedPlan
from simulation.result import SimulationResult


def simulate_monthly(
    processed: ProcessedPlan,
    *,
    stocks_return: np.ndarray,
    bonds_return: np.ndarray,
    ran_at: datetime | None = None,
) -> SimulationResult:
    raise NotImplementedError
```

Run: `uv run pytest packages/simulation/tests/test_engine.py -v`
Expected: FAIL — `NotImplementedError` (logical). If it instead fails with `ImportError`/`AttributeError`, the scaffolding above is incomplete — fix it before moving on.

- [ ] **Step 3: Implement `engine.py`**

```python
from __future__ import annotations

from datetime import datetime

import numpy as np

from simulation.preprocess import ProcessedPlan
from simulation.result import SimulationResult

_SAVINGS_FLOOR = 1e-5  # tpaw _get_stock_allocation limit as savings balance → 0


def _carve_pools(
    *,
    wealth,
    essential_reserve,
    discretionary_reserve,
    legacy_reserve,
):
    """`AccountForWithdrawal` carve: draw each reserve clamped to the running
    balance (essential → discretionary → legacy), returning the constrained
    (discretionary, legacy, general) pools. Works elementwise on floats or arrays.
    Mirrors tpaw's `_NPVSpendingScaledAndConstrainedToWealth` construction.
    """
    remaining = np.maximum(0.0, wealth - np.minimum(wealth, essential_reserve))
    discretionary = np.minimum(remaining, discretionary_reserve)
    remaining = np.maximum(0.0, remaining - discretionary)
    legacy = np.minimum(remaining, legacy_reserve)
    general = np.maximum(0.0, remaining - legacy)
    return discretionary, legacy, general


def _stock_fraction(
    processed: ProcessedPlan,
    month: int,
    *,
    balance_after_withdrawals,
    scale_discretionary,
    scale_legacy,
):
    """tpaw `_get_stock_allocation`: a *separate* pool carve on the post-withdrawal
    savings balance plus future income NPV — using the without-current-month NPVs,
    since this month's expenses were already withdrawn. Returns the saturated
    savings-portfolio stock fraction.
    """
    savings_balance = np.maximum(balance_after_withdrawals, _SAVINGS_FLOOR)
    base = savings_balance + processed.npv_income_without_current[month]
    discretionary, legacy, general = _carve_pools(
        wealth=base,
        essential_reserve=processed.npv_essential_without_current[month],
        discretionary_reserve=(
            processed.npv_discretionary_without_current[month] * scale_discretionary
        ),
        legacy_reserve=processed.legacy_npv[month] * scale_legacy,
    )
    alloc = processed.stock_allocation_total_portfolio[month]
    legacy_alloc = processed.legacy_stock_allocation
    stocks_target = legacy * legacy_alloc + (discretionary + general) * alloc
    return np.clip(stocks_target / savings_balance, 0.0, 1.0)


def _general_target(processed: ProcessedPlan, month: int, general_pool):
    cumulative = processed.cumulative_1_plus_g_over_1_plus_r[month]
    if cumulative == 0.0:
        return general_pool * 0.0  # preserves scalar/array shape
    return general_pool / cumulative


def _expected_run(
    processed: ProcessedPlan,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic planning-return pass (tpaw's `is_expected_run` branch, scale=1).

    Establishes, per month, the *scheduled* wealth and the elasticities of the
    discretionary/legacy goals w.r.t. wealth. Advances the balance with the same
    withdrawal + allocation steps as a normal run, using the scalar planning
    (expected) monthly returns — so scheduled wealth is consistent with a normal
    run whose realized returns equal the planning returns.
    """
    months = processed.months
    scheduled_wealth = np.zeros(months, dtype=np.float64)
    elasticity_discretionary = np.zeros(months, dtype=np.float64)
    elasticity_legacy = np.zeros(months, dtype=np.float64)

    stock_return = processed.monthly_planning_stocks
    bond_return = processed.monthly_planning_bonds

    balance = processed.starting_balance
    for month in range(months):
        income = processed.income_real[month]
        current_essential = processed.essential_real[month]
        current_discretionary = processed.discretionary_real[month]
        wealth = balance + processed.npv_income_without_current[month] + income
        scheduled_wealth[month] = wealth

        # Wealth-based pools (current month included), scale = 1 on the expected run.
        discretionary_pool, legacy_pool, general_pool = _carve_pools(
            wealth=wealth,
            essential_reserve=(
                processed.npv_essential_without_current[month] + current_essential
            ),
            discretionary_reserve=(
                processed.npv_discretionary_without_current[month]
                + current_discretionary
            ),
            legacy_reserve=processed.legacy_npv[month],
        )

        alloc = processed.stock_allocation_total_portfolio[month]
        legacy_alloc = processed.legacy_stock_allocation
        if wealth == 0.0:
            elasticity_wealth = (2.0 * alloc + legacy_alloc) / 3.0
        else:
            stocks = (
                (discretionary_pool + general_pool) * alloc
                + legacy_pool * legacy_alloc
            )
            elasticity_wealth = stocks / wealth
        if elasticity_wealth != 0.0:
            elasticity_discretionary[month] = alloc / elasticity_wealth
            elasticity_legacy[month] = legacy_alloc / elasticity_wealth

        # Target withdrawals then advance the balance at planning returns.
        target_general = _general_target(processed, month, general_pool)
        avail = balance + income
        avail -= min(avail, current_essential)
        avail -= min(avail, current_discretionary)
        avail -= min(avail, target_general)

        stock_fraction = float(
            _stock_fraction(
                processed,
                month,
                balance_after_withdrawals=avail,
                scale_discretionary=1.0,
                scale_legacy=1.0,
            )
        )
        balance = avail * (
            stock_fraction * (1.0 + stock_return)
            + (1.0 - stock_fraction) * (1.0 + bond_return)
        )

    return scheduled_wealth, elasticity_discretionary, elasticity_legacy


def simulate_monthly(
    processed: ProcessedPlan,
    *,
    stocks_return: np.ndarray,
    bonds_return: np.ndarray,
    ran_at: datetime | None = None,
) -> SimulationResult:
    ran_at = ran_at or datetime.now()
    num_runs, months = stocks_return.shape

    scheduled_wealth, elast_disc, elast_legacy = _expected_run(processed)

    balance = np.full(num_runs, processed.starting_balance, dtype=np.float64)
    insufficient = np.zeros(num_runs, dtype=bool)

    balance_start = np.empty((num_runs, months), dtype=np.float64)
    w_essential = np.empty((num_runs, months), dtype=np.float64)
    w_discretionary = np.empty((num_runs, months), dtype=np.float64)
    w_general = np.empty((num_runs, months), dtype=np.float64)
    w_total = np.empty((num_runs, months), dtype=np.float64)
    savings_alloc = np.empty((num_runs, months), dtype=np.float64)

    for month in range(months):
        balance_start[:, month] = balance
        income = processed.income_real[month]
        current_essential = processed.essential_real[month]
        current_discretionary = processed.discretionary_real[month]
        wealth = balance + processed.npv_income_without_current[month] + income

        # Elasticity scaling of discretionary/legacy goals vs. the scheduled run.
        if scheduled_wealth[month] == 0.0:
            p_increase = np.zeros(num_runs, dtype=np.float64)
        else:
            p_increase = wealth / scheduled_wealth[month] - 1.0
        scale_disc = np.maximum(0.0, p_increase * elast_disc[month] + 1.0)
        scale_legacy = np.maximum(0.0, p_increase * elast_legacy[month] + 1.0)

        # Wealth-based pools (current month included) → general pool to amortize.
        _, _, general_pool = _carve_pools(
            wealth=wealth,
            essential_reserve=(
                processed.npv_essential_without_current[month] + current_essential
            ),
            discretionary_reserve=(
                processed.npv_discretionary_without_current[month]
                + current_discretionary
            )
            * scale_disc,
            legacy_reserve=processed.legacy_npv[month] * scale_legacy,
        )

        target_essential = current_essential
        target_discretionary = current_discretionary * scale_disc
        target_general = _general_target(processed, month, general_pool)

        # Contributions + withdrawals (each draw clamped to the running balance).
        avail = balance + income
        drawn_essential = np.minimum(avail, target_essential)
        avail = avail - drawn_essential
        drawn_discretionary = np.minimum(avail, target_discretionary)
        avail = avail - drawn_discretionary
        drawn_general = np.minimum(avail, target_general)
        avail = avail - drawn_general

        requested = target_essential + target_discretionary + target_general
        insufficient |= requested > (balance + income)

        # Stock fraction from tpaw's separate savings-based carve, then rebalance.
        stock_fraction = _stock_fraction(
            processed,
            month,
            balance_after_withdrawals=avail,
            scale_discretionary=scale_disc,
            scale_legacy=scale_legacy,
        )
        stocks_amount = avail * stock_fraction
        bonds_amount = avail - stocks_amount
        balance = stocks_amount * (1.0 + stocks_return[:, month]) + bonds_amount * (
            1.0 + bonds_return[:, month]
        )

        w_essential[:, month] = drawn_essential
        w_discretionary[:, month] = drawn_discretionary
        w_general[:, month] = drawn_general
        w_total[:, month] = drawn_essential + drawn_discretionary + drawn_general
        savings_alloc[:, month] = stock_fraction

    return SimulationResult(
        ran_at=ran_at,
        horizon_months=months,
        num_runs=num_runs,
        balance_start=balance_start,
        withdrawals_essential=w_essential,
        withdrawals_discretionary=w_discretionary,
        withdrawals_general=w_general,
        withdrawals_total=w_total,
        savings_stock_allocation=savings_alloc,
        num_runs_insufficient=int(insufficient.sum()),
    )
```

> **Two distinct pool carves (matching tpaw).** The *wealth-based* carve
> (`_get_precomputation_at_start`) includes the **current month's** essential and
> discretionary expenses and yields the `general_pool` that is amortized by
> `cumulative_1_plus_g_over_1_plus_r`; on the expected run it also feeds the
> elasticities. The *savings-based* carve (`_get_stock_allocation`) runs on the
> post-withdrawal balance plus future-income NPV and uses the **without-current-month**
> NPVs (this month's expenses are already withdrawn) to derive the stock fraction.
> Keeping these separate — rather than reusing one pool set — is required for parity.
>
> **Expected run uses planning returns.** `_expected_run` advances the deterministic
> balance with the scalar `monthly_planning_stocks`/`monthly_planning_bonds` and the
> same withdrawal/allocation steps as a normal run, so `scheduled_wealth` equals the
> trajectory of a normal run whose realized returns equal the planning returns
> (`p_increase == 0`). If the money-conservation or even-amortization engine tests
> fail, debug against tpaw `_single_month` step-by-step before touching expectations.

- [ ] **Step 4: Run the engine test**

Run: `uv run pytest packages/simulation/tests/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Write the `run_simulation` integration test**

```python
# packages/simulation/tests/test_run_simulation.py
from datetime import date, datetime

from simulation import run_simulation
from simulation.result import ENGINE_VERSION


def test_run_simulation_returns_per_run_arrays(make_plan):
    plan = make_plan()

    result = run_simulation(
        plan,
        percentiles=[10, 50, 90],
        today=date(2026, 1, 1),
        ran_at=datetime(2026, 1, 1),
    )

    assert result.engine_version == ENGINE_VERSION
    assert result.num_runs == plan.sampling.num_runs
    assert result.balance_start.shape == (plan.sampling.num_runs, result.horizon_months)
    assert result.withdrawals_total.shape == result.balance_start.shape
```

- [ ] **Step 6: Rewrite `run_simulation` in `stub.py`**

Replace the body of `packages/simulation/simulation/stub.py` (keep file name and the `run_simulation` signature incl. `today`/`ran_at`):

```python
from __future__ import annotations

from datetime import date, datetime

from core.models import Plan

from simulation.bootstrap_inputs import build_return_paths  # see note
from simulation.engine import simulate_monthly
from simulation.preprocess import preprocess
from simulation.result import SimulationResult


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
) -> SimulationResult:
    _ = percentiles  # reserved for Phase 3d aggregation
    today = today or date.today()
    ran_at = ran_at or datetime.now()

    processed = preprocess(plan, today=today)
    paths = build_return_paths(plan, months_per_run=processed.months, today=today)
    return simulate_monthly(
        processed,
        stocks_return=paths.stocks_log_to_simple(),
        bonds_return=paths.bonds_log_to_simple(),
        ran_at=ran_at,
    )
```

> **Returns conversion note:** Phase 3a `build_return_paths` returns `ReturnPaths` with `stocks_log` / `bonds_log` (log returns), shape `(num_runs, months_per_run)`. The engine needs **simple** monthly returns. Add two helpers to `ReturnPaths` in `packages/simulation/simulation/market_data/bootstrap.py`: `stocks_log_to_simple(self) -> np.ndarray: return np.expm1(self.stocks_log)` and the bonds equivalent. Import path in the snippet (`simulation.bootstrap_inputs`) is illustrative — use the real `from simulation.market_data import build_return_paths`. Update the snippet accordingly when implementing.

- [ ] **Step 7: Update `__init__.py` exports**

In `packages/simulation/simulation/__init__.py`, remove `STUB_VERSION` from imports/`__all__`, add `ENGINE_VERSION`, `simulate_monthly`, `preprocess`, and keep `run_simulation`. Grep first:

Run: `rg -n "STUB_VERSION|\.echo\b" packages/`
Fix every hit (notably any web results template/view from Phase 1 that read `.echo`). For the web results partial, replace the echoed values with a minimal summary derived from the new arrays (e.g. median ending balance via `float(np.median(result.balance_start[:, -1]))`) — keep it minimal; full charts are Phase 3d.

- [ ] **Step 8: Run the integration test + the full simulation suite**

Run: `uv run pytest packages/simulation -v`
Expected: PASS (all simulation tests, including market_data).

- [ ] **Step 9: Commit**

```bash
git add packages/simulation/simulation/engine.py packages/simulation/simulation/stub.py packages/simulation/simulation/__init__.py packages/simulation/simulation/market_data/bootstrap.py packages/simulation/tests/test_engine.py packages/simulation/tests/test_run_simulation.py packages/web
git commit -m "feat(simulation): vectorized TPAW forward engine and run_simulation wiring"
```

---

## Task 10: Documentation — README + OVERVIEW

**Files:**
- Create: `packages/simulation/README.md`
- Create: `packages/simulation/OVERVIEW.md`

- [ ] **Step 1: Write `packages/simulation/README.md`**

Human-readable flow. Include: the pipeline diagram from spec §4; an intuition paragraph for each stage (domain cashflows → inflation/real conversion → return paths → risk/RRA → Merton allocation + spending tilt → backward NPV/amortization → forward monthly loop → raw per-run arrays); the meaning of essential/discretionary/general/legacy; and that withdrawal starts at month 0 (retirement is implicit). No code; prose + the one diagram.

- [ ] **Step 2: Write `packages/simulation/OVERVIEW.md`**

Parity backlog: a table of tpaw features and port status (ported in 3b: risk/RRA, Merton, NPV precompute, forward loop, raw results; deferred: percentile aggregation → 3d, planning-return presets/CAPE/EOD → 3c, bootstrapped inflation → #186, ceiling/floor → removed, tax buckets → later). Record the float64-vs-CUDA/float32 parity caveat (spec §8) and the doctest-golden testing approach.

- [ ] **Step 3: Commit**

```bash
git add packages/simulation/README.md packages/simulation/OVERVIEW.md
git commit -m "docs(simulation): add README flow and OVERVIEW parity backlog"
```

---

## Task 11: Rebuild index updates + full verification

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Update the index**

- **Active phase** table: set Current phase to "Phase 3b — execute", Active plan to this file, Next action to "Execute Phase 3b plan".
- **Phase 3b** exit criteria: replace with the spec's criteria — full engine (Merton/RRA/PV/amortized general withdrawal), raw per-run arrays, doctest goldens, spending tilt applied, month-0 withdrawal start.
- **Phase 3c** entry: rewrite title/delivers from "allocation + PV" to **"planning-returns presets"** (live CAPE/EOD expected returns, empirical-variance refinement, stock-allocation glide path); note RRA/Merton/PV/total-portfolio allocation now land in 3b.
- **Completed plans** table: leave 3b for the executor to mark complete on merge.

- [ ] **Step 2: Run the full check**

Run: `make`
Expected: PASS (ruff + pyright + pytest across all packages).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "docs(plan): activate Phase 3b and re-scope Phase 3c to planning-returns presets"
```

---

## Self-Review notes (for the executor)

- If `make_plan` fixtures differ from assumptions, construct `Plan` inline from the same shape used in neighboring tests — do not invent fields.
- The trickiest parity risk is the **expected-run elasticity** pass (Task 9) and the **backward NPV** discounting (Task 8). If the deterministic engine tests fail, debug against tpaw `_single_month` step-by-step before changing test expectations.
- Keep all tpaw doctest literals comment-tagged and never "fix" them to match our output — if they disagree, our implementation is wrong.

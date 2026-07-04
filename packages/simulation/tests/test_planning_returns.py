from decimal import Decimal

import numpy as np
from core.defaults import default_plan
from simulation.market_data import load_historical_returns
from simulation.planning_returns import (
    PlanningReturns,
    annual_stock_log_variance,
    resolve_planning_returns,
)


def _plan_with_returns(stocks: Decimal, bonds: Decimal):
    plan = default_plan()
    plan.planning_returns.expected_annual_return_stocks = stocks
    plan.planning_returns.expected_annual_return_bonds = bonds
    return plan


def test_resolves_expected_returns_from_plan():
    expected_annual_stocks = 0.06
    expected_annual_bonds = 0.025
    plan = _plan_with_returns(
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

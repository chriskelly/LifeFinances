from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.models import DEFAULT_BLOCK_SIZE_MONTHS
from simulation.market_data import load_historical_returns
from simulation.planning_returns import resolve_planning_returns
from simulation.presets import (
    historical_annual_return,
    historical_bond_return,
    round3,
    stock_estimates,
    stock_log_variance,
)

from .tpaw_preset_contract import SP500_CLOSE, TIPS_20YR

TODAY = date(2026, 6, 1)
ROUNDED_TIPS_20YR = round3(TIPS_20YR)


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
    assert result.annual_bonds == ROUNDED_TIPS_20YR
    assert sp_calls["count"] == 1
    assert tr_calls["count"] == 1


def test_conservative_estimate_preset_calls_resolvers_and_uses_preset_math():
    plan = default_plan()
    plan.planning_returns.preset = "conservative_estimate"
    expected_stocks = stock_estimates(sp500_close=SP500_CLOSE).conservative_estimate
    sp_resolver, sp_calls = _spy_resolver(_SP500(SP500_CLOSE))
    tr_resolver, tr_calls = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks
    assert result.annual_bonds == ROUNDED_TIPS_20YR
    assert sp_calls["count"] == 1
    assert tr_calls["count"] == 1


def test_one_over_cape_preset_calls_resolvers_and_uses_preset_math():
    plan = default_plan()
    plan.planning_returns.preset = "one_over_cape"
    expected_stocks = stock_estimates(sp500_close=SP500_CLOSE).one_over_cape
    sp_resolver, sp_calls = _spy_resolver(_SP500(SP500_CLOSE))
    tr_resolver, tr_calls = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan, today=TODAY, sp500_resolver=sp_resolver, treasury_resolver=tr_resolver
    )

    assert result.annual_stocks == expected_stocks
    assert result.annual_bonds == ROUNDED_TIPS_20YR
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

    assert result.annual_bonds == ROUNDED_TIPS_20YR
    assert result.annual_stocks == ROUNDED_TIPS_20YR + float(premium)
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
    assert result.annual_bonds == ROUNDED_TIPS_20YR + float(bonds_delta)


def test_non_fixed_preset_ignores_invalid_fixed_literals():
    invalid_bond_return = Decimal("-1.5")
    plan = default_plan()
    plan.planning_returns.preset = "regression_prediction"
    plan.planning_returns.expected_annual_return_bonds = invalid_bond_return
    sp_resolver, _ = _spy_resolver(_SP500(SP500_CLOSE))
    tr_resolver, _ = _spy_resolver(_Treasury(TIPS_20YR))

    result = resolve_planning_returns(
        plan,
        today=TODAY,
        sp500_resolver=sp_resolver,
        treasury_resolver=tr_resolver,
    )

    assert result.annual_bonds == ROUNDED_TIPS_20YR


def test_tips_20yr_is_rounded_to_three_decimals():
    unrounded_yield = 0.02637
    expected_bonds = round3(unrounded_yield)
    plan = default_plan()
    plan.planning_returns.preset = "regression_prediction"
    tr_resolver, tr_calls = _spy_resolver(_Treasury(unrounded_yield))

    result = resolve_planning_returns(
        plan,
        today=TODAY,
        sp500_resolver=_spy_resolver(_SP500(SP500_CLOSE))[0],
        treasury_resolver=tr_resolver,
    )

    assert result.annual_bonds == expected_bonds
    assert tr_calls["count"] == 1


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

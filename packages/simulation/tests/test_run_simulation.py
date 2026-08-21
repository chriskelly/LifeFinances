from datetime import date, datetime
from decimal import Decimal

from core.defaults import default_plan
from core.models import (
    DEFAULT_PERCENTILES,
    AdvancedConfig,
    InflationConfig,
    PlanningReturnsConfig,
)
from core.timeline import Timeline
from simulation.presets import stock_log_variance
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
    assert result.percentiles == DEFAULT_PERCENTILES


def test_run_simulation_resolved_assumptions_match_fixed_preset() -> None:
    annual_inflation = 0.023
    annual_stocks = 0.051
    annual_bonds = 0.018
    plan = default_plan().model_copy(
        update={
            "inflation": InflationConfig(
                mode="manual", manual_annual_rate=Decimal(str(annual_inflation))
            ),
            "planning_returns": PlanningReturnsConfig(
                preset="fixed",
                expected_annual_return_stocks=Decimal(str(annual_stocks)),
                expected_annual_return_bonds=Decimal(str(annual_bonds)),
            ),
        }
    )
    expected_variance = stock_log_variance(
        block_size_months=plan.sampling.block_size_months,
        volatility_scale=float(plan.planning_returns.stock_volatility_scale),
    )

    result = run_simulation(
        plan,
        today=date(2026, 1, 1),
        ran_at=datetime(2026, 1, 1),
    )

    assumptions = result.resolved_assumptions
    assert assumptions.annual_inflation == annual_inflation
    assert assumptions.annual_stock_return == annual_stocks
    assert assumptions.annual_bond_return == annual_bonds
    assert assumptions.annual_stock_log_variance == expected_variance
    assert assumptions.planning_preset == "fixed"
    assert assumptions.inflation_source == "manual"
    assert assumptions.inflation_observation_date is None
    assert assumptions.sp500_source is None
    assert assumptions.treasury_source is None

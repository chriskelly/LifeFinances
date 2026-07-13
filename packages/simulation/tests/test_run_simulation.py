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
    assert result.percentiles == DEFAULT_PERCENTILES

from datetime import date, datetime

from core.defaults import default_plan
from simulation.result import ENGINE_VERSION

from simulation import run_simulation


def test_run_simulation_returns_per_run_arrays():
    plan = default_plan()

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

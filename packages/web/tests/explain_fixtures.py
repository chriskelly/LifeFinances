from datetime import datetime

import numpy as np
from core.defaults import default_plan
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult
from web.explain import ScopedResult


def scoped_result(
    result: SimulationResult, *, plan_id: int = 1, plan_name: str = "Plan"
) -> ScopedResult:
    plan = default_plan().model_copy(update={"name": plan_name})
    return ScopedResult(plan_id=plan_id, plan=plan, result=result)


def sample_simulation_result() -> SimulationResult:
    percentiles = [10, 50, 90]
    months = 4
    percentile_values = np.arange(
        1.0, 1.0 + len(percentiles) * months, dtype=np.float64
    ).reshape(len(percentiles), months)
    horizon_values = np.arange(101.0, 101.0 + months, dtype=np.float64)
    scheduled_wealth = np.arange(201.0, 201.0 + months, dtype=np.float64)
    diagnostics = empty_diagnostics(months=months).model_copy(
        update={
            "scheduled_wealth": scheduled_wealth,
            "legacy_stock_allocation": 0.37,
        }
    )
    return SimulationResult(
        ran_at=datetime(2026, 9, 23, 8, 30),
        horizon_months=months,
        num_runs=250,
        percentiles=percentiles,
        start_month=(2026, 9),
        balance_start=percentile_values.copy(),
        withdrawals_essential=percentile_values.copy(),
        withdrawals_discretionary=percentile_values.copy(),
        withdrawals_general=percentile_values.copy(),
        withdrawals_total=percentile_values.copy(),
        savings_stock_allocation=percentile_values.copy(),
        wealth_job=horizon_values,
        wealth_social_security=horizon_values + 10.0,
        wealth_pension=horizon_values + 20.0,
        wealth_manual=horizon_values + 30.0,
        num_runs_insufficient=7,
        diagnostics=diagnostics,
        resolved_assumptions=ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.03,
            annual_stock_log_variance=0.04,
            planning_preset="fixed",
            inflation_source="manual",
        ),
    )

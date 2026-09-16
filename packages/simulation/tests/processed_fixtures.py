import numpy as np
from simulation.market_data.inflation import InflationResolved, annual_to_monthly
from simulation.planning_returns import PlanningReturns
from simulation.preprocess import ProcessedPlan


def _resolver_fixtures() -> tuple[InflationResolved, PlanningReturns]:
    annual_inflation = 0.02
    return (
        InflationResolved(
            annual=annual_inflation,
            monthly=annual_to_monthly(annual_inflation),
            source="manual",
        ),
        PlanningReturns(
            annual_stocks=0.05,
            annual_bonds=0.02,
            annual_stock_log_variance=0.03,
        ),
    )


def _flat_processed(
    months: int,
    *,
    starting_balance: float,
    essential_real: np.ndarray | None = None,
) -> ProcessedPlan:
    zeros = np.zeros(months, dtype=np.float64)
    inflation_resolved, planning_resolved = _resolver_fixtures()
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
        monthly_inflation=0.0,
        gross_job=zeros.copy(),
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        manual_gross_real=zeros.copy(),
        taxes=zeros.copy(),
        inflation_resolved=inflation_resolved,
        planning_resolved=planning_resolved,
    )

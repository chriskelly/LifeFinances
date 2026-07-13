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

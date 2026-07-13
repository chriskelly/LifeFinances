from __future__ import annotations

import numpy as np

from simulation.composition import WealthBySource
from simulation.result import RAW_ARRAY_FIELDS, RawSimulationResult, SimulationResult


def _percentile_arrays(
    raw: RawSimulationResult, *, percentiles: list[int]
) -> dict[str, np.ndarray]:
    return {
        name: np.percentile(getattr(raw, name), percentiles, axis=0)
        for name in RAW_ARRAY_FIELDS
    }


def build_public_result(
    raw: RawSimulationResult,
    *,
    percentiles: list[int],
    composition: WealthBySource,
    start_month: tuple[int, int],
) -> SimulationResult:
    reduced = _percentile_arrays(raw, percentiles=percentiles)
    return SimulationResult(
        ran_at=raw.ran_at,
        horizon_months=raw.horizon_months,
        num_runs=raw.num_runs,
        percentiles=list(percentiles),
        start_month=start_month,
        balance_start=reduced["balance_start"],
        withdrawals_essential=reduced["withdrawals_essential"],
        withdrawals_discretionary=reduced["withdrawals_discretionary"],
        withdrawals_general=reduced["withdrawals_general"],
        withdrawals_total=reduced["withdrawals_total"],
        savings_stock_allocation=reduced["savings_stock_allocation"],
        wealth_job=composition.job,
        wealth_social_security=composition.social_security,
        wealth_pension=composition.pension,
        wealth_manual=composition.manual,
        num_runs_insufficient=raw.num_runs_insufficient,
    )

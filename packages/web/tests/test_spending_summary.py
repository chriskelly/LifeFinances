from __future__ import annotations

from datetime import datetime

import numpy as np
from core.models import DEFAULT_PERCENTILES
from simulation.result import ResolvedAssumptions, SimulationResult

from web import spending_summary as spending


def _resolved_assumptions() -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.02,
        annual_stock_return=0.05,
        annual_bond_return=0.02,
        annual_stock_log_variance=0.03,
        planning_preset="fixed",
        inflation_source="manual",
    )


def _result_with_withdrawals(
    withdrawals: np.ndarray, *, percentiles: list[int] | None = None
) -> SimulationResult:
    horizon = withdrawals.shape[1]
    zeros = np.zeros_like(withdrawals)
    months = np.zeros(horizon, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon,
        num_runs=10,
        percentiles=percentiles or list(DEFAULT_PERCENTILES),
        start_month=(2026, 1),
        balance_start=zeros.copy(),
        withdrawals_essential=zeros.copy(),
        withdrawals_discretionary=zeros.copy(),
        withdrawals_general=zeros.copy(),
        withdrawals_total=withdrawals,
        savings_stock_allocation=zeros.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
        resolved_assumptions=_resolved_assumptions(),
    )


def test_initial_spending_is_month_zero_of_total_withdrawals() -> None:
    initial = 4_200.0
    withdrawals = np.array(
        [
            [initial, 3_000.0, 2_500.0],
            [initial, 4_000.0, 3_500.0],
            [initial, 5_000.0, 4_500.0],
        ],
        dtype=np.float64,
    )

    summary = spending.from_result(_result_with_withdrawals(withdrawals))

    assert summary.initial == initial


def test_worst_case_tracks_the_lowest_percentile_row_not_the_global_minimum() -> None:
    lowest_percentile_low = 2_000.0
    global_minimum = 900.0
    # Row order follows the ascending percentile list, so row 0 is the lowest
    # percentile. The global minimum sits in a higher percentile row here so a
    # summary that just takes `min()` over the whole array would be caught.
    withdrawals = np.array(
        [
            [4_000.0, lowest_percentile_low, 2_200.0],
            [4_000.0, global_minimum, 3_000.0],
            [4_000.0, 5_000.0, 4_500.0],
        ],
        dtype=np.float64,
    )

    summary = spending.from_result(_result_with_withdrawals(withdrawals))

    assert summary.worst_case == lowest_percentile_low
    assert global_minimum < lowest_percentile_low


def test_worst_case_follows_the_configured_lowest_percentile() -> None:
    lowest_row_low = 3_100.0
    withdrawals = np.array(
        [[5_000.0, lowest_row_low], [5_000.0, 4_800.0]], dtype=np.float64
    )
    percentiles = [50, 95]

    summary = spending.from_result(
        _result_with_withdrawals(withdrawals, percentiles=percentiles)
    )

    assert summary.worst_case == lowest_row_low

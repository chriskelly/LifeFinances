from __future__ import annotations

from datetime import datetime

import numpy as np
from simulation.result import SimulationResult

from web import spending_summary as spending


def _result_with_withdrawals(withdrawals: np.ndarray) -> SimulationResult:
    percentiles = [5, 50, 95]
    horizon = withdrawals.shape[1]
    zeros = np.zeros_like(withdrawals)
    months = np.zeros(horizon, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon,
        num_runs=10,
        percentiles=percentiles,
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


def test_worst_case_spending_is_min_along_lowest_percentile_path() -> None:
    worst = 1_800.0
    withdrawals = np.array(
        [
            [4_000.0, worst, 2_200.0],
            [4_000.0, 3_500.0, 3_000.0],
            [4_000.0, 5_000.0, 4_500.0],
        ],
        dtype=np.float64,
    )

    summary = spending.from_result(_result_with_withdrawals(withdrawals))

    assert summary.worst_case == worst

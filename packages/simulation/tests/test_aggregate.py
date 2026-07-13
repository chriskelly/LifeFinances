from datetime import datetime

import numpy as np
from simulation.aggregate import build_public_result
from simulation.composition import WealthBySource
from simulation.result import RawSimulationResult


def _raw(*, balance_start: np.ndarray) -> RawSimulationResult:
    num_runs, months = balance_start.shape
    zeros = np.zeros((num_runs, months), dtype=np.float64)
    return RawSimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=balance_start,
        withdrawals_essential=zeros,
        withdrawals_discretionary=zeros,
        withdrawals_general=zeros,
        withdrawals_total=balance_start
        * 0.1,  # distinct from balance for mapping check
        savings_stock_allocation=zeros,
        num_runs_insufficient=0,
    )


def test_build_public_result_reduces_each_array_field_along_runs():
    # Column 0 values [1, 2, 3]; column 1 [10, 20, 30]
    balance_start = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0]], dtype=np.float64)
    percentiles = [0, 50, 100]
    raw = _raw(balance_start=balance_start)
    months = raw.horizon_months
    composition = WealthBySource(
        job=np.zeros(months, dtype=np.float64),
        social_security=np.zeros(months, dtype=np.float64),
        pension=np.zeros(months, dtype=np.float64),
        manual=np.zeros(months, dtype=np.float64),
    )

    result = build_public_result(
        raw,
        percentiles=percentiles,
        composition=composition,
        start_month=(2026, 1),
    )

    assert result.balance_start.shape == (len(percentiles), raw.horizon_months)
    np.testing.assert_allclose(
        result.balance_start,
        np.percentile(raw.balance_start, percentiles, axis=0),
    )
    np.testing.assert_allclose(
        result.withdrawals_total,
        np.percentile(raw.withdrawals_total, percentiles, axis=0),
    )
    assert result.percentiles == percentiles
    assert result.num_runs == raw.num_runs
    assert result.start_month == (2026, 1)

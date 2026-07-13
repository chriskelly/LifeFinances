from datetime import datetime

import numpy as np
from simulation.result import RawSimulationResult, SimulationResult


def test_raw_simulation_result_holds_per_run_arrays():
    num_runs, months = 3, 4
    expected_insufficient = 0
    zeros = np.zeros((num_runs, months), dtype=np.float64)

    result = RawSimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=zeros,
        withdrawals_essential=zeros,
        withdrawals_discretionary=zeros,
        withdrawals_general=zeros,
        withdrawals_total=zeros,
        savings_stock_allocation=zeros,
        num_runs_insufficient=expected_insufficient,
    )

    assert result.balance_start.shape == (num_runs, months)
    assert result.num_runs_insufficient == expected_insufficient


def _make_result(*, balance_start: np.ndarray, num_runs_insufficient: int = 0):
    num_runs, months = balance_start.shape
    other_zeros = np.zeros((num_runs, months), dtype=np.float64)
    return RawSimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        balance_start=balance_start,
        withdrawals_essential=other_zeros,
        withdrawals_discretionary=other_zeros,
        withdrawals_general=other_zeros,
        withdrawals_total=other_zeros,
        savings_stock_allocation=other_zeros,
        num_runs_insufficient=num_runs_insufficient,
    )


def test_equal_results_with_matching_arrays_and_scalars_compare_equal():
    balance_start = np.array([[1.0, 2.0], [3.0, 4.0]])

    first = _make_result(balance_start=balance_start)
    second = _make_result(balance_start=balance_start.copy())

    assert first == second


def test_results_with_differing_arrays_compare_unequal():
    first = _make_result(balance_start=np.array([[1.0, 2.0], [3.0, 4.0]]))
    second = _make_result(balance_start=np.array([[1.0, 2.0], [3.0, 5.0]]))

    assert first != second


def test_results_with_differing_scalars_compare_unequal():
    balance_start = np.array([[1.0, 2.0], [3.0, 4.0]])

    first = _make_result(balance_start=balance_start, num_runs_insufficient=0)
    second = _make_result(balance_start=balance_start, num_runs_insufficient=1)

    assert first != second


def _make_public_result(*, balance_start: np.ndarray) -> SimulationResult:
    percentiles = [5, 50, 95]
    num_runs, months = balance_start.shape
    wealth = np.zeros(months, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=months,
        num_runs=num_runs,
        percentiles=percentiles,
        start_month=(2026, 1),
        balance_start=balance_start,
        withdrawals_essential=np.zeros((len(percentiles), months), dtype=np.float64),
        withdrawals_discretionary=np.zeros(
            (len(percentiles), months), dtype=np.float64
        ),
        withdrawals_general=np.zeros((len(percentiles), months), dtype=np.float64),
        withdrawals_total=np.zeros((len(percentiles), months), dtype=np.float64),
        savings_stock_allocation=np.zeros((len(percentiles), months), dtype=np.float64),
        wealth_job=wealth,
        wealth_social_security=wealth.copy(),
        wealth_pension=wealth.copy(),
        wealth_manual=wealth.copy(),
        num_runs_insufficient=0,
    )


def test_public_simulation_result_equality_compares_ndarray_fields():
    balance_start = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float64)

    first = _make_public_result(balance_start=balance_start)
    second = _make_public_result(balance_start=balance_start.copy())

    assert first == second


def test_public_simulation_result_inequality_on_differing_wealth_band():
    balance_start = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float64)
    first = _make_public_result(balance_start=balance_start)
    second = first.model_copy(update={"wealth_job": first.wealth_job + 1.0})

    assert first != second

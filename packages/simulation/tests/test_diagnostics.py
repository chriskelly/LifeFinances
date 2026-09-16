import math
from dataclasses import replace

import numpy as np
from simulation.diagnostics import (
    RRA_INFINITE_SENTINEL,
    empty_diagnostics,
    rra_for_diagnostics,
)
from simulation.engine import _savings_carve, _stock_fraction, simulate_monthly

from .processed_fixtures import _flat_processed


def test_rra_for_diagnostics_replaces_infinity_with_sentinel() -> None:
    finite = 4.0
    engine_rra = np.array([math.inf, finite], dtype=np.float64)

    displayed = rra_for_diagnostics(engine_rra)

    np.testing.assert_array_equal(
        displayed, np.array([RRA_INFINITE_SENTINEL, finite], dtype=np.float64)
    )
    assert math.isinf(engine_rra[0])


def test_empty_diagnostics_series_match_requested_horizon() -> None:
    months = 3

    diagnostics = empty_diagnostics(months=months)

    assert diagnostics.rra_by_month.shape == (months,)
    assert diagnostics.expected_savings_stock_fraction.shape == (months,)
    assert diagnostics.legacy_stock_allocation == 0.0


def test_savings_carve_fraction_matches_clipped_target_over_balance() -> None:
    months = 1
    starting_balance = 100.0
    merton_alloc = 0.4
    legacy_alloc = 0.2
    processed = replace(
        _flat_processed(months, starting_balance=starting_balance),
        stock_allocation_total_portfolio=np.full(months, merton_alloc),
        legacy_stock_allocation=legacy_alloc,
        npv_income_without_current=np.array([50.0]),
        npv_essential_without_current=np.array([10.0]),
        npv_discretionary_without_current=np.array([20.0]),
        legacy_npv=np.array([30.0]),
    )
    balance_after_withdrawals = 80.0

    carve = _savings_carve(
        processed=processed,
        month=0,
        balance_after_withdrawals=balance_after_withdrawals,
        scale_discretionary=1.0,
        scale_legacy=1.0,
    )

    expected_fraction = float(
        np.clip(carve.stocks_target / carve.savings_balance, 0.0, 1.0)
    )
    assert carve.stock_fraction == expected_fraction
    assert carve.wealth_base == carve.savings_balance + carve.income_npv


def test_savings_carve_preserves_run_axis_for_array_inputs() -> None:
    months = 1
    num_runs = 3
    merton_alloc = 0.5
    processed = replace(
        _flat_processed(months, starting_balance=100.0),
        stock_allocation_total_portfolio=np.full(months, merton_alloc),
        legacy_stock_allocation=0.0,
        npv_income_without_current=np.zeros(months),
        npv_essential_without_current=np.zeros(months),
        npv_discretionary_without_current=np.zeros(months),
        legacy_npv=np.zeros(months),
    )
    balance_after_withdrawals = np.array([10.0, 20.0, 30.0], dtype=np.float64)
    scale = np.ones(num_runs, dtype=np.float64)

    carve = _savings_carve(
        processed=processed,
        month=0,
        balance_after_withdrawals=balance_after_withdrawals,
        scale_discretionary=scale,
        scale_legacy=scale,
    )
    fraction = _stock_fraction(
        processed,
        0,
        balance_after_withdrawals=balance_after_withdrawals,
        scale_discretionary=scale,
        scale_legacy=scale,
    )

    assert carve.stock_fraction.shape == (num_runs,)
    np.testing.assert_array_equal(fraction, carve.stock_fraction)


def test_raw_result_diagnostics_match_expected_run_horizon() -> None:
    months = 4
    processed = _flat_processed(months, starting_balance=1_000.0)
    returns = np.zeros((2, months), dtype=np.float64)

    raw = simulate_monthly(processed, stocks_return=returns, bonds_return=returns)

    assert raw.diagnostics.scheduled_wealth.shape == (months,)
    assert raw.diagnostics.expected_savings_stock_fraction.shape == (months,)
    assert raw.diagnostics.essential_reserve.shape == (months,)
    assert raw.diagnostics.discretionary_pool.shape == (months,)


def test_diagnostics_maps_infinite_engine_rra_and_keeps_zero_merton() -> None:
    months = 2
    zero_merton = 0.0
    finite_merton = 0.5
    processed = replace(
        _flat_processed(months, starting_balance=1_000.0),
        rra=np.array([math.inf, 4.0], dtype=np.float64),
        stock_allocation_total_portfolio=np.array(
            [zero_merton, finite_merton], dtype=np.float64
        ),
    )
    returns = np.zeros((1, months), dtype=np.float64)

    raw = simulate_monthly(processed, stocks_return=returns, bonds_return=returns)

    assert raw.diagnostics.rra_by_month[0] == RRA_INFINITE_SENTINEL
    assert raw.diagnostics.stock_allocation_total_portfolio[0] == zero_merton
    assert math.isinf(processed.rra[0])

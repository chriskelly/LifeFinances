import math
from dataclasses import replace

import numpy as np
from simulation.diagnostics import (
    RRA_INFINITE_SENTINEL,
    build_diagnostics,
    empty_diagnostics,
    rra_for_diagnostics,
)
from simulation.engine import (
    _SAVINGS_FLOOR,
    _savings_carve,
    _stock_fraction,
    simulate_monthly,
)
from simulation.npv import carve_pools, target_general_withdrawal

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


def test_savings_carve_matches_independent_pool_and_target_formula() -> None:
    months = 1
    starting_balance = 100.0
    merton_alloc = 0.4
    legacy_alloc = 0.2
    income_npv = 50.0
    essential_reserve = 10.0
    discretionary_npv = 20.0
    legacy_npv = 30.0
    balance_after_withdrawals = 80.0
    scale_discretionary = 1.0
    scale_legacy = 1.0
    processed = replace(
        _flat_processed(months, starting_balance=starting_balance),
        stock_allocation_total_portfolio=np.full(months, merton_alloc),
        legacy_stock_allocation=legacy_alloc,
        npv_income_without_current=np.array([income_npv]),
        npv_essential_without_current=np.array([essential_reserve]),
        npv_discretionary_without_current=np.array([discretionary_npv]),
        legacy_npv=np.array([legacy_npv]),
    )

    carve = _savings_carve(
        processed=processed,
        month=0,
        balance_after_withdrawals=balance_after_withdrawals,
        scale_discretionary=scale_discretionary,
        scale_legacy=scale_legacy,
    )

    expected_savings_balance = max(balance_after_withdrawals, _SAVINGS_FLOOR)
    expected_wealth_base = expected_savings_balance + income_npv
    expected_discretionary_reserve = discretionary_npv * scale_discretionary
    expected_legacy_reserve = legacy_npv * scale_legacy
    expected_disc, expected_leg, expected_gen = carve_pools(
        wealth=expected_wealth_base,
        essential_reserve=essential_reserve,
        discretionary_reserve=expected_discretionary_reserve,
        legacy_reserve=expected_legacy_reserve,
    )
    expected_stocks_target = (
        expected_leg * legacy_alloc + (expected_disc + expected_gen) * merton_alloc
    )
    expected_fraction = float(
        np.clip(expected_stocks_target / expected_savings_balance, 0.0, 1.0)
    )

    assert float(carve.savings_balance) == expected_savings_balance
    assert float(carve.income_npv) == income_npv
    assert float(carve.wealth_base) == expected_wealth_base
    assert float(carve.essential_reserve) == essential_reserve
    assert float(carve.discretionary_reserve) == expected_discretionary_reserve
    assert float(carve.legacy_reserve) == expected_legacy_reserve
    assert float(carve.discretionary_pool) == float(expected_disc)
    assert float(carve.legacy_pool) == float(expected_leg)
    assert float(carve.general_pool) == float(expected_gen)
    assert float(carve.stocks_target) == float(expected_stocks_target)
    assert float(carve.stock_fraction) == expected_fraction


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

    assert np.asarray(carve.stock_fraction).shape == (num_runs,)
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


def test_raw_result_diagnostics_record_expected_run_carve_month0() -> None:
    months = 4
    starting_balance = 1_000.0
    processed = _flat_processed(months, starting_balance=starting_balance)
    returns = np.zeros((1, months), dtype=np.float64)

    raw = simulate_monthly(processed, stocks_return=returns, bonds_return=returns)

    # Reconstruct month-0 post-withdrawal balance from the wealth carve (scale=1).
    income = float(processed.income_real[0])
    wealth = starting_balance + float(processed.npv_income_without_current[0]) + income
    _, _, general_pool = carve_pools(
        wealth=wealth,
        essential_reserve=(
            float(processed.npv_essential_without_current[0])
            + float(processed.essential_real[0])
        ),
        discretionary_reserve=(
            float(processed.npv_discretionary_without_current[0])
            + float(processed.discretionary_real[0])
        ),
        legacy_reserve=float(processed.legacy_npv[0]),
    )
    target_general = float(
        target_general_withdrawal(
            general_pool=general_pool,
            cumulative_1_plus_g_over_1_plus_r=float(
                processed.cumulative_1_plus_g_over_1_plus_r[0]
            ),
        )
    )
    avail = starting_balance + income - target_general
    expected = _savings_carve(
        processed=processed,
        month=0,
        balance_after_withdrawals=avail,
        scale_discretionary=1.0,
        scale_legacy=1.0,
    )

    assert raw.diagnostics.savings_balance[0] == float(expected.savings_balance)
    assert raw.diagnostics.income_npv[0] == float(expected.income_npv)
    assert raw.diagnostics.wealth_base[0] == float(expected.wealth_base)
    assert raw.diagnostics.essential_reserve[0] == float(expected.essential_reserve)
    assert raw.diagnostics.discretionary_pool[0] == float(expected.discretionary_pool)
    assert raw.diagnostics.legacy_pool[0] == float(expected.legacy_pool)
    assert raw.diagnostics.general_pool[0] == float(expected.general_pool)
    assert raw.diagnostics.stocks_target[0] == float(expected.stocks_target)
    assert raw.diagnostics.expected_savings_stock_fraction[0] == float(
        expected.stock_fraction
    )
    assert raw.diagnostics.stock_allocation_total_portfolio[0] == float(
        processed.stock_allocation_total_portfolio[0]
    )
    assert raw.diagnostics.legacy_stock_allocation == processed.legacy_stock_allocation


def test_build_diagnostics_detaches_ndarray_inputs() -> None:
    months = 2
    merton = np.array([0.3, 0.7], dtype=np.float64)
    processed = replace(
        _flat_processed(months, starting_balance=100.0),
        stock_allocation_total_portfolio=merton,
        rra=np.array([4.0, math.inf], dtype=np.float64),
    )
    scheduled_wealth = np.array([10.0, 20.0], dtype=np.float64)
    zeros = np.zeros(months, dtype=np.float64)
    expected_scheduled_month0 = float(scheduled_wealth[0])
    expected_merton_month0 = float(merton[0])

    diagnostics = build_diagnostics(
        processed=processed,
        scheduled_wealth=scheduled_wealth,
        elasticity_discretionary=zeros,
        elasticity_legacy=zeros,
        savings_balance=zeros,
        income_npv=zeros,
        wealth_base=zeros,
        essential_reserve=zeros,
        discretionary_reserve=zeros,
        legacy_reserve=zeros,
        discretionary_pool=zeros,
        legacy_pool=zeros,
        general_pool=zeros,
        stocks_target=zeros,
        expected_savings_stock_fraction=zeros,
    )

    scheduled_wealth[0] = -1.0
    merton[0] = -1.0
    assert diagnostics.scheduled_wealth[0] == expected_scheduled_month0
    assert diagnostics.stock_allocation_total_portfolio[0] == expected_merton_month0

    diagnostics.scheduled_wealth[0] = -2.0
    assert scheduled_wealth[0] == -1.0
    assert diagnostics.rra_by_month[1] == RRA_INFINITE_SENTINEL


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

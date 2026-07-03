import numpy as np
import pytest
from simulation.npv import (
    carve_pools,
    expenses_scale_for_normal_run,
    target_general_withdrawal,
)

TOL = 1e-6


def test_expenses_scale_more_wealth():
    # pinned: tpaw run_tpaw.cu _get_precomputation_at_start "more wealth"
    balance = 100000.0
    npv_income = 40000.0
    current_income = 10000.0
    wealth = balance + npv_income + current_income
    scheduled_balance = 90000.0
    scheduled_npv_income = 50000.0
    scheduled_wealth = scheduled_balance + scheduled_npv_income
    elasticity_discretionary = 0.2
    elasticity_legacy = 0.5
    p_increase = (wealth - scheduled_wealth) / scheduled_wealth

    scale = expenses_scale_for_normal_run(
        wealth=wealth,
        scheduled_wealth=scheduled_wealth,
        elasticity_discretionary=elasticity_discretionary,
        elasticity_legacy=elasticity_legacy,
    )

    assert scale.discretionary == pytest.approx(
        p_increase * elasticity_discretionary + 1.0, abs=TOL
    )
    assert scale.legacy == pytest.approx(p_increase * elasticity_legacy + 1.0, abs=TOL)


def test_expenses_scale_clamped_to_zero():
    wealth = 0.0
    scheduled_wealth = 100000.0
    elasticity_discretionary = 10.0
    elasticity_legacy = 10.0

    scale = expenses_scale_for_normal_run(
        wealth=wealth,
        scheduled_wealth=scheduled_wealth,
        elasticity_discretionary=elasticity_discretionary,
        elasticity_legacy=elasticity_legacy,
    )

    assert scale.discretionary == 0.0
    assert scale.legacy == 0.0


def test_general_pool_is_wealth_minus_constrained_spending():
    # essential then discretionary then legacy, each clamped to balance; with
    # all reserves zero, the entire wealth flows through to the general pool.
    wealth = 150000.0

    _, _, general = carve_pools(
        wealth=wealth,
        essential_reserve=0.0,
        discretionary_reserve=0.0,
        legacy_reserve=0.0,
    )

    assert general == pytest.approx(wealth, abs=TOL)


def test_target_general_withdrawal_amortizes_pool():
    # pinned: tpaw run_tpaw.cu _get_target_withdrawals "withdrawal_started"
    general_pool = 50000.0
    cumulative = 0.05  # nonsense value, but matches tpaw

    result = target_general_withdrawal(
        withdrawal_started=True,
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
    )

    assert result == pytest.approx(general_pool / cumulative, abs=TOL)


def test_target_general_zero_before_withdrawal_start():
    general_pool = 50000.0
    cumulative = 0.05

    result = target_general_withdrawal(
        withdrawal_started=False,
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
    )

    assert result == 0.0


def test_target_general_defaults_to_withdrawal_started():
    general_pool = 50000.0
    cumulative = 0.05

    result = target_general_withdrawal(
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
    )

    assert result == pytest.approx(general_pool / cumulative, abs=TOL)


def test_target_general_zero_when_cumulative_factor_is_zero():
    # Guards a division-by-zero that would otherwise crash the very first
    # simulated month, where the cumulative discount factor starts at 0.
    general_pool = 50000.0
    cumulative_zero = 0.0

    result = target_general_withdrawal(
        general_pool=general_pool,
        cumulative_1_plus_g_over_1_plus_r=cumulative_zero,
    )

    assert result == 0.0


def test_carve_pools_draws_essential_then_discretionary_then_legacy_in_order():
    wealth = 100.0
    essential_reserve = 30.0
    discretionary_reserve = 50.0
    legacy_reserve = 40.0

    discretionary, legacy, general = carve_pools(
        wealth=wealth,
        essential_reserve=essential_reserve,
        discretionary_reserve=discretionary_reserve,
        legacy_reserve=legacy_reserve,
    )

    remaining_after_essential = wealth - essential_reserve
    expected_discretionary = min(remaining_after_essential, discretionary_reserve)
    remaining_after_discretionary = remaining_after_essential - expected_discretionary
    expected_legacy = min(remaining_after_discretionary, legacy_reserve)
    expected_general = remaining_after_discretionary - expected_legacy
    assert discretionary == pytest.approx(expected_discretionary, abs=TOL)
    assert legacy == pytest.approx(expected_legacy, abs=TOL)
    assert general == pytest.approx(expected_general, abs=TOL)


def test_carve_pools_is_array_safe():
    wealth = np.array([100.0, 10.0])
    essential_reserve = 30.0
    discretionary_reserve = 50.0
    legacy_reserve = 40.0

    discretionary, legacy, general = carve_pools(
        wealth=wealth,
        essential_reserve=essential_reserve,
        discretionary_reserve=discretionary_reserve,
        legacy_reserve=legacy_reserve,
    )
    discretionary = np.asarray(discretionary)
    legacy = np.asarray(legacy)
    general = np.asarray(general)

    assert discretionary.shape == wealth.shape
    assert legacy.shape == wealth.shape
    assert general.shape == wealth.shape
    # The second run has less wealth than the essential reserve alone, so
    # every downstream pool must clamp to zero rather than go negative.
    assert discretionary[1] == pytest.approx(0.0, abs=TOL)
    assert legacy[1] == pytest.approx(0.0, abs=TOL)
    assert general[1] == pytest.approx(0.0, abs=TOL)

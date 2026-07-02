import pytest
from simulation.npv import (
    expenses_scale_for_normal_run,
    precomputation_general_pool,
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
    # essential then discretionary*scale then legacy*scale, each clamped to balance.
    wealth = 150000.0

    pool = precomputation_general_pool(
        wealth=wealth,
        npv_essential=0.0,
        npv_discretionary=0.0,
        npv_legacy=0.0,
        scale_discretionary=1.0,
        scale_legacy=1.0,
    )

    assert pool == pytest.approx(wealth, abs=TOL)


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

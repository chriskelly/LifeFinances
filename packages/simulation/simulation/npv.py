from __future__ import annotations

from dataclasses import dataclass

from simulation.withdrawals import _withdraw


@dataclass(frozen=True)
class ExpensesScale:
    discretionary: float
    legacy: float


def expenses_scale_for_normal_run(
    *,
    wealth: float,
    scheduled_wealth: float,
    elasticity_discretionary: float,
    elasticity_legacy: float,
) -> ExpensesScale:
    if scheduled_wealth == 0.0:
        p_increase = 0.0
    else:
        p_increase = wealth / scheduled_wealth - 1.0
    return ExpensesScale(
        discretionary=max(0.0, p_increase * elasticity_discretionary + 1.0),
        legacy=max(0.0, p_increase * elasticity_legacy + 1.0),
    )


def precomputation_general_pool(
    *,
    wealth: float,
    npv_essential: float,
    npv_discretionary: float,
    npv_legacy: float,
    scale_discretionary: float,
    scale_legacy: float,
) -> float:
    balance = wealth
    _, balance = _withdraw(balance, npv_essential)
    _, balance = _withdraw(balance, npv_discretionary * scale_discretionary)
    _, balance = _withdraw(balance, npv_legacy * scale_legacy)
    return balance


def target_general_withdrawal(
    *,
    withdrawal_started: bool,
    general_pool: float,
    cumulative_1_plus_g_over_1_plus_r: float,
) -> float:
    if not withdrawal_started:
        return 0.0
    return general_pool / cumulative_1_plus_g_over_1_plus_r

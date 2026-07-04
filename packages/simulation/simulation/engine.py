"""Vectorized forward monthly TPAW simulation engine.

Mirrors `run_tpaw.cu::_kernel` / `_single_month`: the array axis is the run
axis, and this module advances every run one month at a time using the
per-month planning-return precompute from `preprocess.py` and the per-run
bootstrapped simple returns from Phase 3a.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from simulation.npv import (
    carve_pools,
    expenses_scale_for_normal_run,
    target_general_withdrawal,
)
from simulation.preprocess import ProcessedPlan
from simulation.result import SimulationResult

_SAVINGS_FLOOR = 1e-5  # tpaw _get_stock_allocation limit as savings balance → 0


def _stock_fraction(
    processed: ProcessedPlan,
    month: int,
    *,
    balance_after_withdrawals,
    scale_discretionary,
    scale_legacy,
):
    """tpaw `_get_stock_allocation`: a *separate* pool carve on the post-withdrawal
    savings balance plus future income NPV — using the without-current-month NPVs,
    since this month's expenses were already withdrawn. Returns the saturated
    savings-portfolio stock fraction.
    """
    savings_balance = np.maximum(balance_after_withdrawals, _SAVINGS_FLOOR)
    base = savings_balance + processed.npv_income_without_current[month]
    discretionary, legacy, general = carve_pools(
        wealth=base,
        essential_reserve=processed.npv_essential_without_current[month],
        discretionary_reserve=(
            processed.npv_discretionary_without_current[month] * scale_discretionary
        ),
        legacy_reserve=processed.legacy_npv[month] * scale_legacy,
    )
    alloc = processed.stock_allocation_total_portfolio[month]
    legacy_alloc = processed.legacy_stock_allocation
    stocks_target = legacy * legacy_alloc + (discretionary + general) * alloc
    return np.clip(stocks_target / savings_balance, 0.0, 1.0)


def _expected_run(
    processed: ProcessedPlan,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Deterministic planning-return pass (tpaw's `is_expected_run` branch, scale=1).

    Establishes, per month, the *scheduled* wealth and the elasticities of the
    discretionary/legacy goals w.r.t. wealth. Advances the balance with the same
    withdrawal + allocation steps as a normal run, using the scalar planning
    (expected) monthly returns — so scheduled wealth is consistent with a normal
    run whose realized returns equal the planning returns.
    """
    months = processed.months
    scheduled_wealth = np.zeros(months, dtype=np.float64)
    elasticity_discretionary = np.zeros(months, dtype=np.float64)
    elasticity_legacy = np.zeros(months, dtype=np.float64)

    stock_return = processed.monthly_planning_stocks
    bond_return = processed.monthly_planning_bonds

    balance = processed.starting_balance
    for month in range(months):
        income = processed.income_real[month]
        current_essential = processed.essential_real[month]
        current_discretionary = processed.discretionary_real[month]
        wealth = balance + processed.npv_income_without_current[month] + income
        scheduled_wealth[month] = wealth

        # Wealth-based pools (current month included), scale = 1 on the expected run.
        discretionary_pool, legacy_pool, general_pool = carve_pools(
            wealth=wealth,
            essential_reserve=(
                processed.npv_essential_without_current[month] + current_essential
            ),
            discretionary_reserve=(
                processed.npv_discretionary_without_current[month]
                + current_discretionary
            ),
            legacy_reserve=processed.legacy_npv[month],
        )

        alloc = processed.stock_allocation_total_portfolio[month]
        legacy_alloc = processed.legacy_stock_allocation
        if wealth == 0.0:
            elasticity_wealth = (2.0 * alloc + legacy_alloc) / 3.0
        else:
            stocks = (
                discretionary_pool + general_pool
            ) * alloc + legacy_pool * legacy_alloc
            elasticity_wealth = stocks / wealth
        if elasticity_wealth != 0.0:
            elasticity_discretionary[month] = alloc / elasticity_wealth
            elasticity_legacy[month] = legacy_alloc / elasticity_wealth

        # Target withdrawals then advance the balance at planning returns.
        target_general = target_general_withdrawal(
            general_pool=general_pool,
            cumulative_1_plus_g_over_1_plus_r=processed.cumulative_1_plus_g_over_1_plus_r[
                month
            ],
        )
        avail = balance + income
        avail -= min(avail, current_essential)
        avail -= min(avail, current_discretionary)
        avail -= min(avail, target_general)

        stock_fraction = float(
            _stock_fraction(
                processed,
                month,
                balance_after_withdrawals=avail,
                scale_discretionary=1.0,
                scale_legacy=1.0,
            )
        )
        balance = avail * (
            stock_fraction * (1.0 + stock_return)
            + (1.0 - stock_fraction) * (1.0 + bond_return)
        )

    return scheduled_wealth, elasticity_discretionary, elasticity_legacy


def simulate_monthly(
    processed: ProcessedPlan,
    *,
    stocks_return: np.ndarray,
    bonds_return: np.ndarray,
    ran_at: datetime | None = None,
) -> SimulationResult:
    ran_at = ran_at or datetime.now()
    num_runs, months = stocks_return.shape

    scheduled_wealth, elast_disc, elast_legacy = _expected_run(processed)

    balance = np.full(num_runs, processed.starting_balance, dtype=np.float64)
    insufficient = np.zeros(num_runs, dtype=bool)

    balance_start = np.empty((num_runs, months), dtype=np.float64)
    w_essential = np.empty((num_runs, months), dtype=np.float64)
    w_discretionary = np.empty((num_runs, months), dtype=np.float64)
    w_general = np.empty((num_runs, months), dtype=np.float64)
    w_total = np.empty((num_runs, months), dtype=np.float64)
    savings_alloc = np.empty((num_runs, months), dtype=np.float64)

    for month in range(months):
        balance_start[:, month] = balance
        income = processed.income_real[month]
        current_essential = processed.essential_real[month]
        current_discretionary = processed.discretionary_real[month]
        wealth = balance + processed.npv_income_without_current[month] + income

        # Elasticity scaling of discretionary/legacy goals vs. the scheduled run.
        scale = expenses_scale_for_normal_run(
            wealth=wealth,
            scheduled_wealth=scheduled_wealth[month],
            elasticity_discretionary=elast_disc[month],
            elasticity_legacy=elast_legacy[month],
        )
        scale_disc = scale.discretionary
        scale_legacy = scale.legacy

        # Wealth-based pools (current month included) → general pool to amortize.
        _, _, general_pool = carve_pools(
            wealth=wealth,
            essential_reserve=(
                processed.npv_essential_without_current[month] + current_essential
            ),
            discretionary_reserve=(
                processed.npv_discretionary_without_current[month]
                + current_discretionary
            )
            * scale_disc,
            legacy_reserve=processed.legacy_npv[month] * scale_legacy,
        )

        target_essential = current_essential
        target_discretionary = current_discretionary * scale_disc
        target_general = target_general_withdrawal(
            general_pool=general_pool,
            cumulative_1_plus_g_over_1_plus_r=processed.cumulative_1_plus_g_over_1_plus_r[
                month
            ],
        )

        # Contributions + withdrawals (each draw clamped to the running balance).
        avail = balance + income
        drawn_essential = np.minimum(avail, target_essential)
        avail = avail - drawn_essential
        drawn_discretionary = np.minimum(avail, target_discretionary)
        avail = avail - drawn_discretionary
        drawn_general = np.minimum(avail, target_general)
        avail = avail - drawn_general

        requested = target_essential + target_discretionary + target_general
        insufficient |= requested > (balance + income)

        # Stock fraction from tpaw's separate savings-based carve, then rebalance.
        stock_fraction = _stock_fraction(
            processed,
            month,
            balance_after_withdrawals=avail,
            scale_discretionary=scale_disc,
            scale_legacy=scale_legacy,
        )
        stocks_amount = avail * stock_fraction
        bonds_amount = avail - stocks_amount
        balance = stocks_amount * (1.0 + stocks_return[:, month]) + bonds_amount * (
            1.0 + bonds_return[:, month]
        )

        w_essential[:, month] = drawn_essential
        w_discretionary[:, month] = drawn_discretionary
        w_general[:, month] = drawn_general
        w_total[:, month] = drawn_essential + drawn_discretionary + drawn_general
        savings_alloc[:, month] = stock_fraction

    return SimulationResult(
        ran_at=ran_at,
        horizon_months=months,
        num_runs=num_runs,
        balance_start=balance_start,
        withdrawals_essential=w_essential,
        withdrawals_discretionary=w_discretionary,
        withdrawals_general=w_general,
        withdrawals_total=w_total,
        savings_stock_allocation=savings_alloc,
        num_runs_insufficient=int(insufficient.sum()),
    )

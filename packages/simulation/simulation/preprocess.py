"""Assemble per-month engine inputs (risk, Merton allocation, backward NPV pass).

Mirrors tpaw's `process_plan_params_server.rs` / the precompute stage of
`cuda_process_tpaw_run_x_mfn_simulated_x_mfn.cu`, using the **planning (expected)
returns** for discounting rather than per-run bootstrapped returns.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np
from core.models import PersonHousehold, Plan
from core.streams import TimedStream
from core.timeline import Timeline, person_end_date, project_stream

from domain import build_monthly_cashflows
from simulation.market_data import resolve_inflation
from simulation.mertons import effective_mertons
from simulation.planning_returns import resolve_planning_returns
from simulation.risk import legacy_rra, rra_by_month


@dataclass(frozen=True)
class ProcessedPlan:
    months: int
    starting_balance: float
    income_real: np.ndarray
    essential_real: np.ndarray
    discretionary_real: np.ndarray
    rra: np.ndarray
    stock_allocation_total_portfolio: np.ndarray
    legacy_stock_allocation: float
    spending_tilt: np.ndarray
    npv_income_without_current: np.ndarray
    npv_essential_without_current: np.ndarray
    npv_discretionary_without_current: np.ndarray
    legacy_npv: np.ndarray
    cumulative_1_plus_g_over_1_plus_r: np.ndarray
    # Scalar monthly planning (expected) returns — drive the deterministic
    # "expected run" balance trajectory that establishes scheduled wealth.
    monthly_planning_stocks: float
    monthly_planning_bonds: float


def _sum_streams(streams: Sequence[TimedStream], timeline: Timeline) -> np.ndarray:
    months = timeline.horizon_months
    total = np.zeros(months, dtype=np.float64)
    for stream in streams:
        series = project_stream(stream, timeline)
        total += np.array([float(value) for value in series], dtype=np.float64)
    return total


def _current_age_months(person: PersonHousehold, today: date) -> int:
    return (today.year - person.birth_year) * 12 + (today.month - person.birth_month)


def preprocess(plan: Plan, *, today: date | None = None) -> ProcessedPlan:
    today = today or date.today()
    timeline = Timeline(plan, today=today)
    months = timeline.horizon_months

    cashflows = build_monthly_cashflows(plan, today=today)
    if len(cashflows.net_cashflow) != months:
        raise ValueError(
            "domain cashflow horizon must match core.timeline horizon: "
            f"got {len(cashflows.net_cashflow)}, expected {months}"
        )
    inflation = resolve_inflation(plan, today=today)
    planning = resolve_planning_returns(plan)
    if 1.0 + planning.annual_bonds <= 0.0:
        raise ValueError(
            f"planning annual bond return {planning.annual_bonds} implies "
            "total loss or worse (1 + rate <= 0); cannot compound monthly"
        )
    if 1.0 + planning.annual_stocks <= 0.0:
        raise ValueError(
            f"planning annual stock return {planning.annual_stocks} implies "
            "total loss or worse (1 + rate <= 0); cannot compound monthly"
        )

    # Real conversion: divide month t nominal by (1 + monthly_inflation) ** t.
    deflator = (1.0 + inflation.monthly) ** np.arange(months, dtype=np.float64)
    income_nominal = np.array(
        [float(value) for value in cashflows.net_cashflow], dtype=np.float64
    )
    income_real = income_nominal / deflator
    essential_real = _sum_streams(plan.extra_essential_spending, timeline) / deflator
    discretionary_real = (
        _sum_streams(plan.extra_discretionary_spending, timeline) / deflator
    )

    # Per-month RRA from the longer-lived person's age glide. "Longer-lived"
    # must match core.timeline.horizon_months's own criterion (latest
    # birth_year + max_age_years), not raw max_age_years alone — two people
    # with different birth years can have the higher max_age_years but the
    # earlier absolute end date.
    people = plan.household.people
    longer = max(people, key=person_end_date)
    rra = rra_by_month(
        plan.risk,
        num_months=months,
        current_age_months=_current_age_months(longer, today),
        max_age_months=longer.max_age_years * 12,
    )

    # Per-month Merton allocation + spending tilt using planning returns.
    equity_premium = planning.annual_stocks - planning.annual_bonds
    stock_alloc = np.empty(months, dtype=np.float64)
    spending_tilt = np.empty(months, dtype=np.float64)
    for month in range(months):
        merton = effective_mertons(
            annual_bond_return=planning.annual_bonds,
            annual_equity_premium=equity_premium,
            annual_variance_stocks=planning.annual_stock_log_variance,
            rra=float(rra[month]),
            time_preference=float(plan.risk.time_preference),
            annual_additional_spending_tilt=float(
                plan.risk.additional_annual_spending_tilt
            ),
        )
        stock_alloc[month] = merton.stock_allocation
        spending_tilt[month] = merton.spending_tilt

    legacy_alloc = effective_mertons(
        annual_bond_return=planning.annual_bonds,
        annual_equity_premium=equity_premium,
        annual_variance_stocks=planning.annual_stock_log_variance,
        rra=legacy_rra(plan.risk),
        time_preference=0.0,
        annual_additional_spending_tilt=0.0,
    ).stock_allocation

    monthly_bonds = (1.0 + planning.annual_bonds) ** (1.0 / 12.0) - 1.0
    monthly_stocks = (1.0 + planning.annual_stocks) ** (1.0 / 12.0) - 1.0
    one_over_1p_bonds = 1.0 / (1.0 + monthly_bonds)
    monthly_premium = monthly_stocks - monthly_bonds

    # Backward NPV pass: income/essential discounted at the bond rate;
    # discretionary and the amortization factor at the (month-specific)
    # total-portfolio rate implied by that month's Merton allocation.
    npv_income = np.zeros(months, dtype=np.float64)
    npv_essential = np.zeros(months, dtype=np.float64)
    npv_discretionary = np.zeros(months, dtype=np.float64)
    cumulative = np.zeros(months, dtype=np.float64)

    income_with_current = 0.0
    essential_with_current = 0.0
    discretionary_with_current = 0.0
    cumulative_running = 0.0
    for month in range(months - 1, -1, -1):
        one_plus_r_portfolio = 1.0 + (
            monthly_premium * stock_alloc[month] + monthly_bonds
        )
        one_over_r_portfolio = 1.0 / one_plus_r_portfolio

        income_with_current = (
            income_with_current * one_over_1p_bonds + income_real[month]
        )
        essential_with_current = (
            essential_with_current * one_over_1p_bonds + essential_real[month]
        )
        discretionary_with_current = (
            discretionary_with_current * one_over_r_portfolio
            + discretionary_real[month]
        )

        one_plus_g_over_r = (spending_tilt[month] + 1.0) * one_over_r_portfolio
        cumulative_running = cumulative_running * one_plus_g_over_r + 1.0
        cumulative[month] = cumulative_running

        npv_income[month] = income_with_current - income_real[month]
        npv_essential[month] = essential_with_current - essential_real[month]
        npv_discretionary[month] = (
            discretionary_with_current - discretionary_real[month]
        )

    # Legacy NPV per month at the legacy portfolio rate, months-remaining
    # (inclusive of the current month) periods out.
    legacy_target = float(plan.legacy_target)
    months_remaining = np.arange(months, 0, -1, dtype=np.float64)
    r_legacy = monthly_premium * legacy_alloc + monthly_bonds
    legacy_npv = legacy_target / np.power(1.0 + r_legacy, months_remaining)

    return ProcessedPlan(
        months=months,
        starting_balance=float(plan.portfolio.current_savings_balance),
        income_real=income_real,
        essential_real=essential_real,
        discretionary_real=discretionary_real,
        rra=rra,
        stock_allocation_total_portfolio=stock_alloc,
        legacy_stock_allocation=legacy_alloc,
        spending_tilt=spending_tilt,
        npv_income_without_current=npv_income,
        npv_essential_without_current=npv_essential,
        npv_discretionary_without_current=npv_discretionary,
        legacy_npv=legacy_npv,
        cumulative_1_plus_g_over_1_plus_r=cumulative,
        monthly_planning_stocks=monthly_stocks,
        monthly_planning_bonds=monthly_bonds,
    )

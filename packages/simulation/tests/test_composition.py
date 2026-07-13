from datetime import date
from decimal import Decimal

import numpy as np
from core.defaults import default_plan
from core.job import Job
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary
from simulation.composition import (
    WealthBySource,
    prorate_net_income_by_source,
    wealth_by_income_source,
)
from simulation.preprocess import ProcessedPlan, preprocess


def _plan_with_job_income() -> Plan:
    """Minimal plan with positive gross job income across the horizon."""
    base = default_plan()
    job = Job(
        annual_income=Decimal("120_000"),
        end=CalendarMonthBoundary(year=2045, month=12),
    )
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1983,
        jobs=[job],
        social_security=base.household.person1.social_security,
    )
    return Plan(
        name="Composition Integration",
        household=Household(person1=person1, person2=base.household.person2),
        portfolio=Portfolio(current_savings_balance=Decimal("500_000")),
    )


def _npv_including_current_closed_form(
    real_series: np.ndarray, *, one_over: float
) -> np.ndarray:
    """Independent expected NPV: sum of each month's real value discounted back.

    Deliberately does NOT call the production `backward_npv_including_current`
    so the reconciliation test verifies composition's discounting rather than
    trivially restating the helper it uses internally.
    """
    months = len(real_series)
    return np.array(
        [
            sum(real_series[k] * one_over ** (k - m) for k in range(m, months))
            for m in range(months)
        ],
        dtype=np.float64,
    )


def test_prorated_nets_sum_to_net_cashflow_when_gross_positive():
    gross_job = np.array([80.0], dtype=np.float64)
    gross_ss = np.array([20.0], dtype=np.float64)
    gross_pension = np.array([0.0], dtype=np.float64)
    gross_manual = np.array([0.0], dtype=np.float64)
    # Domain stores taxes as non-positive.
    taxes = np.array([-10.0], dtype=np.float64)
    total_gross = gross_job + gross_ss + gross_pension + gross_manual
    net_cashflow = total_gross + taxes

    nets = prorate_net_income_by_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        taxes=taxes,
    )

    summed = nets["job"] + nets["social_security"] + nets["pension"] + nets["manual"]
    np.testing.assert_allclose(summed, net_cashflow)


def test_proration_zero_gross_month_yields_zero_nets():
    zeros = np.array([0.0], dtype=np.float64)
    taxes = np.array([-5.0], dtype=np.float64)  # residual tax ignored for composition

    nets = prorate_net_income_by_source(
        gross_job=zeros,
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        taxes=taxes,
    )

    for series in nets.values():
        np.testing.assert_allclose(series, zeros)


def test_wealth_by_source_sums_to_independently_discounted_combined_income():
    months = 4
    # total_gross is positive every month, so combined nets == net cashflow and
    # the wealth bands must reconcile with the combined-income NPV.
    gross_job = np.array([100.0, 100.0, 0.0, 0.0], dtype=np.float64)
    gross_ss = np.array([0.0, 0.0, 50.0, 50.0], dtype=np.float64)
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-20.0, -20.0, -5.0, -5.0], dtype=np.float64)
    monthly_inflation = 0.02  # nonzero so the deflator is actually exercised
    monthly_bond = 0.01
    one_over = 1.0 / (1.0 + monthly_bond)

    wealth = wealth_by_income_source(
        gross_job=gross_job,
        gross_social_security=gross_ss,
        gross_pension=zeros,
        gross_manual=zeros,
        taxes=taxes,
        monthly_inflation=monthly_inflation,
        monthly_bond_rate=monthly_bond,
    )

    combined_nominal = gross_job + gross_ss + taxes
    deflator = (1.0 + monthly_inflation) ** np.arange(months, dtype=np.float64)
    combined_real = combined_nominal / deflator
    expected_total = _npv_including_current_closed_form(
        combined_real, one_over=one_over
    )

    actual_total = wealth.job + wealth.social_security + wealth.pension + wealth.manual
    np.testing.assert_allclose(actual_total, expected_total)


def test_proration_zero_gross_months_stay_zero_across_horizon():
    # Composition intentionally drops residual taxes when a month has no gross
    # income (spec §7.1): those months contribute nothing to any wealth band.
    months = 3
    zeros = np.zeros(months, dtype=np.float64)
    taxes = np.array([-5.0, -3.0, -1.0], dtype=np.float64)

    nets = prorate_net_income_by_source(
        gross_job=zeros,
        gross_social_security=zeros.copy(),
        gross_pension=zeros.copy(),
        gross_manual=zeros.copy(),
        taxes=taxes,
    )

    for series in nets.values():
        np.testing.assert_allclose(series, zeros)


def _wealth_from_processed(processed: ProcessedPlan) -> WealthBySource:
    return wealth_by_income_source(
        gross_job=processed.gross_job,
        gross_social_security=processed.gross_social_security,
        gross_pension=processed.gross_pension,
        gross_manual=processed.gross_manual,
        taxes=processed.taxes,
        monthly_inflation=processed.monthly_inflation,
        monthly_bond_rate=processed.monthly_planning_bonds,
    )


def test_wealth_bands_reconcile_with_preprocess_income_npv():
    # Spec §7.2: Σ wealth_s[m] == npv_income_without_current[m] + income_real[m]
    # when composition and preprocess share the same discount path and net total.
    # Zero-gross months (spec §7.1) omit residual taxes from composition, so only
    # assert months where total_gross > 0.
    today = date(2026, 1, 1)
    processed = preprocess(_plan_with_job_income(), today=today)
    wealth = _wealth_from_processed(processed)

    total_gross = (
        processed.gross_job
        + processed.gross_social_security
        + processed.gross_pension
        + processed.gross_manual
    )
    positive_gross = total_gross > 0.0
    assert np.any(positive_gross), "fixture must include positive-gross months"

    wealth_total = wealth.job + wealth.social_security + wealth.pension + wealth.manual
    expected = processed.npv_income_without_current + processed.income_real
    np.testing.assert_allclose(wealth_total[positive_gross], expected[positive_gross])


def test_month_zero_stack_matches_total_portfolio_wealth():
    # Spec §9.3: savings + income wealth matches hand total at month 0.
    today = date(2026, 1, 1)
    processed = preprocess(_plan_with_job_income(), today=today)
    wealth = _wealth_from_processed(processed)

    income_wealth_0 = processed.npv_income_without_current[0] + processed.income_real[0]
    stacked_0 = (
        processed.starting_balance
        + wealth.job[0]
        + wealth.social_security[0]
        + wealth.pension[0]
        + wealth.manual[0]
    )
    hand_total_0 = processed.starting_balance + income_wealth_0
    np.testing.assert_allclose(stacked_0, hand_total_0)

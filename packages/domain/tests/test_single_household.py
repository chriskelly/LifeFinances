from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.job import FormulaPension, Job
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.social_security import (
    FULL_RETIREMENT_AGE_MONTHS,
    AnnualEarnings,
    PersonSocialSecurityConfig,
)
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from core.timeline import Timeline
from domain.job_income import project_job_income
from domain.pension import project_pension
from domain.social_security import project_social_security
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from domain.taxes import compute_taxes

from domain import build_monthly_cashflows


def _single_person_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1983,
        jobs=[
            Job(
                annual_income=Decimal("120_000"),
                end=CalendarMonthBoundary(year=2045, month=12),
            )
        ],
    )
    return Plan(
        name="Single Person",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_job_income_omits_absent_partner_and_totals_equal_person1() -> None:
    plan = _single_person_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))

    projection = project_job_income(plan, timeline)

    assert projection.person2 is None
    assert projection.total_gross == projection.person1.gross
    assert projection.total_ss_covered_gross == projection.person1.ss_covered_gross
    assert projection.total_tax_deferred == projection.person1.tax_deferred


def _single_ss_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1960,
        social_security=PersonSocialSecurityConfig(
            claim_age_months=FULL_RETIREMENT_AGE_MONTHS,
            earnings_record=[
                AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
            ],
        ),
    )
    return Plan(
        name="Single SS",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_single_person_ss_has_no_spousal_and_total_equals_own() -> None:
    plan = _single_ss_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person2 is None
    assert projection.person1.spousal_alternative == (
        [Decimal("0.00")] * timeline.horizon_months
    )
    assert projection.person1.max_benefit == projection.person1.own_benefit
    assert projection.total == projection.person1.max_benefit


def _single_pension_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1970,
        jobs=[
            Job(
                annual_income=Decimal("120_000"),
                end=PersonAgeBoundary(person="person1", age_months=62 * 12),
                pension=FormulaPension(
                    service_start=CalendarMonthBoundary(year=2010, month=1),
                    claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
                    age_factor_table=age_factors_from_statutory(
                        CALSTRS_2_AT_62_AGE_FACTORS
                    ),
                ),
            )
        ],
    )
    return Plan(
        name="Single Pension",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_single_person_pension_projects_without_partner() -> None:
    plan = _single_pension_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert len(projection.formula) == timeline.horizon_months
    assert any(value > Decimal("0.00") for value in projection.formula)


def test_single_person_taxes_use_single_brackets_and_no_partner_fica() -> None:
    plan = _single_person_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)
    social_security = project_social_security(plan, timeline, job_income)
    pension = project_pension(plan, timeline, job_income)

    taxes = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=social_security,
        pension=pension,
    )

    assert len(taxes.fica_social_security) == timeline.horizon_months
    assert any(value < Decimal("0.00") for value in taxes.fica_social_security)


def test_single_person_cashflows_run_end_to_end() -> None:
    plan = _single_person_plan()
    today = date(2026, 1, 1)

    cashflows = build_monthly_cashflows(plan, today=today)

    horizon = Timeline(plan, today=today).horizon_months
    assert len(cashflows.net_cashflow) == horizon

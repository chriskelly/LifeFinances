from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.job import AgeFactor, FormulaPension, Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from core.timeline import Timeline
from domain.pension.formula import (
    claim_age_months,
    final_compensation,
    interpolate_age_factor,
    service_credit_years,
)
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def test_calstrs_table_spans_55_to_65_and_is_monotonic() -> None:
    youngest_age_months = 55 * 12
    oldest_age_months = 65 * 12

    ages = [age for age, _ in CALSTRS_2_AT_62_AGE_FACTORS]
    factors = [factor for _, factor in CALSTRS_2_AT_62_AGE_FACTORS]

    assert ages[0] == youngest_age_months
    assert ages[-1] == oldest_age_months
    assert factors == sorted(factors)


def test_age_factors_from_statutory_builds_config_models() -> None:
    rows = ((62 * 12, Decimal("0.0200")), (65 * 12, Decimal("0.0240")))

    result = age_factors_from_statutory(rows)

    assert result == [
        AgeFactor(age_months=62 * 12, factor=Decimal("0.0200")),
        AgeFactor(age_months=65 * 12, factor=Decimal("0.0240")),
    ]


def _person_with_job(job: Job, *, birth_year: int = 1983) -> PersonHousehold:
    return PersonHousehold(birth_month=1, birth_year=birth_year, jobs=[job])


def _plan_with_person1_job(job: Job) -> Plan:
    return Plan(
        name="Pension Test",
        household=Household(
            person1=_person_with_job(job),
            person2=PersonHousehold(birth_month=1, birth_year=1985),
        ),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_service_credit_counts_inclusive_months_as_years() -> None:
    service_start = CalendarMonthBoundary(year=2016, month=1)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    expected_years = Decimal(30)
    job = Job(
        annual_income=Decimal("120_000"),
        end=job_end,
        pension=FormulaPension(
            service_start=service_start,
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
        ),
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    assert service_credit_years(job=job, timeline=timeline) == expected_years


def test_service_credit_reduced_by_sabbatical_loss() -> None:
    service_start = CalendarMonthBoundary(year=2016, month=1)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    remaining = Decimal("0.5")
    break_start = CalendarMonthBoundary(year=2030, month=1)
    break_end = CalendarMonthBoundary(year=2030, month=12)
    window_years = Decimal(12) / Decimal(12)
    expected_years = Decimal(30) - (Decimal(1) - remaining) * window_years
    job = Job(
        annual_income=Decimal("120_000"),
        end=job_end,
        sabbaticals=[
            SabbaticalWindow(
                start=break_start,
                end=break_end,
                remaining_fraction=remaining,
            )
        ],
        pension=FormulaPension(
            service_start=service_start,
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
        ),
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    assert service_credit_years(job=job, timeline=timeline) == expected_years


def test_service_credit_requires_job_end() -> None:
    job = Job(
        annual_income=Decimal("120_000"),
        pension=FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
        ),
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    with pytest.raises(ValueError, match="job end"):
        service_credit_years(job=job, timeline=timeline)


def test_final_compensation_averages_trailing_months_annualized() -> None:
    monthly_income = Decimal("10_000")
    annual_income = monthly_income * Decimal(12)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    job = Job(
        annual_income=annual_income,
        end=job_end,
        pension=FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
            final_comp_averaging_months=12,
        ),
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    # No raise, no sabbatical => final comp equals the annual income.
    assert final_compensation(job=job, timeline=timeline) == annual_income


def test_interpolate_age_factor_is_linear_between_rows() -> None:
    factor_at_62 = Decimal("0.0200")
    factor_at_63 = Decimal("0.0213")
    table = [
        AgeFactor(age_months=62 * 12, factor=factor_at_62),
        AgeFactor(age_months=63 * 12, factor=factor_at_63),
    ]
    midpoint_age = 62 * 12 + 6
    expected = factor_at_62 + (factor_at_63 - factor_at_62) * (Decimal(6) / Decimal(12))

    assert interpolate_age_factor(table, midpoint_age) == expected


def test_interpolate_age_factor_clamps_outside_table_range() -> None:
    factor_at_62 = Decimal("0.0200")
    factor_at_65 = Decimal("0.0240")
    table = [
        AgeFactor(age_months=62 * 12, factor=factor_at_62),
        AgeFactor(age_months=65 * 12, factor=factor_at_65),
    ]

    assert interpolate_age_factor(table, 55 * 12) == factor_at_62
    assert interpolate_age_factor(table, 70 * 12) == factor_at_65


def test_interpolate_age_factor_rejects_empty_table() -> None:
    with pytest.raises(ValueError, match="empty"):
        interpolate_age_factor([], 62 * 12)


def test_claim_age_months_uses_owning_person_birth() -> None:
    birth_year = 1983
    claim_age = 62 * 12
    person = PersonHousehold(birth_month=1, birth_year=birth_year)
    household = Household(
        person1=person,
        person2=PersonHousehold(birth_month=1, birth_year=1985),
    )
    claim = PersonAgeBoundary(person="person1", age_months=claim_age)

    assert (
        claim_age_months(person=person, claim=claim, household=household) == claim_age
    )

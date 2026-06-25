from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.job import AgeFactor, FormulaPension, Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, TimedStream
from core.timeline import Timeline
from domain.job_income import project_job_income
from domain.pension import PensionProjection, project_pension
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


def _job_with_pension(
    *, annual_income: Decimal, claim_age_months_value: int, end_year: int
) -> Job:
    return Job(
        annual_income=annual_income,
        end=CalendarMonthBoundary(year=end_year, month=12),
        pension=FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(
                person="person1", age_months=claim_age_months_value
            ),
            age_factor_table=age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS),
        ),
    )


def test_project_pension_returns_horizon_length_series() -> None:
    job = _job_with_pension(
        annual_income=Decimal("109_500"), claim_age_months_value=62 * 12, end_year=2045
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert isinstance(projection, PensionProjection)
    assert len(projection.formula) == timeline.horizon_months
    assert len(projection.manual) == timeline.horizon_months
    assert len(projection.stored_total) == timeline.horizon_months


def test_formula_benefit_starts_at_claim_month_and_is_zero_before() -> None:
    claim_age = 62 * 12
    job = _job_with_pension(
        annual_income=Decimal("120_000"),
        claim_age_months_value=claim_age,
        end_year=2045,
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)
    claim_index = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    projection = project_pension(plan, timeline, job_income)

    assert projection.formula[claim_index - 1] == Decimal("0.00")
    assert projection.formula[claim_index] > Decimal("0.00")


def test_trust_factor_scales_formula_benefit() -> None:
    claim_age = 62 * 12
    reduced_trust = Decimal("0.5")
    full_job = _job_with_pension(
        annual_income=Decimal("120_000"),
        claim_age_months_value=claim_age,
        end_year=2045,
    )
    reduced_job = _job_with_pension(
        annual_income=Decimal("120_000"),
        claim_age_months_value=claim_age,
        end_year=2045,
    )
    assert reduced_job.pension is not None
    reduced_job.pension.trust_factor = reduced_trust
    full_plan = _plan_with_person1_job(full_job)
    reduced_plan = _plan_with_person1_job(reduced_job)
    full_timeline = Timeline(full_plan, today=date(2026, 1, 1))
    reduced_timeline = Timeline(reduced_plan, today=date(2026, 1, 1))
    claim_index = full_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    full = project_pension(
        full_plan, full_timeline, project_job_income(full_plan, full_timeline)
    )
    reduced = project_pension(
        reduced_plan,
        reduced_timeline,
        project_job_income(reduced_plan, reduced_timeline),
    )

    assert reduced.formula[claim_index] == (
        full.formula[claim_index] * reduced_trust
    ).quantize(Decimal("0.01"))


def test_changing_job_end_changes_service_credit_without_separate_pension_edit() -> (
    None
):
    claim_age = 62 * 12
    early_end_job = _job_with_pension(
        annual_income=Decimal("120_000"),
        claim_age_months_value=claim_age,
        end_year=2040,
    )
    late_end_job = _job_with_pension(
        annual_income=Decimal("120_000"),
        claim_age_months_value=claim_age,
        end_year=2045,
    )
    early_plan = _plan_with_person1_job(early_end_job)
    late_plan = _plan_with_person1_job(late_end_job)
    early_timeline = Timeline(early_plan, today=date(2026, 1, 1))
    late_timeline = Timeline(late_plan, today=date(2026, 1, 1))
    claim_index = early_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    early = project_pension(
        early_plan, early_timeline, project_job_income(early_plan, early_timeline)
    )
    late = project_pension(
        late_plan, late_timeline, project_job_income(late_plan, late_timeline)
    )

    # A longer career => more service credit => higher benefit, with no pension edit.
    assert late.formula[claim_index] > early.formula[claim_index]


def test_manual_income_streams_flow_into_pension_manual() -> None:
    monthly_amount = Decimal("1_500.00")
    plan = _plan_with_person1_job(
        _job_with_pension(
            annual_income=Decimal("120_000"),
            claim_age_months_value=62 * 12,
            end_year=2045,
        )
    )
    plan.manual_income_streams = [
        TimedStream(label="inherited pension", monthly_amount=monthly_amount)
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert projection.manual[0] == monthly_amount
    assert projection.stored_total[0] == projection.formula[0] + monthly_amount

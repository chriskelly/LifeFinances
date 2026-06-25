from __future__ import annotations

from decimal import Decimal

import pytest
from core.job import AgeFactor, FormulaPension, Job
from core.models import Household, PersonHousehold, Plan
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from pydantic import ValidationError


def _formula_pension() -> FormulaPension:
    return FormulaPension(
        service_start=CalendarMonthBoundary(year=2016, month=1),
        claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
        age_factor_table=[
            AgeFactor(age_months=62 * 12, factor=Decimal("0.0200")),
            AgeFactor(age_months=65 * 12, factor=Decimal("0.0240")),
        ],
    )


def test_formula_pension_defaults() -> None:
    expected_averaging_months = 36
    expected_trust = Decimal(1)

    pension = _formula_pension()

    assert pension.final_comp_averaging_months == expected_averaging_months
    assert pension.trust_factor == expected_trust
    assert pension.benefit_real_growth_rate == Decimal(0)


def test_trust_factor_must_be_between_zero_and_one() -> None:
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
            trust_factor=too_high,
        )


def test_job_pension_defaults_to_none() -> None:
    assert Job(annual_income=Decimal("100_000")).pension is None


def test_pension_config_round_trips_through_repository(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_pension = _formula_pension()
    job_with_pension = Job(
        annual_income=Decimal("109_500"),
        end=CalendarMonthBoundary(year=2045, month=12),
        pension=expected_pension,
    )

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=plan.household.person1.birth_month,
                birth_year=plan.household.person1.birth_year,
                max_age_years=plan.household.person1.max_age_years,
                jobs=[job_with_pension],
                social_security=plan.household.person1.social_security,
            ),
            person2=plan.household.person2,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.person1.jobs[0].pension == expected_pension

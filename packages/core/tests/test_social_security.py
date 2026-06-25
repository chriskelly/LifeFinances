# packages/core/tests/test_social_security.py
from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import Household, PersonHousehold, Plan
from core.repository import PlanRepository
from core.social_security import (
    FULL_RETIREMENT_AGE_MONTHS,
    MAX_CLAIM_AGE_MONTHS,
    MIN_CLAIM_AGE_MONTHS,
    AnnualEarnings,
    PersonSocialSecurityConfig,
)
from pydantic import ValidationError


def test_default_plan_has_social_security_defaults() -> None:
    plan = default_plan()

    assert plan.household.person1.social_security.claim_age_months == (
        FULL_RETIREMENT_AGE_MONTHS
    )
    person2 = plan.household.person2
    assert person2 is not None
    assert person2.social_security.claim_age_months == (FULL_RETIREMENT_AGE_MONTHS)
    assert plan.household.social_security_trust_factor == Decimal("1")


def test_claim_age_must_be_between_62_and_70() -> None:
    too_early = MIN_CLAIM_AGE_MONTHS - 1
    too_late = MAX_CLAIM_AGE_MONTHS + 1

    with pytest.raises(ValidationError):
        PersonSocialSecurityConfig(claim_age_months=too_early)

    with pytest.raises(ValidationError):
        PersonSocialSecurityConfig(claim_age_months=too_late)


def test_household_trust_factor_must_be_between_zero_and_one() -> None:
    base = default_plan().household
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        Household(
            person1=base.person1,
            person2=base.person2,
            social_security_trust_factor=too_high,
        )


def test_social_security_config_round_trips_through_repository(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_claim_age = MIN_CLAIM_AGE_MONTHS
    expected_trust = Decimal("0.76")
    expected_earnings = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200")),
        AnnualEarnings(year=2024, fica_earnings=Decimal("52700")),
    ]

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=plan.household.person1.birth_month,
                birth_year=plan.household.person1.birth_year,
                max_age_years=plan.household.person1.max_age_years,
                jobs=plan.household.person1.jobs,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=expected_claim_age,
                    earnings_record=expected_earnings,
                ),
            ),
            person2=plan.household.person2,
            social_security_trust_factor=expected_trust,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.person1.social_security.claim_age_months == (
        expected_claim_age
    )
    assert loaded.household.person1.social_security.earnings_record == (
        expected_earnings
    )
    assert loaded.household.social_security_trust_factor == expected_trust

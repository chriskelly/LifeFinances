from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import FilingStatus, Household, Plan
from core.repository import PlanRepository
from pydantic import ValidationError


def test_household_defaults_to_married_filing_jointly() -> None:
    expected_status: FilingStatus = "married_filing_jointly"
    expected_fraction = Decimal("0.80")

    household = default_plan().household

    assert household.filing_status == expected_status
    assert household.residence_state is None
    assert household.ss_pension_taxable_fraction == expected_fraction


def test_ss_pension_taxable_fraction_must_be_between_zero_and_one() -> None:
    base = default_plan().household
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        Household(
            person1=base.person1,
            person2=base.person2,
            ss_pension_taxable_fraction=too_high,
        )


def test_filing_status_rejects_unknown_value() -> None:
    base = default_plan().household

    with pytest.raises(ValidationError):
        Household.model_validate(
            {
                "person1": base.person1.model_dump(),
                "person2": base.person2.model_dump(),
                "filing_status": "unknown",
            }
        )


def test_household_tax_config_round_trips_through_repository(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_status: FilingStatus = "single"
    expected_state = "California"
    expected_fraction = Decimal("0.65")

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=plan.household.person1,
            person2=plan.household.person2,
            filing_status=expected_status,
            residence_state=expected_state,
            ss_pension_taxable_fraction=expected_fraction,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.filing_status == expected_status
    assert loaded.household.residence_state == expected_state
    assert loaded.household.ss_pension_taxable_fraction == expected_fraction

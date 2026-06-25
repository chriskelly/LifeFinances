from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.models import FilingStatus, Household, PersonHousehold, Plan, Portfolio
from core.timeline import horizon_months


def _person(birth_year: int) -> PersonHousehold:
    return PersonHousehold(birth_month=1, birth_year=birth_year)


def test_household_people_excludes_absent_partner() -> None:
    person1 = _person(1980)
    household = Household(person1=person1, person2=None)

    assert household.people == (person1,)


def test_household_people_includes_present_partner() -> None:
    person1 = _person(1980)
    person2 = _person(1982)
    household = Household(person1=person1, person2=person2)

    assert household.people == (person1, person2)


def test_resolved_filing_status_is_single_for_one_person() -> None:
    expected: FilingStatus = "single"
    household = Household(person1=_person(1980), person2=None)

    assert household.resolved_filing_status == expected


def test_resolved_filing_status_is_mfj_for_two_people() -> None:
    expected: FilingStatus = "married_filing_jointly"
    household = Household(person1=_person(1980), person2=_person(1982))

    assert household.resolved_filing_status == expected


def test_explicit_filing_status_overrides_household_size() -> None:
    overridden: FilingStatus = "married_filing_jointly"
    household = Household(
        person1=_person(1980),
        person2=None,
        filing_status=overridden,
    )

    assert household.resolved_filing_status == overridden


def test_person2_defaults_to_none() -> None:
    household = Household(person1=_person(1980))

    assert household.person2 is None


def test_horizon_uses_only_present_people() -> None:
    birth_year = 1980
    max_age_years = 90
    today = date(2026, 1, 1)
    person1 = PersonHousehold(
        birth_month=1, birth_year=birth_year, max_age_years=max_age_years
    )
    plan = Plan(
        name="Single",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )
    expected = (birth_year + max_age_years - today.year) * 12 + (1 - today.month)

    assert horizon_months(plan, today=today) == expected

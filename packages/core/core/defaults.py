from __future__ import annotations

from decimal import Decimal

from core.models import Household, PersonHousehold, Plan, Portfolio

DEFAULT_PLAN_NAME = "Default Plan"
DEFAULT_BIRTH_MONTH = 1
DEFAULT_PERSON1_BIRTH_YEAR = 1970
DEFAULT_PERSON2_BIRTH_YEAR = 1972
DEFAULT_MAX_AGE_YEARS = 100
DEFAULT_SAVINGS_BALANCE = Decimal("500000")


def default_plan() -> Plan:
    def person(birth_year: int) -> PersonHousehold:
        return PersonHousehold(
            birth_month=DEFAULT_BIRTH_MONTH,
            birth_year=birth_year,
            max_age_years=DEFAULT_MAX_AGE_YEARS,
        )

    return Plan(
        name=DEFAULT_PLAN_NAME,
        household=Household(
            person1=person(DEFAULT_PERSON1_BIRTH_YEAR),
            person2=person(DEFAULT_PERSON2_BIRTH_YEAR),
        ),
        portfolio=Portfolio(current_savings_balance=DEFAULT_SAVINGS_BALANCE),
    )

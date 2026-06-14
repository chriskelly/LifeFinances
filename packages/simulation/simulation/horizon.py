from __future__ import annotations

from datetime import date

from core.models import PersonHousehold, Plan


def person_end_date(person: PersonHousehold) -> date:
    return date(person.birth_year + person.max_age_years, person.birth_month, 1)


def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    household = plan.household
    end = max(person_end_date(household.person1), person_end_date(household.person2))
    return (end.year - today.year) * 12 + (end.month - today.month)

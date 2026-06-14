from __future__ import annotations

from datetime import date

from core.models import PersonHousehold, Plan
from core.streams import Boundary, CalendarMonthBoundary, PersonAgeBoundary


def add_months(year: int, month: int, months: int) -> tuple[int, int]:
    """Add `months` to a (year, month) pair. `month` is 1-12."""
    total = year * 12 + (month - 1) + months
    return total // 12, total % 12 + 1


def person_end_date(person: PersonHousehold) -> date:
    return date(person.birth_year + person.max_age_years, person.birth_month, 1)


def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    household = plan.household
    end = max(person_end_date(household.person1), person_end_date(household.person2))
    return (end.year - today.year) * 12 + (end.month - today.month)


class Timeline:
    """Resolves plan boundaries to month indices relative to `today`.

    month_index 0 is the current calendar month (today's year/month).
    """

    def __init__(self, plan: Plan, *, today: date | None = None) -> None:
        self.plan = plan
        self.today = today or date.today()

    @property
    def horizon_months(self) -> int:
        return horizon_months(self.plan, today=self.today)

    def _offset(self, year: int, month: int) -> int:
        return (year - self.today.year) * 12 + (month - self.today.month)

    def index_of(self, boundary: Boundary) -> int:
        if isinstance(boundary, CalendarMonthBoundary):
            return self._offset(boundary.year, boundary.month)
        if isinstance(boundary, PersonAgeBoundary):
            person = getattr(self.plan.household, boundary.person)
            reached_year, reached_month = add_months(
                person.birth_year, person.birth_month, boundary.age_months
            )
            return self._offset(reached_year, reached_month)
        raise TypeError(f"Unknown boundary: {boundary!r}")

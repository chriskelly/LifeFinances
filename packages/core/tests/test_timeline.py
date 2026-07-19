from __future__ import annotations

from datetime import date

from core.defaults import default_plan
from core.models import Household, PersonHousehold
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, PersonMaxAgeBoundary
from core.timeline import (
    Timeline,
    boundary_to_year_month,
    horizon_months,
    person_end_date,
)


def test_index_of_calendar_month_is_offset_from_today() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)
    target_year, target_month = 2027, 9

    result = timeline.index_of(
        CalendarMonthBoundary(year=target_year, month=target_month)
    )

    expected = (target_year - today.year) * 12 + (target_month - today.month)
    assert result == expected


def test_index_of_past_calendar_month_is_negative() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)

    result = timeline.index_of(CalendarMonthBoundary(year=2026, month=1))

    assert result == -5


def test_index_of_person_age_uses_birth_month_plus_age_months() -> None:
    today = date(2026, 1, 1)
    plan = default_plan()
    person = plan.household.person1
    age_months = 600  # 50 years
    timeline = Timeline(plan, today=today)

    result = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=age_months)
    )

    reached_year = person.birth_year + age_months // 12
    reached_month = person.birth_month
    expected = (reached_year - today.year) * 12 + (reached_month - today.month)
    assert result == expected


def test_horizon_months_matches_max_age_person_age_boundary() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)
    later = max(person_end_date(person) for person in plan.household.people)

    expected = (later.year - today.year) * 12 + (later.month - today.month)
    assert timeline.horizon_months == expected
    assert horizon_months(plan, today=today) == expected


def test_boundary_to_year_month_calendar_is_identity() -> None:
    year, month = 2031, 7

    result = boundary_to_year_month(
        CalendarMonthBoundary(year=year, month=month), default_plan().household
    )

    assert result == (year, month)


def test_boundary_to_year_month_person_age_uses_birth_plus_age() -> None:
    household = default_plan().household
    person = household.person1
    age_months = 600  # 50 years

    result = boundary_to_year_month(
        PersonAgeBoundary(person="person1", age_months=age_months), household
    )

    assert result == (person.birth_year + age_months // 12, person.birth_month)


def test_person_max_age_boundary_resolves_to_birth_month_at_max_age() -> None:
    birth_month = 3
    birth_year = 1990
    max_age_years = 95
    household = Household(
        person1=PersonHousehold(
            birth_month=birth_month, birth_year=birth_year, max_age_years=max_age_years
        )
    )

    year, month = boundary_to_year_month(
        PersonMaxAgeBoundary(person="person1"), household
    )

    assert (year, month) == (birth_year + max_age_years, birth_month)


def test_month_boundary_is_inverse_of_index_of() -> None:
    timeline = Timeline(default_plan(), today=date(2026, 6, 1))
    index = 19

    boundary = timeline.month_boundary(index)

    assert isinstance(boundary, CalendarMonthBoundary)
    assert timeline.index_of(boundary) == index

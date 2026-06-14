from __future__ import annotations

from datetime import date

from core.defaults import default_plan
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from core.timeline import Timeline, horizon_months, person_end_date


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
    later = max(
        person_end_date(plan.household.person1),
        person_end_date(plan.household.person2),
    )

    expected = (later.year - today.year) * 12 + (later.month - today.month)
    assert timeline.horizon_months == expected
    assert horizon_months(plan, today=today) == expected

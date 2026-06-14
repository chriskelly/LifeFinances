from __future__ import annotations

from decimal import Decimal

from core.streams import (
    CalendarMonthBoundary,
    PersonAgeBoundary,
    TimedStream,
)


def test_timed_stream_round_trips_through_json_preserving_decimal() -> None:
    expected_amount = Decimal("1234.56")
    expected_growth = Decimal("0.03")
    stream = TimedStream(
        label="Salary",
        monthly_amount=expected_amount,
        start=CalendarMonthBoundary(year=2030, month=4),
        end=PersonAgeBoundary(person="person1", age_months=780),
        is_nominal=True,
        annual_growth_rate=expected_growth,
    )

    loaded = TimedStream.model_validate_json(stream.model_dump_json())

    assert loaded.monthly_amount == expected_amount
    assert loaded.annual_growth_rate == expected_growth
    assert loaded.is_nominal is True


def test_boundary_union_resolves_to_correct_kind() -> None:
    calendar_year, calendar_month = 2031, 7
    age_months = 744
    stream = TimedStream(
        monthly_amount=Decimal("500"),
        start=CalendarMonthBoundary(year=calendar_year, month=calendar_month),
        end=PersonAgeBoundary(person="person2", age_months=age_months),
    )

    loaded = TimedStream.model_validate_json(stream.model_dump_json())

    assert isinstance(loaded.start, CalendarMonthBoundary)
    assert loaded.start.year == calendar_year
    assert loaded.start.month == calendar_month
    assert isinstance(loaded.end, PersonAgeBoundary)
    assert loaded.end.person == "person2"
    assert loaded.end.age_months == age_months

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline, add_months, project_stream


def _timeline() -> Timeline:
    return Timeline(default_plan(), today=date(2026, 1, 1))


def test_open_stream_fills_whole_horizon_flat() -> None:
    timeline = _timeline()
    amount = Decimal("1000.00")
    stream = TimedStream(monthly_amount=amount)

    series = project_stream(stream, timeline)

    assert len(series) == timeline.horizon_months
    assert series[0] == amount
    assert series[-1] == amount


def test_bounded_window_is_zero_outside_and_amount_inside() -> None:
    timeline = _timeline()
    amount = Decimal("500.00")
    start_index = 12
    end_index = 23
    start_year, start_month = add_months(
        timeline.today.year, timeline.today.month, start_index
    )
    end_year, end_month = add_months(
        timeline.today.year, timeline.today.month, end_index
    )
    start = CalendarMonthBoundary(year=start_year, month=start_month)
    end = CalendarMonthBoundary(year=end_year, month=end_month)
    stream = TimedStream(monthly_amount=amount, start=start, end=end)

    series = project_stream(stream, timeline)

    assert timeline.index_of(start) == start_index
    assert timeline.index_of(end) == end_index
    assert series[start_index - 1] == Decimal("0.00")
    assert series[start_index] == amount
    assert series[end_index] == amount
    assert series[end_index + 1] == Decimal("0.00")


def test_growth_compounds_monthly_from_start_anchor() -> None:
    timeline = _timeline()
    base = Decimal("1000.00")
    rate = Decimal("0.12")
    stream = TimedStream(monthly_amount=base, annual_growth_rate=rate)

    series = project_stream(stream, timeline)

    expected_month_12 = (
        base * (Decimal(1) + rate) ** (Decimal(12) / Decimal(12))
    ).quantize(Decimal("0.01"))
    assert series[0] == base.quantize(Decimal("0.01"))
    assert series[12] == expected_month_12


def test_window_entirely_in_past_returns_all_zero() -> None:
    timeline = _timeline()
    stream = TimedStream(
        monthly_amount=Decimal("100.00"),
        start=CalendarMonthBoundary(year=2000, month=1),
        end=CalendarMonthBoundary(year=2001, month=1),
    )

    series = project_stream(stream, timeline)

    assert len(series) == timeline.horizon_months
    assert all(value == Decimal("0.00") for value in series)

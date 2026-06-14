from __future__ import annotations

from decimal import Decimal

from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, TimedStream


def test_manual_income_streams_round_trip_through_sqlite(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_amount = Decimal("2500.00")
    expected_growth = Decimal("0.02")
    age_months = 900
    plan.manual_income_streams = [
        TimedStream(
            label="Rental",
            monthly_amount=expected_amount,
            start=CalendarMonthBoundary(year=2030, month=6),
            end=PersonAgeBoundary(person="person2", age_months=age_months),
            is_nominal=True,
            annual_growth_rate=expected_growth,
        )
    ]

    repo.save(plan_id, plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert len(loaded.manual_income_streams) == 1
    stream = loaded.manual_income_streams[0]
    assert stream.monthly_amount == expected_amount
    assert stream.annual_growth_rate == expected_growth
    assert stream.is_nominal is True
    assert isinstance(stream.start, CalendarMonthBoundary)
    assert isinstance(stream.end, PersonAgeBoundary)
    assert stream.end.age_months == age_months

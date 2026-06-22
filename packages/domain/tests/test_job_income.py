from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline, add_months, project_stream
from domain.job_income.compile import project_job_gross


def _timeline() -> Timeline:
    return Timeline(default_plan(), today=date(2026, 1, 1))


def test_single_job_matches_growth_curve() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    rate = Decimal("0.12")
    job = Job(annual_income=annual_income, annual_raise=rate)

    gross = project_job_gross(job, timeline)

    reference = project_stream(
        TimedStream(
            monthly_amount=annual_income / Decimal(12), annual_growth_rate=rate
        ),
        timeline,
    )
    assert gross == reference


def test_full_break_zeroes_window_and_resumes_on_curve() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    rate = Decimal("0.12")
    break_start_index = 12
    break_end_index = 23
    resume_index = break_end_index + 1
    start_y, start_m = add_months(
        timeline.today.year, timeline.today.month, break_start_index
    )
    end_y, end_m = add_months(
        timeline.today.year, timeline.today.month, break_end_index
    )
    job = Job(
        annual_income=annual_income,
        annual_raise=rate,
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=start_y, month=start_m),
                end=CalendarMonthBoundary(year=end_y, month=end_m),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    gross = project_job_gross(job, timeline)

    no_break = project_job_gross(
        Job(annual_income=annual_income, annual_raise=rate), timeline
    )
    assert gross[break_start_index] == Decimal("0.00")
    assert gross[break_end_index] == Decimal("0.00")
    assert gross[resume_index] == no_break[resume_index]


def test_partial_reduction_scales_window() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    remaining = Decimal("0.5")
    window_index = 6
    win_y, win_m = add_months(timeline.today.year, timeline.today.month, window_index)
    job = Job(
        annual_income=annual_income,
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=win_y, month=win_m),
                end=CalendarMonthBoundary(year=win_y, month=win_m),
                remaining_fraction=remaining,
            )
        ],
    )

    gross = project_job_gross(job, timeline)

    full_monthly = (annual_income / Decimal(12)).quantize(Decimal("0.01"))
    assert gross[window_index] == (full_monthly * remaining).quantize(Decimal("0.01"))

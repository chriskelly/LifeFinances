from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline, add_months, project_stream
from domain.job_income import project_job_income
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


def _plan_with_jobs(person1_jobs: list[Job], person2_jobs: list[Job]) -> Plan:
    base = default_plan()
    base_person2 = base.household.person2
    assert base_person2 is not None
    return Plan(
        name=base.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=base.household.person1.birth_month,
                birth_year=base.household.person1.birth_year,
                max_age_years=base.household.person1.max_age_years,
                jobs=person1_jobs,
            ),
            person2=PersonHousehold(
                birth_month=base_person2.birth_month,
                birth_year=base_person2.birth_year,
                max_age_years=base_person2.max_age_years,
                jobs=person2_jobs,
            ),
        ),
        portfolio=base.portfolio,
    )


def test_concurrent_jobs_sum_per_person() -> None:
    timeline = _timeline()
    income_a = Decimal("60000")
    income_b = Decimal("36000")
    plan = _plan_with_jobs(
        [Job(annual_income=income_a), Job(annual_income=income_b)], []
    )

    projection = project_job_income(plan, timeline)

    expected_month0 = (income_a / Decimal(12) + income_b / Decimal(12)).quantize(
        Decimal("0.01")
    )
    assert projection.person1.gross[0] == expected_month0


def test_non_ss_covered_job_excluded_from_ss_series() -> None:
    timeline = _timeline()
    covered = Decimal("60000")
    uncovered = Decimal("48000")
    plan = _plan_with_jobs(
        [
            Job(annual_income=covered, social_security_eligible=True),
            Job(annual_income=uncovered, social_security_eligible=False),
        ],
        [],
    )

    projection = project_job_income(plan, timeline)

    assert projection.person1.gross[0] == (
        covered / Decimal(12) + uncovered / Decimal(12)
    ).quantize(Decimal("0.01"))
    assert projection.person1.ss_covered_gross[0] == (covered / Decimal(12)).quantize(
        Decimal("0.01")
    )


def test_tax_deferred_scales_with_income_fraction() -> None:
    timeline = _timeline()
    income = Decimal("100000")
    deferred = Decimal("20000")
    plan = _plan_with_jobs(
        [Job(annual_income=income, annual_tax_deferred=deferred)], []
    )

    projection = project_job_income(plan, timeline)

    fraction = deferred / income
    expected = ((income / Decimal(12)).quantize(Decimal("0.01")) * fraction).quantize(
        Decimal("0.01")
    )
    assert projection.person1.tax_deferred[0] == expected


def test_zero_income_job_has_zero_tax_deferred() -> None:
    timeline = _timeline()
    plan = _plan_with_jobs([Job(annual_income=Decimal("0"))], [])

    projection = project_job_income(plan, timeline)

    assert all(value == Decimal("0.00") for value in projection.person1.tax_deferred)


def test_household_totals_equal_sum_of_persons() -> None:
    timeline = _timeline()
    income1 = Decimal("90000")
    income2 = Decimal("72000")
    plan = _plan_with_jobs([Job(annual_income=income1)], [Job(annual_income=income2)])

    projection = project_job_income(plan, timeline)

    person2_projection = projection.person2
    assert person2_projection is not None
    assert projection.total_gross[0] == (
        projection.person1.gross[0] + person2_projection.gross[0]
    )

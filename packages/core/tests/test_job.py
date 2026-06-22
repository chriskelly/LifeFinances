from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.job import Job, SabbaticalWindow
from core.models import Household, PersonHousehold
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from pydantic import ValidationError


def _household_with_person1_jobs(jobs: list[Job]) -> Household:
    return Household(
        person1=PersonHousehold(birth_month=1, birth_year=1980, jobs=jobs),
        person2=PersonHousehold(birth_month=1, birth_year=1982),
    )


def test_job_rejects_tax_deferred_above_income() -> None:
    income = Decimal("100000")
    too_much_deferred = income + Decimal("1")

    with pytest.raises(ValidationError):
        Job(annual_income=income, annual_tax_deferred=too_much_deferred)


def test_job_allows_tax_deferred_equal_to_income() -> None:
    income = Decimal("100000")

    job = Job(annual_income=income, annual_tax_deferred=income)

    assert job.annual_tax_deferred == income


def test_plan_with_jobs_round_trips_through_repository(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    annual_income = Decimal("120000")
    job = Job(
        label="Engineer",
        annual_income=annual_income,
        annual_tax_deferred=Decimal("23000"),
        annual_raise=Decimal("0.03"),
        end=CalendarMonthBoundary(year=date.today().year + 30, month=1),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=date.today().year + 5, month=1),
                end=CalendarMonthBoundary(year=date.today().year + 5, month=12),
                remaining_fraction=Decimal("0.5"),
            )
        ],
    )
    plan.household.person1.jobs.append(job)

    repo.save(plan_id, plan)
    reloaded = repo.get_by_id(plan_id)

    assert reloaded is not None
    assert reloaded.household.person1.jobs == plan.household.person1.jobs
    assert reloaded.household.person1.jobs[0].annual_income == annual_income


def test_overlapping_sabbatical_windows_rejected() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=1),
                end=CalendarMonthBoundary(year=2030, month=6),
                remaining_fraction=Decimal("0.5"),
            ),
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=6),
                end=CalendarMonthBoundary(year=2030, month=12),
                remaining_fraction=Decimal("0"),
            ),
        ],
    )

    with pytest.raises(ValidationError):
        _household_with_person1_jobs([job])


def test_window_outside_explicit_job_bounds_rejected() -> None:
    job_start_year = 2030
    job = Job(
        annual_income=Decimal("100000"),
        start=CalendarMonthBoundary(year=job_start_year, month=1),
        end=CalendarMonthBoundary(year=job_start_year + 5, month=12),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=job_start_year - 1, month=1),
                end=CalendarMonthBoundary(year=job_start_year - 1, month=6),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    with pytest.raises(ValidationError):
        _household_with_person1_jobs([job])


def test_window_against_open_bound_is_accepted() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=PersonAgeBoundary(person="person1", age_months=720),
                end=PersonAgeBoundary(person="person1", age_months=732),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    household = _household_with_person1_jobs([job])

    assert household.person1.jobs[0].sabbaticals[0].remaining_fraction == Decimal("0")


def test_cross_person_and_mixed_boundary_kinds_resolve() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=1),
                end=PersonAgeBoundary(person="person2", age_months=720),
                remaining_fraction=Decimal("0.5"),
            )
        ],
    )

    household = _household_with_person1_jobs([job])

    assert len(household.person1.jobs[0].sabbaticals) == 1

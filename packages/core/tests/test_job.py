from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.job import Job, SabbaticalWindow
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary
from pydantic import ValidationError


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

"""Job income: compile jobs into projected monthly cashflow series."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from core.models import PersonHousehold, Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income.compile import project_job_gross

_CENTS = Decimal("0.01")


def _add(left: list[Decimal], right: list[Decimal]) -> list[Decimal]:
    return [a + b for a, b in zip(left, right, strict=True)]


class PersonJobIncome(BaseModel):
    gross: list[Decimal]
    ss_covered_gross: list[Decimal]
    tax_deferred: list[Decimal]


class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome
    total_gross: list[Decimal]
    total_ss_covered_gross: list[Decimal]
    total_tax_deferred: list[Decimal]


def _project_person(person: PersonHousehold, timeline: Timeline) -> PersonJobIncome:
    horizon = timeline.horizon_months
    gross = [Decimal("0.00")] * horizon
    ss_covered = [Decimal("0.00")] * horizon
    tax_deferred = [Decimal("0.00")] * horizon
    for job in person.jobs:
        job_gross = project_job_gross(job, timeline)
        gross = _add(gross, job_gross)
        if job.social_security_eligible:
            ss_covered = _add(ss_covered, job_gross)
        if job.annual_income > 0:
            fraction = job.annual_tax_deferred / job.annual_income
            job_deferred = [
                (value * fraction).quantize(_CENTS, rounding=ROUND_HALF_UP)
                for value in job_gross
            ]
            tax_deferred = _add(tax_deferred, job_deferred)
    return PersonJobIncome(
        gross=gross, ss_covered_gross=ss_covered, tax_deferred=tax_deferred
    )


def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection:
    person1 = _project_person(plan.household.person1, timeline)
    person2 = _project_person(plan.household.person2, timeline)
    return JobIncomeProjection(
        person1=person1,
        person2=person2,
        total_gross=_add(person1.gross, person2.gross),
        total_ss_covered_gross=_add(person1.ss_covered_gross, person2.ss_covered_gross),
        total_tax_deferred=_add(person1.tax_deferred, person2.tax_deferred),
    )

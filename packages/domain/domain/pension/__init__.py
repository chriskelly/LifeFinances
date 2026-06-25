from __future__ import annotations

from decimal import Decimal

from core.job import Job
from core.models import Household, PersonHousehold, Plan
from core.streams import TimedStream
from core.timeline import Timeline, project_stream
from pydantic import BaseModel

from domain.job_income import JobIncomeProjection
from domain.pension.formula import (
    claim_age_months,
    final_compensation,
    interpolate_age_factor,
    service_credit_years,
)

_MONTHS_PER_YEAR = Decimal(12)


class PensionProjection(BaseModel):
    formula: list[Decimal]
    manual: list[Decimal]
    stored_total: list[Decimal]  # formula + manual; snapshot at projection time


def _formula_benefit_series(
    *, job: Job, person: PersonHousehold, household: Household, timeline: Timeline
) -> list[Decimal]:
    pension = job.pension
    assert pension is not None
    if not pension.age_factor_table:
        raise ValueError("empty age_factor_table")
    credit = service_credit_years(job=job, timeline=timeline)
    final_comp = final_compensation(job=job, timeline=timeline)
    age = claim_age_months(person=person, claim=pension.claim, household=household)
    factor = interpolate_age_factor(pension.age_factor_table, age)
    annual_benefit = credit * factor * final_comp
    monthly = annual_benefit / _MONTHS_PER_YEAR * pension.trust_factor
    if monthly < 0:
        monthly = Decimal(0)
    stream = TimedStream(
        monthly_amount=monthly,
        start=pension.claim,
        annual_growth_rate=pension.benefit_real_growth_rate,
    )
    return project_stream(stream, timeline)


def project_pension(
    plan: Plan, timeline: Timeline, job_income: JobIncomeProjection
) -> PensionProjection:
    horizon = timeline.horizon_months
    formula = [Decimal("0.00")] * horizon
    household = plan.household
    for person in (household.person1, household.person2):
        for job in person.jobs:
            if job.pension is None:
                continue
            series = _formula_benefit_series(
                job=job, person=person, household=household, timeline=timeline
            )
            formula = [a + b for a, b in zip(formula, series, strict=True)]
    manual = [Decimal("0.00")] * horizon
    for stream in plan.manual_income_streams:
        projected = project_stream(stream, timeline)
        manual = [a + b for a, b in zip(manual, projected, strict=True)]
    stored_total = [f + m for f, m in zip(formula, manual, strict=True)]
    return PensionProjection(formula=formula, manual=manual, stored_total=stored_total)

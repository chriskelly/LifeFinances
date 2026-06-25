from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor, Job
from core.models import Household, PersonHousehold
from core.streams import Boundary
from core.timeline import Timeline, boundary_to_year_month

from domain.job_income.compile import project_job_gross

_MONTHS_PER_YEAR = Decimal(12)


def _absolute_month(boundary: Boundary, household: Household) -> int:
    year, month = boundary_to_year_month(boundary, household)
    return year * 12 + month


def service_credit_years(*, job: Job, timeline: Timeline) -> Decimal:
    if job.pension is None:
        raise ValueError("service_credit_years requires a job with a formula pension")
    if job.end is None:
        raise ValueError("formula pension requires a job end boundary")
    household = timeline.plan.household
    start_abs = _absolute_month(job.pension.service_start, household)
    end_abs = _absolute_month(job.end, household)
    gross_months = end_abs - start_abs + 1
    loss_years = Decimal(0)
    for window in job.sabbaticals:
        window_months = (
            _absolute_month(window.end, household)
            - _absolute_month(window.start, household)
            + 1
        )
        loss_years += (Decimal(1) - window.remaining_fraction) * (
            Decimal(window_months) / _MONTHS_PER_YEAR
        )
    return Decimal(gross_months) / _MONTHS_PER_YEAR - loss_years


def final_compensation(*, job: Job, timeline: Timeline) -> Decimal:
    if job.pension is None:
        raise ValueError("final_compensation requires a job with a formula pension")
    if job.end is None:
        raise ValueError("formula pension requires a job end boundary")
    horizon = timeline.horizon_months
    if horizon <= 0:
        return Decimal("0.00")
    gross = project_job_gross(job, timeline)
    end_index = min(max(timeline.index_of(job.end), 0), horizon - 1)
    averaging_months = job.pension.final_comp_averaging_months
    start_index = max(end_index - averaging_months + 1, 0)
    window = gross[start_index : end_index + 1]
    average_monthly = sum(window, Decimal(0)) / Decimal(len(window))
    return average_monthly * _MONTHS_PER_YEAR


def interpolate_age_factor(table: list[AgeFactor], age_months: int) -> Decimal:
    if not table:
        raise ValueError("empty age_factor_table")
    rows = sorted(table, key=lambda row: row.age_months)
    if age_months <= rows[0].age_months:
        return rows[0].factor
    if age_months >= rows[-1].age_months:
        return rows[-1].factor
    for lower, upper in zip(rows, rows[1:], strict=False):
        if lower.age_months <= age_months <= upper.age_months:
            span = upper.age_months - lower.age_months
            if span == 0:
                return lower.factor
            ratio = Decimal(age_months - lower.age_months) / Decimal(span)
            return lower.factor + (upper.factor - lower.factor) * ratio
    return rows[-1].factor


def claim_age_months(
    *, person: PersonHousehold, claim: Boundary, household: Household
) -> int:
    claim_year, claim_month = boundary_to_year_month(claim, household)
    return (claim_year - person.birth_year) * 12 + (claim_month - person.birth_month)

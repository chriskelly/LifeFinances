from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from core.models import Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income import JobIncomeProjection
from domain.pension import PensionProjection
from domain.social_security import SocialSecurityProjection
from domain.statutory.social_security import (
    SS_MAX_EARNINGS_BY_YEAR,
    statutory_value_for_year,
)
from domain.statutory.taxes import (
    FEDERAL_BRACKETS,
    FEDERAL_STANDARD_DEDUCTION,
    MEDICARE_TAX_RATE,
    SOCIAL_SECURITY_TAX_RATE,
    STATE_BRACKETS,
    STATE_STANDARD_DEDUCTION,
)
from domain.taxes.brackets import annual_income_tax

_CENTS = Decimal("0.01")


class TaxBreakdown(BaseModel):
    federal_income: list[Decimal]
    state_income: list[Decimal]
    fica_medicare: list[Decimal]
    fica_social_security: list[Decimal]
    stored_total: list[Decimal]  # sum of components; snapshot at compute time


def _indices_by_year(timeline: Timeline) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for month_index in range(timeline.horizon_months):
        year = timeline.month_boundary(month_index).year
        grouped.setdefault(year, []).append(month_index)
    return grouped


def _fica_social_security(
    job_income: JobIncomeProjection, timeline: Timeline
) -> list[Decimal]:
    horizon = timeline.horizon_months
    wage_base = statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, timeline.today.year)
    person_series = (
        job_income.person1.ss_covered_gross,
        job_income.person2.ss_covered_gross,
    )
    series = [Decimal("0.00")] * horizon
    cumulative: dict[tuple[int, int], Decimal] = {}
    for month_index in range(horizon):
        year = timeline.month_boundary(month_index).year
        month_tax = Decimal(0)
        for person_idx, covered in enumerate(person_series):
            key = (person_idx, year)
            accrued = cumulative.get(key, Decimal(0))
            remaining = max(wage_base - accrued, Decimal(0))
            taxable = min(covered[month_index], remaining)
            month_tax += SOCIAL_SECURITY_TAX_RATE * taxable
            cumulative[key] = accrued + covered[month_index]
        series[month_index] = -month_tax.quantize(_CENTS, rounding=ROUND_HALF_UP)
    return series


def compute_taxes(
    *,
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
    social_security: SocialSecurityProjection,
    pension: PensionProjection,
) -> TaxBreakdown:
    horizon = timeline.horizon_months
    if horizon <= 0:
        return TaxBreakdown(
            federal_income=[],
            state_income=[],
            fica_medicare=[],
            fica_social_security=[],
            stored_total=[],
        )

    household = plan.household
    filing = household.filing_status
    ss_pension_fraction = household.ss_pension_taxable_fraction
    state = household.residence_state

    job_taxable = [
        gross - deferred
        for gross, deferred in zip(
            job_income.total_gross, job_income.total_tax_deferred, strict=True
        )
    ]
    total_taxable = [
        job_taxable[m]
        + (social_security.total[m] + pension.stored_total[m]) * ss_pension_fraction
        for m in range(horizon)
    ]

    fed_brackets = FEDERAL_BRACKETS[filing]
    fed_deduction = FEDERAL_STANDARD_DEDUCTION[filing]
    state_brackets = STATE_BRACKETS.get(state, {}).get(filing) if state else None
    state_deduction = (
        STATE_STANDARD_DEDUCTION.get(state, {}).get(filing, Decimal(0))
        if state
        else Decimal(0)
    )

    federal = [Decimal("0.00")] * horizon
    state_income = [Decimal("0.00")] * horizon
    for indices in _indices_by_year(timeline).values():
        year_taxable = sum((total_taxable[m] for m in indices), Decimal(0))
        if year_taxable <= 0:
            continue
        year_federal = annual_income_tax(
            brackets=fed_brackets,
            standard_deduction=fed_deduction,
            annual_income=year_taxable,
        )
        year_state = (
            annual_income_tax(
                brackets=state_brackets,
                standard_deduction=state_deduction,
                annual_income=year_taxable,
            )
            if state_brackets is not None
            else Decimal("0.00")
        )
        for month_index in indices:
            share = total_taxable[month_index] / year_taxable
            federal[month_index] = -(year_federal * share).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )
            state_income[month_index] = -(year_state * share).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )

    medicare = [
        -(MEDICARE_TAX_RATE * gross).quantize(_CENTS, rounding=ROUND_HALF_UP)
        for gross in job_income.total_gross
    ]
    fica_social_security = _fica_social_security(job_income, timeline)
    stored_total = [
        f + s + m + ss
        for f, s, m, ss in zip(
            federal, state_income, medicare, fica_social_security, strict=True
        )
    ]

    return TaxBreakdown(
        federal_income=federal,
        state_income=state_income,
        fica_medicare=medicare,
        fica_social_security=fica_social_security,
        stored_total=stored_total,
    )

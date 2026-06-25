"""Income, pension, Social Security, and tax domain logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.models import Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income import project_job_income
from domain.pension import project_pension
from domain.social_security import project_social_security
from domain.taxes import TaxBreakdown, compute_taxes


class MonthlyCashflows(BaseModel):
    gross_job: list[Decimal]
    gross_social_security: list[Decimal]
    gross_pension: list[Decimal]
    gross_manual: list[Decimal]
    total_gross: list[Decimal]
    taxes: TaxBreakdown
    net_cashflow: list[Decimal]


def build_monthly_cashflows(
    plan: Plan, *, today: date | None = None
) -> MonthlyCashflows:
    timeline = Timeline(plan, today=today)
    job_income = project_job_income(plan, timeline)
    social_security = project_social_security(plan, timeline, job_income)
    pension = project_pension(plan, timeline, job_income)
    taxes = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=social_security,
        pension=pension,
    )

    gross_job = job_income.total_gross
    gross_social_security = social_security.total
    gross_pension = pension.formula
    gross_manual = pension.manual
    total_gross = [
        gross_job[m] + gross_social_security[m] + gross_pension[m] + gross_manual[m]
        for m in range(timeline.horizon_months)
    ]
    net_cashflow = [
        total + tax for total, tax in zip(total_gross, taxes.stored_total, strict=True)
    ]

    return MonthlyCashflows(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        total_gross=total_gross,
        taxes=taxes,
        net_cashflow=net_cashflow,
    )

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from core.streams import Boundary


class SabbaticalWindow(BaseModel):
    start: Boundary
    end: Boundary
    remaining_fraction: Decimal = Field(ge=0, le=1)


class AgeFactor(BaseModel):
    """Defined-benefit age factor at a given age."""

    age_months: int = Field(ge=0)
    factor: Decimal = Field(ge=0)


class FormulaPension(BaseModel):
    """Defined-benefit pension formula attached to a job.

    Benefit = service_credit_years x age_factor x final_compensation.
    All dollar amounts are real today's dollars; inflation is applied by the
    simulation layer on the projected benefit stream.
    """

    service_start: Boundary
    claim: Boundary
    age_factor_table: list[AgeFactor]
    final_comp_averaging_months: int = Field(default=36, ge=1)
    trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    benefit_real_growth_rate: Decimal = Decimal(0)


class Job(BaseModel):
    label: str | None = None
    annual_income: Decimal = Field(ge=0)
    annual_tax_deferred: Decimal = Field(default=Decimal(0), ge=0)
    annual_raise: Decimal = Decimal(0)
    start: Boundary | None = None
    end: Boundary | None = None
    social_security_eligible: bool = True
    sabbaticals: list[SabbaticalWindow] = Field(default_factory=list)
    pension: FormulaPension | None = None

    @model_validator(mode="after")
    def _tax_deferred_within_income(self) -> Job:
        if self.annual_tax_deferred > self.annual_income:
            raise ValueError("annual_tax_deferred must not exceed annual_income")
        return self

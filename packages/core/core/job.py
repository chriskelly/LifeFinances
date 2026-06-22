from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from core.streams import Boundary


class SabbaticalWindow(BaseModel):
    start: Boundary
    end: Boundary
    remaining_fraction: Decimal = Field(ge=0, le=1)


class Job(BaseModel):
    label: str | None = None
    annual_income: Decimal = Field(ge=0)
    annual_tax_deferred: Decimal = Field(default=Decimal(0), ge=0)
    annual_raise: Decimal = Decimal(0)
    start: Boundary | None = None
    end: Boundary | None = None
    social_security_eligible: bool = True
    sabbaticals: list[SabbaticalWindow] = Field(default_factory=list)

    @model_validator(mode="after")
    def _tax_deferred_within_income(self) -> Job:
        if self.annual_tax_deferred > self.annual_income:
            raise ValueError("annual_tax_deferred must not exceed annual_income")
        return self

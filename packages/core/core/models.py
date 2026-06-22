from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from core.job import Job
from core.streams import TimedStream


class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold


class Portfolio(BaseModel):
    current_savings_balance: Decimal = Field(ge=0)


class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    manual_income_streams: list[TimedStream] = Field(default_factory=list)

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.job import Job
from core.social_security import PersonSocialSecurityConfig
from core.streams import TimedStream
from core.timeline import boundary_to_year_month

FilingStatus = Literal["married_filing_jointly", "single"]


def _validate_job_windows(job: Job, household: Household) -> None:
    def absolute(boundary) -> int:
        year, month = boundary_to_year_month(boundary, household)
        return year * 12 + month

    low = absolute(job.start) if job.start is not None else None
    high = absolute(job.end) if job.end is not None else None

    previous_end: int | None = None
    for window in job.sabbaticals:
        start = absolute(window.start)
        end = absolute(window.end)
        if start > end:
            raise ValueError("sabbatical window start must not be after its end")
        if low is not None and start < low:
            raise ValueError("sabbatical window starts before the job's start")
        if high is not None and end > high:
            raise ValueError("sabbatical window ends after the job's end")
        if previous_end is not None and start <= previous_end:
            raise ValueError("sabbatical windows must be ordered and non-overlapping")
        previous_end = end


class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)
    social_security: PersonSocialSecurityConfig = Field(
        default_factory=PersonSocialSecurityConfig
    )


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus = "married_filing_jointly"
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> Household:
        for person in (self.person1, self.person2):
            for job in person.jobs:
                _validate_job_windows(job, self)
        return self


class Portfolio(BaseModel):
    current_savings_balance: Decimal = Field(ge=0)


class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    manual_income_streams: list[TimedStream] = Field(default_factory=list)

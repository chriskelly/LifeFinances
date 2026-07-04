from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from core.job import Job
from core.social_security import PersonSocialSecurityConfig
from core.streams import TimedStream
from core.timeline import boundary_to_year_month

FilingStatus = Literal["married_filing_jointly", "single"]

DEFAULT_BLOCK_SIZE_MONTHS = 60  # tpaw blockSize.inMonths = 12 * 5
DEFAULT_NUM_RUNS = 500  # tpaw numOfSimulationForMonteCarloSampling
DEFAULT_STAGGER_RUN_STARTS = True  # tpaw staggerRunStarts
DEFAULT_SAMPLING_SEED = 1_234_567  # LifeFinances default for reproducibility

DEFAULT_RISK_TOLERANCE_AT_20 = Decimal(12)  # tpaw default test plan "Moderate"
DEFAULT_DELTA_AT_MAX_AGE = Decimal(0)
DEFAULT_LEGACY_DELTA_FROM_AT_20 = Decimal(0)
DEFAULT_TIME_PREFERENCE = Decimal(0)
DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT = Decimal(0)

# Pinned tpaw risk-tolerance -> RRA scale constants. Not user-editable.
RISK_TOLERANCE_NUM_VALUES = 25
RISK_TOLERANCE_START_RRA = 16.0
RISK_TOLERANCE_END_RRA = 0.5

DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS = Decimal("0.05")
DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS = Decimal("0.02")


class AppSettings(BaseModel):
    fred_api_key: str | None = None
    eod_api_key: str | None = None

    @field_validator("fred_api_key", "eod_api_key", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class SamplingConfig(BaseModel):
    block_size_months: int = Field(default=DEFAULT_BLOCK_SIZE_MONTHS, ge=1)
    num_runs: int = Field(default=DEFAULT_NUM_RUNS, ge=1)
    stagger_run_starts: bool = DEFAULT_STAGGER_RUN_STARTS
    seed: int = DEFAULT_SAMPLING_SEED


class InflationConfig(BaseModel):
    mode: Literal["suggested", "manual"] = "suggested"
    manual_annual_rate: Decimal | None = None

    @model_validator(mode="after")
    def _require_manual_rate(self) -> InflationConfig:
        if self.mode == "manual" and self.manual_annual_rate is None:
            raise ValueError("manual_annual_rate is required when mode == 'manual'")
        return self


class RiskConfig(BaseModel):
    risk_tolerance_at_20: Decimal = Field(default=DEFAULT_RISK_TOLERANCE_AT_20, ge=0)
    delta_at_max_age: Decimal = DEFAULT_DELTA_AT_MAX_AGE
    legacy_delta_from_at_20: Decimal = DEFAULT_LEGACY_DELTA_FROM_AT_20
    time_preference: Decimal = DEFAULT_TIME_PREFERENCE
    additional_annual_spending_tilt: Decimal = DEFAULT_ADDITIONAL_ANNUAL_SPENDING_TILT


class PlanningReturnsConfig(BaseModel):
    expected_annual_return_stocks: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS
    expected_annual_return_bonds: Decimal = DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS


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
    person2: PersonHousehold | None = None
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus | None = None
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)

    @property
    def people(self) -> tuple[PersonHousehold, ...]:
        if self.person2 is None:
            return (self.person1,)
        return (self.person1, self.person2)

    @property
    def resolved_filing_status(self) -> FilingStatus:
        if self.filing_status is not None:
            return self.filing_status
        return "single" if self.person2 is None else "married_filing_jointly"

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> Household:
        for person in self.people:
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
    sampling: SamplingConfig = Field(default_factory=SamplingConfig)
    inflation: InflationConfig = Field(default_factory=InflationConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    planning_returns: PlanningReturnsConfig = Field(
        default_factory=PlanningReturnsConfig
    )
    extra_essential_spending: list[TimedStream] = Field(default_factory=list)
    extra_discretionary_spending: list[TimedStream] = Field(default_factory=list)
    # Interpreted as already-real (today's dollars) by the simulation engine —
    # unlike every other spending/income stream on this model, it is NOT
    # inflation-adjusted before being discounted.
    legacy_target: Decimal = Field(default=Decimal(0), ge=0)

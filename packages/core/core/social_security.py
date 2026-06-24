from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

MIN_CLAIM_AGE_MONTHS = 62 * 12
FULL_RETIREMENT_AGE_MONTHS = 67 * 12
MAX_CLAIM_AGE_MONTHS = 70 * 12


class AnnualEarnings(BaseModel):
    """One SSA historical annual FICA earnings row."""

    year: int
    fica_earnings: Decimal = Field(ge=0)


class PersonSocialSecurityConfig(BaseModel):
    """Per-person Social Security calculation inputs."""

    claim_age_months: int = Field(
        default=FULL_RETIREMENT_AGE_MONTHS,
        ge=MIN_CLAIM_AGE_MONTHS,
        le=MAX_CLAIM_AGE_MONTHS,
    )
    earnings_record: list[AnnualEarnings] = Field(default_factory=list)

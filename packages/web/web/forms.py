from __future__ import annotations

from decimal import Decimal
from typing import get_args

from core.models import (
    AppSettings,
    FilingStatus,
    Household,
    PersonHousehold,
    Plan,
    Portfolio,
)
from pydantic import BaseModel

# Field-name constants for templates/tests — must match DTO field names
PERSON1_BIRTH_MONTH = "person1_birth_month"
PERSON1_BIRTH_YEAR = "person1_birth_year"
PERSON1_MAX_AGE_YEARS = "person1_max_age_years"
PERSON2_BIRTH_MONTH = "person2_birth_month"
PERSON2_BIRTH_YEAR = "person2_birth_year"
PERSON2_MAX_AGE_YEARS = "person2_max_age_years"
HAS_PARTNER = "has_partner"
FILING_STATUS = "filing_status"
RESIDENCE_STATE = "residence_state"
SS_PENSION_TAXABLE_FRACTION = "ss_pension_taxable_fraction"
SOCIAL_SECURITY_TRUST_FACTOR = "social_security_trust_factor"

FILING_STATUSES: tuple[FilingStatus, ...] = get_args(FilingStatus)
FILING_STATUS_LABELS = {
    "single": "Single",
    "married_filing_jointly": "Married filing jointly",
}
CURRENT_SAVINGS_BALANCE = "current_savings_balance"
FRED_API_KEY = "fred_api_key"
CLEAR_FRED_API_KEY = "clear_fred_api_key"
EOD_API_KEY = "eod_api_key"
CLEAR_EOD_API_KEY = "clear_eod_api_key"
PLAN_NAME = "name"
RETURN_PLAN = "return_plan"


class HouseholdForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    filing_status: FilingStatus
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Decimal("0.80")
    social_security_trust_factor: Decimal = Decimal(1)
    has_partner: bool = False
    person2_birth_month: int | None = None
    person2_birth_year: int | None = None
    person2_max_age_years: int | None = None

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        data["person1"].update(
            {
                "birth_month": self.person1_birth_month,
                "birth_year": self.person1_birth_year,
                "max_age_years": self.person1_max_age_years,
            }
        )
        if self.has_partner:
            existing2 = data.get("person2")
            if existing2 is None:
                existing2 = PersonHousehold(
                    birth_month=self.person2_birth_month or 1,
                    birth_year=self.person2_birth_year or 0,
                    max_age_years=self.person2_max_age_years or 1,
                ).model_dump()
            existing2.update(
                {
                    "birth_month": self.person2_birth_month,
                    "birth_year": self.person2_birth_year,
                    "max_age_years": self.person2_max_age_years,
                }
            )
            data["person2"] = existing2
        else:
            data["person2"] = None
        data["filing_status"] = self.filing_status
        if self.residence_state is not None:
            data["residence_state"] = self.residence_state or None
        data["ss_pension_taxable_fraction"] = self.ss_pension_taxable_fraction
        data["social_security_trust_factor"] = self.social_security_trust_factor
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})


class PortfolioForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    current_savings_balance: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.portfolio.model_dump()
        data["current_savings_balance"] = self.current_savings_balance
        portfolio = Portfolio.model_validate(data)
        return plan.model_copy(update={"portfolio": portfolio})


def _apply_api_key(
    settings: AppSettings,
    *,
    field: str,
    value: str | None,
    clear: bool,
) -> AppSettings:
    if clear:
        return settings.model_copy(update={field: None})
    if value and value.strip():
        return settings.model_copy(update={field: value.strip()})
    return settings


class AppSettingsForm(BaseModel):
    """Flat transport DTO for local app settings."""

    fred_api_key: str | None = None
    clear_fred_api_key: bool = False
    eod_api_key: str | None = None
    clear_eod_api_key: bool = False

    def apply_to(self, settings: AppSettings) -> AppSettings:
        updated = _apply_api_key(
            settings,
            field="fred_api_key",
            value=self.fred_api_key,
            clear=self.clear_fred_api_key,
        )
        return _apply_api_key(
            updated,
            field="eod_api_key",
            value=self.eod_api_key,
            clear=self.clear_eod_api_key,
        )

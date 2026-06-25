from __future__ import annotations

from decimal import Decimal

from core.models import Household, PersonHousehold, Plan
from pydantic import BaseModel

# Field-name constants for templates/tests — must match DTO field names
PERSON1_BIRTH_MONTH = "person1_birth_month"
PERSON1_BIRTH_YEAR = "person1_birth_year"
PERSON1_MAX_AGE_YEARS = "person1_max_age_years"
PERSON2_BIRTH_MONTH = "person2_birth_month"
PERSON2_BIRTH_YEAR = "person2_birth_year"
PERSON2_MAX_AGE_YEARS = "person2_max_age_years"
HAS_PARTNER = "has_partner"
CURRENT_SAVINGS_BALANCE = "current_savings_balance"


class HouseholdForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    has_partner: bool = False
    person2_birth_month: int | None = None
    person2_birth_year: int | None = None
    person2_max_age_years: int | None = None

    def apply_to(self, plan: Plan) -> Plan:
        person2 = None
        if self.has_partner:
            person2 = PersonHousehold.model_validate(
                {
                    "birth_month": self.person2_birth_month,
                    "birth_year": self.person2_birth_year,
                    "max_age_years": self.person2_max_age_years,
                }
            )
        household = Household(
            person1=PersonHousehold(
                birth_month=self.person1_birth_month,
                birth_year=self.person1_birth_year,
                max_age_years=self.person1_max_age_years,
            ),
            person2=person2,
        )
        return plan.model_copy(update={"household": household})


class PortfolioForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    current_savings_balance: Decimal

    def apply_to(self, plan: Plan) -> Plan:
        portfolio = plan.portfolio.model_copy(
            update={"current_savings_balance": self.current_savings_balance}
        )
        return plan.model_copy(update={"portfolio": portfolio})

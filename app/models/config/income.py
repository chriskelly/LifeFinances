"""Income configuration classes"""

from pydantic import BaseModel, model_validator


class IncomeProfile(BaseModel):
    """
    Attributes
        starting_income (float)

        tax_deferred_income (float): Defaults to 0

        yearly_raise (float): Defaults to 0.3

        try_to_optimize (bool): Defaults to True

        social_security_eligible (bool): Defaults to True

        last_date (float)
    """

    starting_income: float
    tax_deferred_income: float = 0
    yearly_raise: float = 0.3
    try_to_optimize: bool = True
    social_security_eligible: bool = True
    last_date: float

    @model_validator(mode="after")
    def tax_deferred_income_less_than_starting_income(self):
        """Tax deferred income must be less than starting income"""
        if self.tax_deferred_income > self.starting_income:
            raise ValueError("Tax deferred income must be less than starting income")
        return self


def _income_profiles_in_order(income_profiles: list[IncomeProfile] | None):
    """Income profiles must be in order"""
    if income_profiles:
        for i in range(1, len(income_profiles)):
            if income_profiles[i].last_date < income_profiles[i - 1].last_date:
                raise ValueError("Income profiles must be in order")

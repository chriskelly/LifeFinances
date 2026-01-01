"""User and partner configuration classes"""

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo

from app.data import constants
from app.data.taxes import STATE_BRACKET_RATES
from app.models.config.admin import Admin
from app.models.config.benefits import SocialSecurity
from app.models.config.income import IncomeProfile, _income_profiles_in_order
from app.models.config.portfolio import Portfolio
from app.models.config.spending import Spending
from app.models.config.standalone_tools import (
    DisabilityInsuranceCalculator,
    TPAWPlanner,
)


class Partner(BaseModel):
    """
    Attributes
        age (int)

        social_security_pension (SocialSecurity): Defaults to default `SocialSecurity`

        income_profiles (list[IncomeProfile]): Defaults to None
    """

    age: int = Field(
        json_schema_extra={
            "ui": {
                "label": "Partner Age",
                "tooltip": "Current age of partner/spouse in years",
                "section": "Partner",
                "min_value": 18,
                "max_value": 100,
            }
        }
    )
    social_security_pension: SocialSecurity = Field(
        default_factory=SocialSecurity,
        json_schema_extra={
            "ui": {
                "label": "Partner Social Security",
                "tooltip": "Partner's Social Security benefit configuration and claiming strategy",
                "section": "Partner",
            }
        },
    )
    income_profiles: list[IncomeProfile] | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Partner Income Profiles",
                "tooltip": "List of income profiles over time for partner",
                "section": "Partner",
            }
        },
    )


class User(BaseModel):
    """
    Attributes
        age (int)

        trial_quantity (int): Defaults to 500

        calculate_til (float): Defaults to current year minus age plus 90

        net_worth_target (float): Defaults to None

        portfolio (Portfolio)

        social_security_pension (SocialSecurity): Defaults to default `SocialSecurity`

        spending (Spending)

        state (str): Defaults to None

        income_profiles (list[IncomeProfile]): Defaults to None

        partner (Partner): Defaults to None

        tpaw_planner (TPAWPlanner): Defaults to None

        admin (Admin): Defaults to None
    """

    age: int = Field(
        json_schema_extra={
            "ui": {
                "label": "Age",
                "tooltip": "Your current age in years",
                "section": "Basic Settings",
                "min_value": 18,
                "max_value": 100,
            }
        }
    )
    trial_quantity: int = Field(
        default=500,
        json_schema_extra={
            "ui": {
                "label": "Number of Trials",
                "tooltip": "Number of Monte Carlo simulation trials to run (default: 500)",
                "section": "Basic Settings",
                "min_value": 1,
                "max_value": 10000,
            }
        },
    )
    calculate_til: float = Field(
        default=None,  # pyright: ignore[reportAssignmentType] # field_validator will set this to a float
        json_schema_extra={
            "ui": {
                "label": "Calculate Until Year",
                "tooltip": "Year to calculate until (defaults to age 90)",
                "section": "Basic Settings",
                "min_value": 2020,
                "max_value": 2100,
            }
        },
    )
    net_worth_target: float | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Net Worth Target",
                "tooltip": "Target net worth threshold for certain strategies",
                "section": "Basic Settings",
                "min_value": 0,
            }
        },
    )
    portfolio: Portfolio = Field(
        json_schema_extra={
            "ui": {
                "label": "Portfolio",
                "tooltip": "Portfolio configuration including net worth and allocation strategy",
                "section": "Portfolio",
            }
        }
    )
    social_security_pension: SocialSecurity = Field(
        default_factory=SocialSecurity,
        json_schema_extra={
            "ui": {
                "label": "Social Security",
                "tooltip": "Social Security benefit configuration and claiming strategy",
                "section": "Social Security",
            }
        },
    )
    spending: Spending = Field(
        json_schema_extra={
            "ui": {
                "label": "Spending",
                "tooltip": "Spending profiles and strategy configuration",
                "section": "Spending",
            }
        }
    )
    state: str | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "State of Residence",
                "tooltip": "State for tax calculations (California or New York)",
                "section": "Basic Settings",
                "choices": ["California", "New York"],
            }
        },
    )
    income_profiles: list[IncomeProfile] | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Income Profiles",
                "tooltip": "List of income profiles over time",
                "section": "Income",
            }
        },
    )
    partner: Partner | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Partner",
                "tooltip": "Partner/spouse configuration",
                "section": "Partner",
            }
        },
    )
    tpaw_planner: TPAWPlanner = Field(
        default_factory=TPAWPlanner,
        json_schema_extra={
            "ui": {
                "label": "TPAW Planner",
                "tooltip": "Time-Path Adjusted Withdrawal planner configuration",
                "section": "TPAW",
            }
        },
    )
    disability_insurance_calculator: DisabilityInsuranceCalculator | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Disability Insurance",
                "tooltip": "Disability insurance coverage calculator",
                "section": "Insurance",
            }
        },
    )
    admin: Admin | None = Field(
        default=None,
        json_schema_extra={
            "ui": {
                "label": "Admin",
                "tooltip": "Administrative configuration including pension details",
                "section": "Admin",
            }
        },
    )

    @property
    def intervals_per_trial(self) -> int:
        """Returns the number of intervals per trial"""

        return int(
            (self.calculate_til - constants.TODAY_YR_QT) / constants.YEARS_PER_INTERVAL
        )

    @field_validator("calculate_til")
    @classmethod
    def set_calculate_til(cls, calculate_til, info: ValidationInfo):
        """Set calculate till to be current year minus age + 90 if not specified"""
        if calculate_til is None:
            return constants.TODAY_YR - info.data["age"] + 90
        return calculate_til

    @field_validator("state")
    @classmethod
    def state_supported(cls, state):
        """Class method for validating state is supported by taxes module"""
        if state not in STATE_BRACKET_RATES:
            raise ValueError(
                f"{state} is not supported. You can add it to data/taxes.py!"
            )
        return state

    @model_validator(mode="after")
    def validate_income_profiles(self):
        """Income profiles must be in order"""
        _income_profiles_in_order(self.income_profiles)
        partner = self.partner
        if partner and partner.income_profiles:
            _income_profiles_in_order(partner.income_profiles)
        return self

    @model_validator(mode="after")
    def default_calculate_til(self):
        """Set calculate till to be current year minus age + 90 if not specified"""
        if self.calculate_til is None:
            self.calculate_til = constants.TODAY_YR - self.age + 90
        return self

    @model_validator(mode="after")
    def social_security_same_strategy(self):
        """User cannot enable/choose `same` strategy and
        partner cannot enable other strategies if `same` is chosen"""
        social_security_pension = self.social_security_pension
        strategy = social_security_pension.strategy
        enabled_strategies = strategy.enabled_strategies
        if enabled_strategies and "same" in enabled_strategies:
            raise ValueError("`Same` strategy can only be enabled for partner")
        return self

    @model_validator(mode="after")
    def either_income_or_net_worth(self):
        """User should provide at least one income profile or net worth"""
        portfolio = self.portfolio
        partner = self.partner
        if (
            not self.income_profiles
            and not portfolio.current_net_worth
            and not (partner and partner.income_profiles)
        ):
            raise ValueError(
                "User must provide at least one income profile or net worth"
            )
        return self

    @model_validator(mode="after")
    def total_portfolio_strategy_compatibility(self):
        """Total portfolio strategy requires age-based benefit strategies to avoid circular dependencies"""
        portfolio = self.portfolio
        allocation_strategy = portfolio.allocation_strategy

        # Check if total_portfolio strategy is chosen
        chosen_strategy_name, _ = allocation_strategy.chosen_strategy
        if chosen_strategy_name != "total_portfolio":
            return self

        # Validate social security strategy
        ss_strategy = self.social_security_pension.strategy
        ss_chosen_strategy_name, _ = ss_strategy.chosen_strategy
        if ss_chosen_strategy_name not in ("early", "mid", "late"):
            raise ValueError(
                "When using total_portfolio allocation strategy, social security must use "
                "an age-based strategy (early, mid, or late), not net_worth-based. "
                f"Current strategy: {ss_chosen_strategy_name}"
            )

        # Validate pension strategy if admin/pension is configured
        if self.admin and self.admin.pension:
            pension_strategy = self.admin.pension.strategy
            pension_chosen_strategy_name, _ = pension_strategy.chosen_strategy
            if pension_chosen_strategy_name not in ("early", "mid", "late", "cash_out"):
                raise ValueError(
                    "When using total_portfolio allocation strategy, pension must use "
                    "an age-based strategy (early, mid, late) or cash_out, not net_worth-based. "
                    f"Current strategy: {pension_chosen_strategy_name}"
                )

        return self

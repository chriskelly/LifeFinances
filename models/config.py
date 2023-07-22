"""Config

Useful Pydantic documentation
    Required, optional, and nullable fields
        https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields
    V2 Validators
        
"""
# pylint: disable=no-self-argument # @field_validator are class methods
# pylint: disable=missing-class-docstring # many self-explanatory classes

from typing import Optional
import yaml
from pydantic import BaseModel, ValidationError, field_validator, Field
from pydantic_core.core_schema import FieldValidationInfo
from data.taxes import STATE_BRACKET_RATES

# TODO: from pydantic.json_schema import GenerateJsonSchema


class Strategy(BaseModel):
    enabled: bool = False
    chosen: bool = False

    @field_validator("chosen")
    def chosen_forces_enabled(cls, chosen, info: FieldValidationInfo):
        """Forces enabled to true if chosen is true

        Note: In strategy class, enabled has to be defined before chosen in order to access it.
        """
        if chosen:
            info.data["enabled"] = True
        return chosen


class StrategyOptions:
    @property
    def enabled_strategies(self) -> dict[str, Strategy]:
        """Dict of enabled strategies

        Returns:
            dict[str,Strategy]: {name of strategy: Strategy Object}
        """
        return {
            prop: strategy
            for (prop, strategy) in vars(self).items()
            if strategy and strategy.enabled
        }

    @property
    def chosen_strategy(self) -> tuple[str, Strategy]:
        """Strategy chosen by user

        Returns:
            tuple[str,Strategy]: (name of strategy, Strategy Object)
        """
        return next(
            (
                (prop, strategy)
                for (prop, strategy) in vars(self).items()
                if strategy and strategy.chosen
            ),
            None,
        )


class RealEstateStrategy(Strategy):
    equity_ratio: float


class FlatBondStrategy(Strategy):
    flat_bond_target: Optional[float] = None


class XMinusAgeStrategy(Strategy):
    x: Optional[int] = None


class BondTentStrategy(Strategy):
    start_allocation: Optional[float] = None
    start_date: Optional[float] = None
    peak_allocation: Optional[float] = None
    peak_date: Optional[float] = None
    end_allocation: Optional[float] = None
    end_date: Optional[float] = None


class LifeCycleStrategy(Strategy):
    equity_target: Optional[float] = None


class AllocationOptions(BaseModel, StrategyOptions):
    flat_bond: Optional[Strategy] = None
    x_minus_age: Optional[XMinusAgeStrategy] = None
    bond_tent: Optional[BondTentStrategy] = None
    life_cycle: Optional[LifeCycleStrategy] = None


class Portfolio(BaseModel):
    current_net_worth: float
    drawdown_tax_rate: float = 0.1
    real_estate: RealEstateStrategy = None
    annuities_instead_of_bonds: bool
    allocation_strategy: AllocationOptions


class NetWorthStrategy(Strategy):
    equity_target: Optional[float] = None


class SocialSecurityPensionOptions(BaseModel, StrategyOptions):
    early: Optional[Strategy] = None
    mid: Optional[Strategy] = None
    late: Optional[Strategy] = None
    net_worth: Optional[NetWorthStrategy] = None
    same: Optional[Strategy] = None


class SocialSecurityPension(BaseModel):
    trust_factor: Optional[float] = 1
    pension_eligible: bool = False
    strategy: SocialSecurityPensionOptions


class CeilFloorStrategy(Strategy):
    allowed_fluctuation: Optional[float] = None


class SpendingOptions(BaseModel, StrategyOptions):
    inflation_only: Optional[Strategy] = None
    ceil_floor: Optional[CeilFloorStrategy] = None


class Spending(BaseModel):
    yearly_amount: int
    spending_strategy: SpendingOptions
    retirement_change: float


class Kids(BaseModel):
    cost_of_kid: float
    birth_years: list[float]


class IncomeProfile(BaseModel):
    starting_income: float
    tax_deferred_income: float
    yearly_raise: float
    try_to_optimize: bool
    social_security_eligible: bool
    last_date: float


class Partner(BaseModel):
    age: int
    social_security_pension: SocialSecurityPension
    earnings_records: dict
    income_profiles: list[IncomeProfile]


class Admin(BaseModel):
    partner_pension_strategy: SocialSecurityPensionOptions


class User(BaseModel):
    age: int = Field(description="foo value of the response")
    calculate_til: float
    equity_target: Optional[float] = None
    portfolio: Portfolio
    social_security_pension: SocialSecurityPension
    spending: Spending
    state: Optional[str] = None
    kids: Optional[Kids] = None
    earnings_records: Optional[dict] = None
    income_profiles: list[IncomeProfile] = []
    partner: Optional[Partner] = None
    admin: Optional[Admin] = None

    @field_validator("state")
    def state_supported(cls, state):
        """Class method for validating state is supported by taxes module"""
        if state not in STATE_BRACKET_RATES:
            raise ValueError(
                f"{state} is not supported. You can add it to data/taxes.py!"
            )
        return state


# Populate the Python object from the YAML configuration
with open("config.yml", "r", encoding="utf-8") as file:
    yaml_content = yaml.safe_load(file)
try:
    config = User(**yaml_content)
except ValidationError as e:
    print(e)


def variable_override(obj, attr: str, override_value):
    """Iterate recursively through obj and replace attr with override_value

    Only replaces if not specified

    Args:
        obj (any)
        attr (str): the object attribute to be targeted
        override_value (any): the value to change the attribute to
    """
    if hasattr(obj, "__dict__"):
        for field_name, field_value in vars(obj).items():
            # Confirm attribute is part of obj, but is set
            # to default None (consequense of user not providing it in config)
            if field_name == attr and not field_value:
                setattr(obj, attr, override_value)
            else:
                variable_override(field_value, attr, override_value)


if config.equity_target:
    # config.equity_target is considered global
    # and overwrites any equity_target value left unspecified
    variable_override(config, "equity_target", config.equity_target)

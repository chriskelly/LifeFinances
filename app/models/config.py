"""Config

Useful Pydantic documentation
    Required, optional, and nullable fields
        https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields
    V2 Validators
        
"""
# pylint: disable=no-self-argument # @field_validator are class methods

from typing import Optional
import yaml
from pydantic import BaseModel, ValidationError, field_validator, validator
from pydantic_core.core_schema import FieldValidationInfo
from app.data.taxes import STATE_BRACKET_RATES
from app.data import constants


class Strategy(BaseModel):
    """
    Attributes
        enabled (bool)

        chosen (bool)
    """

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
    """
    Property class that implements the following properties:
        enabled_strategies (dict[str, Strategy])

        chosen_strategy (tuple[str, Strategy])
    """

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
    """
    Attributes
        equity_ratio (float)
    """

    equity_ratio: float


class RealEstateOptions(BaseModel, StrategyOptions):
    """
    Attributes
        include (RealEstateStrategy)

        dont_include (Strategy)
    """

    include: Optional[RealEstateStrategy] = None
    dont_include: Optional[Strategy] = None


class FlatBondStrategy(Strategy):
    """
    Attributes
        flat_bond_target (float)
    """

    flat_bond_target: Optional[float] = None


class XMinusAgeStrategy(Strategy):
    """
    Attributes
        x (int)
    """

    x: Optional[int] = None


class BondTentStrategy(Strategy):
    """
    Attributes
        start_allocation (float)

        start_date (float)

        peak_allocation (float)

        peak_date (float)

        end_allocation (float)

        end_date (float)
    """

    start_allocation: Optional[float] = None
    start_date: Optional[float] = None
    peak_allocation: Optional[float] = None
    peak_date: Optional[float] = None
    end_allocation: Optional[float] = None
    end_date: Optional[float] = None


class LifeCycleStrategy(Strategy):
    """
    Attributes
        equity_target (float)
    """

    equity_target: Optional[float] = None


class AllocationOptions(BaseModel, StrategyOptions):
    """
    Attributes
        flat_bond (FlatBondStrategy)

        x_minus_age (XMinusAgeStrategy)

        bond_tent (BondTentStrategy)

        life_cycle (LifeCycleStrategy)
    """

    flat_bond: Optional[FlatBondStrategy] = None
    x_minus_age: Optional[XMinusAgeStrategy] = None
    bond_tent: Optional[BondTentStrategy] = None
    life_cycle: Optional[LifeCycleStrategy] = None


class Portfolio(BaseModel):
    """
    Attributes
        current_net_worth (float)

        drawdown_tax_rate (float)

        real_estate (RealEstateStrategy)

        annuities_instead_of_bonds (bool)

        allocation_strategy (AllocationOptions)
    """

    current_net_worth: float = 0
    drawdown_tax_rate: float = 0.1
    real_estate: RealEstateOptions = None
    annuities_instead_of_bonds: bool = False
    allocation_strategy: AllocationOptions = AllocationOptions(
        flat_bond=FlatBondStrategy(flat_bond_target=0.4, chosen=True),
    )


class NetWorthStrategy(Strategy):
    """
    Attributes
        equity_target (float)
    """

    equity_target: Optional[float] = None


class SocialSecurityPensionOptions(BaseModel, StrategyOptions):
    """
    Attributes
        early (Strategy)

        mid (Strategy)

        late (Strategy)

        net_worth (NetWorthStrategy)

        same (Strategy)
    """

    early: Optional[Strategy] = None
    mid: Optional[Strategy] = None
    late: Optional[Strategy] = None
    net_worth: Optional[NetWorthStrategy] = None
    same: Optional[Strategy] = None


class SocialSecurityPension(BaseModel):
    """
    Attributes
        trust_factor (float)

        pension_eligible (bool)

        strategy (SocialSecurityPensionOptions)
    """

    trust_factor: Optional[float] = 1
    pension_eligible: bool = False
    strategy: SocialSecurityPensionOptions


class CeilFloorStrategy(Strategy):
    """
    Attributes
        allowed_fluctuation (float)
    """

    allowed_fluctuation: Optional[float] = None


class SpendingOptions(BaseModel, StrategyOptions):
    """
    Attributes
        inflation_only (Strategy)

        ceil_floor (CeilFloorStrategy)
    """

    inflation_only: Optional[Strategy] = None
    ceil_floor: Optional[CeilFloorStrategy] = None


class Spending(BaseModel):
    """
    Attributes
        yearly_amount (int)

        spending_strategy (SpendingOptions)

        retirement_change (float)
    """

    yearly_amount: int
    spending_strategy: SpendingOptions = SpendingOptions(
        inflation_only=Strategy(chosen=True)
    )
    retirement_change: float = 0


class Kids(BaseModel):
    """
    Attributes
        cost_of_kid (float)

        birth_years (list[float])
    """

    cost_of_kid: float
    birth_years: list[float]


class IncomeProfile(BaseModel):
    """
    Attributes
        starting_income (float)

        tax_deferred_income (float)

        yearly_raise (float)

        try_to_optimize (bool)

        social_security_eligible (bool)

        last_date (float)
    """

    starting_income: float
    tax_deferred_income: float = 0
    yearly_raise: float = 0.3
    try_to_optimize: bool = True
    social_security_eligible: bool = True
    last_date: float


class Partner(BaseModel):
    """
    Attributes
        age (int)

        social_security_pension (SocialSecurityPension)

        earnings_records (dict)

        income_profiles (list[IncomeProfile])
    """

    age: Optional[int] = None
    social_security_pension: Optional[SocialSecurityPension] = None
    earnings_records: Optional[dict] = None
    income_profiles: Optional[list[IncomeProfile]] = None


class Admin(BaseModel):
    """
    Attributes
        partner_pension_strategy (SocialSecurityPensionOptions)
    """

    partner_pension_strategy: SocialSecurityPensionOptions


class User(BaseModel):
    """
    Attributes
        age (int)

        calculate_til (float)

        equity_target (float)

        portfolio (Portfolio)

        social_security_pension (SocialSecurityPension)

        spending (Spending)

        state (str)

        kids (Kids)

        earnings_records (dict)

        income_profiles (list[IncomeProfile])

        partner (Partner)

        admin (Admin)
    """

    age: int
    calculate_til: float = None
    equity_target: Optional[float] = None
    portfolio: Portfolio = Portfolio()
    social_security_pension: Optional[SocialSecurityPension] = None
    spending: Spending
    state: Optional[str] = None
    kids: Optional[Kids] = None
    earnings_records: Optional[dict] = None
    income_profiles: list[IncomeProfile] = []
    partner: Optional[Partner] = None
    admin: Optional[Admin] = None

    @validator("calculate_til", pre=True)
    def set_calculate_til(cls, value, values):
        """Set calculate till to be current year minus age + 90 if not specified"""
        if value is None:
            return constants.TODAY_YR - values["age"] + 90
        return value

    @field_validator("state")
    def state_supported(cls, state):
        """Class method for validating state is supported by taxes module"""
        if state not in STATE_BRACKET_RATES:
            raise ValueError(
                f"{state} is not supported. You can add it to data/taxes.py!"
            )
        return state


# Populate the Python object from the YAML configuration
with open(constants.CONFIG_PATH, "r", encoding="utf-8") as file:
    yaml_content = yaml.safe_load(file)
try:
    config = User(**yaml_content)
except ValidationError as e:
    print(e)


def attribute_filller(obj, attr: str, fill_value):
    """Iterate recursively through obj and fills attr with fill_value

    Only fills if not specified (attr set to None)

    Args:
        obj (any)
        attr (str): the object attribute to be targeted
        fill_value (any): the value to change the attribute to
    """
    if hasattr(obj, "__dict__"):
        for field_name, field_value in vars(obj).items():
            # Confirm attribute is part of obj, but is set
            # to default None (consequense of user not providing it in config)
            if field_name == attr and not field_value:
                setattr(obj, attr, fill_value)
            else:
                attribute_filller(field_value, attr, fill_value)


if config.equity_target:
    # config.equity_target is considered global
    # and overwrites any equity_target value left unspecified
    attribute_filller(config, "equity_target", config.equity_target)

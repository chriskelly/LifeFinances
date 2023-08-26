"""Config

Useful Pydantic documentation
    Required, optional, and nullable fields
        https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields
    V2 Validators
        
"""

from typing import Optional
import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from pydantic_core.core_schema import FieldValidationInfo
from app.data.taxes import STATE_BRACKET_RATES
from app.data import constants


class StrategyConfig(BaseModel):
    """
    Attributes
        enabled (bool)

        chosen (bool)
    """

    enabled: bool = False
    chosen: bool = False

    @field_validator("chosen")
    @classmethod
    def chosen_forces_enabled(cls, chosen, info: FieldValidationInfo):
        """Forces enabled to true if chosen is true

        Note: In strategy class, enabled has to be defined before chosen in order to access it.
        """
        if chosen:
            info.data["enabled"] = True
        return chosen


class StrategyOptions(BaseModel):
    """
    Attributes:
        enabled_strategies (dict[str, Strategy])

        chosen_strategy (tuple[str, Strategy])
    """

    enabled_strategies: Optional[dict[str, StrategyConfig]] = None
    chosen_strategy: Optional[tuple[str, StrategyConfig]] = None

    @model_validator(mode="after")
    def find_enabled_and_chosen_strategies(self):
        """Find enabled and chosen strategies"""
        # Restrict only one strategy to be chosen
        chosen_cnt = sum(
            1 for _, strategy in vars(self).items() if strategy and strategy.chosen
        )
        if chosen_cnt != 1:
            raise ValueError(
                f"Exactly one {type(self).__name__} strategy must have 'chosen' set to True."
            )
        # Find enabled strategies
        self.enabled_strategies = {
            prop: strategy
            for (prop, strategy) in vars(self).items()
            if strategy and strategy.enabled
        }
        # Find chosen strategy
        self.chosen_strategy = next(
            (
                (prop, strategy)
                for (prop, strategy) in self.enabled_strategies.items()
                if strategy and strategy.chosen
            ),
            None,
        )
        return self


class RealEstateStrategyConfig(StrategyConfig):
    """
    Attributes
        fraction_of_high_risk (float)
    """

    fraction_of_high_risk: float


class RealEstateOptions(StrategyOptions):
    """
    Attributes
        include (RealEstateStrategy)

        dont_include (Strategy)
    """

    include: Optional[RealEstateStrategyConfig] = None
    dont_include: Optional[StrategyConfig] = None


class LowRiskOptions(StrategyOptions):
    """
    Attributes
        bonds (Strategy)

        annuities (Strategy)
    """

    bonds: Optional[StrategyConfig] = None
    annuities: Optional[StrategyConfig] = None


class FlatAllocationStrategyConfig(StrategyConfig):
    """
    Attributes
        low_risk_target (float)
    """

    low_risk_target: Optional[float] = None

    @model_validator(mode="after")
    def low_risk_target_between_0_and_1(self):
        """Restrict low_risk_target to be between 0 and 1 if provided"""
        if self.low_risk_target and (
            self.low_risk_target < 0 or self.low_risk_target > 1
        ):
            raise ValueError("low_risk_target must be between 0 and 1")
        return self


class XMinusAgeStrategyConfig(StrategyConfig):
    """
    Attributes
        x (int)
    """

    x: Optional[int] = None


class BondTentStrategyConfig(StrategyConfig):
    """
    While called a Bond Tent, this strategy also applies to annuities if selected.

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

    @field_validator("start_allocation", "peak_allocation", "end_allocation")
    @classmethod
    def allocation_between_0_and_1(cls, allocation: float):
        """Restrict allocations to be between 0 and 1 if provided"""
        if allocation < 0 or allocation > 1:
            raise ValueError("Allocation must be between 0 and 1")
        return allocation

    @model_validator(mode="after")
    def dates_in_order(self):
        """Restrict dates to be in order if provided"""
        if self.start_date and self.peak_date and self.end_date:
            if self.start_date >= self.peak_date:
                raise ValueError("Start date must be before peak date")
            if self.peak_date >= self.end_date:
                raise ValueError("Peak date must be before end date")
        return self

    @model_validator(mode="after")
    def all_attributes_or_none(self):
        """Restrict attributes to be all present or all absent"""
        values = list(
            {
                k: v for k, v in vars(self).items() if k not in {"enabled", "chosen"}
            }.values()
        )
        none_values = [value is None for value in values]
        if any(none_values) and not all(none_values):
            raise ValueError(
                "All Bond Tent attributes must be defined if any are defined"
            )
        return self


class LifeCycleStrategyConfig(StrategyConfig):
    """
    Attributes
        equity_target (float)
    """

    equity_target: Optional[float] = None

    @model_validator(mode="after")
    def equity_target_greater_or_equal_to_0(self):
        """Restrict equity target to be greater or equal to 0 if provided"""
        if self.equity_target and self.equity_target < 0:
            raise ValueError("Equity target must be greater or equal to 0")
        return self


class AllocationOptions(StrategyOptions):
    """
    Attributes
        flat_allocation (FlatAllocationStrategyConfig)

        x_minus_age (XMinusAgeStrategyConfig)

        bond_tent (BondTentStrategyConfig)

        life_cycle (LifeCycleStrategyConfig)
    """

    flat_allocation: Optional[FlatAllocationStrategyConfig] = None
    x_minus_age: Optional[XMinusAgeStrategyConfig] = None
    bond_tent: Optional[BondTentStrategyConfig] = None
    life_cycle: Optional[LifeCycleStrategyConfig] = None


class Portfolio(BaseModel):
    """
    Attributes
        current_net_worth (float)

        drawdown_tax_rate (float)

        real_estate (RealEstateStrategy)

        low_risk (LowRiskOptions)

        allocation_strategy (AllocationOptions)
    """

    current_net_worth: float = 0
    drawdown_tax_rate: float = 0.1
    real_estate: RealEstateOptions = RealEstateOptions(
        dont_include=StrategyConfig(chosen=True)
    )
    low_risk: LowRiskOptions = LowRiskOptions(bonds=StrategyConfig(chosen=True))
    allocation_strategy: AllocationOptions = AllocationOptions(
        flat_allocation=FlatAllocationStrategyConfig(low_risk_target=0.4, chosen=True),
    )


class NetWorthStrategyConfig(StrategyConfig):
    """
    Attributes
        equity_target (float)
    """

    equity_target: Optional[float] = None


class SocialSecurityPensionOptions(StrategyOptions):
    """
    Attributes
        early (Strategy)

        mid (Strategy)

        late (Strategy)

        net_worth (NetWorthStrategy)

        same (Strategy)
    """

    early: Optional[StrategyConfig] = None
    mid: Optional[StrategyConfig] = None
    late: Optional[StrategyConfig] = None
    net_worth: Optional[NetWorthStrategyConfig] = None
    same: Optional[StrategyConfig] = None


class SocialSecurityPension(BaseModel):
    """
    Attributes
        trust_factor (float)

        pension_eligible (bool)

        strategy (SocialSecurityPensionOptions)
    """

    trust_factor: Optional[float] = 1
    pension_eligible: bool = False
    strategy: Optional[SocialSecurityPensionOptions] = SocialSecurityPensionOptions(
        mid=StrategyConfig(chosen=True)
    )
    earnings_records: Optional[dict] = {}


class CeilFloorStrategyConfig(StrategyConfig):
    """
    Attributes
        allowed_fluctuation (float)
    """

    allowed_fluctuation: Optional[float] = None


class SpendingOptions(StrategyOptions):
    """
    Attributes
        inflation_only (Strategy)

        ceil_floor (CeilFloorStrategy)
    """

    inflation_only: Optional[StrategyConfig] = None
    ceil_floor: Optional[CeilFloorStrategyConfig] = None


class Spending(BaseModel):
    """
    Attributes
        yearly_amount (int)

        spending_strategy (SpendingOptions)

        retirement_change (float)
    """

    yearly_amount: int
    spending_strategy: SpendingOptions = SpendingOptions(
        inflation_only=StrategyConfig(chosen=True)
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

    @model_validator(mode="after")
    def tax_deferred_income_less_than_starting_income(self):
        """Tax deferred income must be less than starting income"""
        if self.tax_deferred_income > self.starting_income:
            raise ValueError("Tax deferred income must be less than starting income")
        return self


def _income_profiles_in_order(income_profiles: list[IncomeProfile]):
    """Income profiles must be in order"""
    if income_profiles:
        for i in range(1, len(income_profiles)):
            if income_profiles[i].last_date < income_profiles[i - 1].last_date:
                raise ValueError("Income profiles must be in order")


class Partner(BaseModel):
    """
    Attributes
        age (int)

        social_security_pension (SocialSecurityPension)

        earnings_records (dict)

        income_profiles (list[IncomeProfile])
    """

    age: Optional[int] = None
    social_security_pension: Optional[SocialSecurityPension] = SocialSecurityPension()
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

        trial_quantity (int)

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
    trial_quantity: int = 500
    calculate_til: float = None
    equity_target: Optional[float] = None
    portfolio: Portfolio = Portfolio()
    social_security_pension: Optional[SocialSecurityPension] = SocialSecurityPension()
    spending: Spending
    state: Optional[str] = None
    kids: Optional[Kids] = None
    income_profiles: list[IncomeProfile] = None
    partner: Optional[Partner] = None
    admin: Optional[Admin] = None

    @property
    def intervals_per_trial(self) -> int:
        """Returns the number of intervals per trial"""

        return int(
            (self.calculate_til - constants.TODAY_YR_QT) / constants.YEARS_PER_INTERVAL
        )

    @field_validator("calculate_til")
    @classmethod
    def set_calculate_til(cls, calculate_til, info: FieldValidationInfo):
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
        if self.partner and self.partner.income_profiles:
            _income_profiles_in_order(self.partner.income_profiles)
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
        if "same" in self.social_security_pension.strategy.enabled_strategies:
            raise ValueError("`Same` strategy can only be enabled for partner")
        return self

    @model_validator(mode="after")
    def either_income_or_net_worth(self):
        """User should provide at least one income profile or net worth"""
        if (
            not self.income_profiles
            and not self.portfolio.current_net_worth
            and not (self.partner and self.partner.income_profiles)
        ):
            raise ValueError(
                "User must provide at least one income profile or net worth"
            )
        return self


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


def get_config() -> User:
    """Populate the Python object from the YAML configuration file

    Returns:
        User
    """
    with open(constants.CONFIG_PATH, "r", encoding="utf-8") as file:
        yaml_content = yaml.safe_load(file)
    try:
        config = User(**yaml_content)
    except ValidationError as error:
        print(error)

    # config.equity_target is considered global
    # and overwrites any equity_target value left unspecified
    if config.equity_target:
        attribute_filller(config, "equity_target", config.equity_target)

    return config

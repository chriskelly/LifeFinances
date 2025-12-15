"""Config

Useful Pydantic documentation
    Required, optional, and nullable fields
        https://docs.pydantic.dev/latest/migration/#required-optional-and-nullable-fields
    V2 Validators

"""

import csv
import math
from pathlib import Path
from typing import Optional, cast
import yaml
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from pydantic_core.core_schema import ValidationInfo
from app.data.taxes import STATE_BRACKET_RATES
from app.data import constants

with open(constants.STATISTICS_PATH, "r", encoding="utf-8") as file:
    reader = csv.reader(file)
    next(reader)  # Skip the first row
    ALLOWED_ASSETS = {row[0] for row in reader}
    ALLOWED_ASSETS.discard("Inflation")


class StrategyConfig(BaseModel):
    """
    Attributes
        enabled (bool): Defaults to False

        chosen (bool): Defaults to False
    """

    enabled: bool = False
    chosen: bool = False

    @field_validator("chosen")
    @classmethod
    def chosen_forces_enabled(cls, chosen, info: ValidationInfo):
        """Forces enabled to true if chosen is true

        Note: In strategy class, enabled has to be defined before chosen in order to access it.
        """
        if chosen:
            info.data["enabled"] = True
        return chosen


class StrategyOptions(BaseModel):
    """
    Attributes:
        enabled_strategies (dict[str, Strategy]): Defaults to None

        chosen_strategy (tuple[str, Strategy]): Set by validator, guaranteed to be non-None
    """

    enabled_strategies: Optional[dict[str, StrategyConfig]] = None
    chosen_strategy: tuple[str, StrategyConfig] = None  # type: ignore[assignment]

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
        chosen_strategy = next(
            (
                (prop, strategy)
                for (prop, strategy) in self.enabled_strategies.items()
                if strategy and strategy.chosen
            ),
            None,
        )
        if chosen_strategy is None:
            raise ValueError(
                f"chosen_strategy is None after validation. This should not happen if exactly one "
                f"{type(self).__name__} strategy has 'chosen' set to True."
            )
        # Type assertion: chosen_strategy is guaranteed to be non-None after the check above
        self.chosen_strategy = cast(tuple[str, StrategyConfig], chosen_strategy)
        return self


class AnnuityConfig(BaseModel):
    """
    Attributes
        net_worth_target (float): If net worth falls below this value, the annuity will trigger

        contribution_rate (float): The percentage of net income that will be
        contributed to the annuity
    """

    net_worth_target: float
    contribution_rate: float


def _allocation_sums_to_1(allocation: dict[str, float]):
    """Restrict allocation to sum to 1 if provided"""
    if allocation and not math.isclose(1, sum(allocation.values())):
        raise ValueError("flat strategy allocation must sum to 1")


def _allocation_options_valid(allocation_options: dict[str, float]):
    """All assets must be allowed in allocation options"""
    for asset in allocation_options.keys():
        if asset not in ALLOWED_ASSETS:
            raise ValueError(f"{asset} is not allowed in allocation options")


def _validate_allocation(allocation: dict[str, float]):
    """Validate allocation if provided"""
    _allocation_sums_to_1(allocation)
    _allocation_options_valid(allocation)


class FlatAllocationStrategyConfig(StrategyConfig):
    """
    Attributes
        allocation (dict[str, float])
    """

    allocation: dict[str, float]

    @model_validator(mode="after")
    def validate_allocation(self):
        """Validate allocation"""
        _validate_allocation(self.allocation)
        return self


class NetWorthPivotStrategyConfig(StrategyConfig):
    """
    Attributes
        net_worth_target (float): Also referred to as equity target
    """

    net_worth_target: float
    under_target_allocation: dict[str, float]
    over_target_allocation: dict[str, float]

    @model_validator(mode="after")
    def net_worth_target_greater_or_equal_to_0(self):
        """Restrict net worth target to be greater or equal to 0 if provided"""
        if self.net_worth_target and self.net_worth_target < 0:
            raise ValueError("Net worth target must be greater or equal to 0")
        return self

    @model_validator(mode="after")
    def validate_allocations(self):
        """Validate allocations"""
        _validate_allocation(self.under_target_allocation)
        _validate_allocation(self.over_target_allocation)
        return self


class AllocationOptions(StrategyOptions):
    """
    Attributes
        flat (FlatAllocationStrategyConfig): Defaults to None

        net_worth_pivot (LifeCycleStrategyConfig): Defaults to None
    """

    flat: Optional[FlatAllocationStrategyConfig] = None
    net_worth_pivot: Optional[NetWorthPivotStrategyConfig] = None


class Portfolio(BaseModel):
    """
    Attributes
        current_net_worth (float): Defaults to 0

        tax_rate (float): Defaults to 0.1

        annuity (AnnuityConfig): Defaults to None

        allocation_strategy (AllocationOptions)
    """

    current_net_worth: float = 0
    tax_rate: float = 0.1
    annuity: Optional[AnnuityConfig] = None
    allocation_strategy: AllocationOptions


class NetWorthStrategyConfig(StrategyConfig):
    """
    Attributes
        net_worth_target (float): Defaults to None
    """

    net_worth_target: Optional[float] = None


class SocialSecurityOptions(StrategyOptions):
    """
    Attributes
        early (Strategy): Defaults to None

        mid (Strategy): Defaults to None

        late (Strategy): Defaults to None

        net_worth (NetWorthStrategy): Defaults to None

        same (Strategy): Defaults to None
    """

    early: Optional[StrategyConfig] = None
    mid: Optional[StrategyConfig] = None
    late: Optional[StrategyConfig] = None
    net_worth: Optional[NetWorthStrategyConfig] = None
    same: Optional[StrategyConfig] = None


class SocialSecurity(BaseModel):
    """
    Attributes
        trust_factor (float): Defaults to 1

        pension_eligible (bool): Defaults to False

        strategy (SocialSecurityOptions): Defaults to `mid` strategy

        earnings_records (dict): Defaults to empty dict
    """

    trust_factor: float = 1
    pension_eligible: bool = False
    strategy: SocialSecurityOptions = SocialSecurityOptions(
        mid=StrategyConfig(chosen=True)
    )
    earnings_records: dict = {}


class PensionOptions(SocialSecurityOptions):
    """
    Attributes
        early (Strategy): Defaults to None

        mid (Strategy): Defaults to None

        late (Strategy): Defaults to None

        net_worth (NetWorthStrategy): Defaults to None

        same (Strategy): Defaults to None

        cash_out (Strategy): Defaults to None
    """

    cash_out: Optional[StrategyConfig] = None


class Pension(BaseModel):
    """
    Attributes
        trust_factor (float): Defaults to 1

        account_balance (float): Defaults to 0

        balance_update (float): Defaults to 2022.5

        strategy (PensionOptions): Defaults to `mid` strategy
    """

    trust_factor: float = 1
    account_balance: float = 0
    balance_update: float = 2022.5
    strategy: PensionOptions = PensionOptions(mid=StrategyConfig(chosen=True))


class SpendingOptions(StrategyOptions):
    """
    Attributes
        inflation_only (Strategy): Defaults to None

        ceil_floor (CeilFloorStrategy): Defaults to None
    """

    inflation_only: StrategyConfig = StrategyConfig(chosen=True)


class SpendingProfile(BaseModel):
    """
    Attributes
        yearly_amount (float)

        end_date (float)
    """

    yearly_amount: int
    end_date: Optional[float] = None


def _spending_profiles_validation(spending_profiles: list[SpendingProfile]):
    """Spending profiles must be in order and last profile should have no end date"""
    if spending_profiles:
        # Validate that all profiles except the last have end_date set
        for i in range(len(spending_profiles) - 1):
            if spending_profiles[i].end_date is None:
                raise ValueError(
                    "All spending profiles except the last must have an end_date"
                )

        # Validate ordering: compare end_date values for all profiles except the last
        # Since we've already validated that all except the last have end_date,
        # we can compare directly
        if len(spending_profiles) > 1:
            for i in range(1, len(spending_profiles) - 1):
                end_date_i = spending_profiles[i].end_date
                end_date_prev = spending_profiles[i - 1].end_date
                if end_date_i is not None and end_date_prev is not None:
                    if end_date_i < end_date_prev:
                        raise ValueError("Spending profiles must be in order")

        # Validate that the last profile has no end_date
        if spending_profiles[-1].end_date:
            raise ValueError("Last spending profile should have no end date")


class Spending(BaseModel):
    """
    Attributes
        spending_strategy (SpendingOptions): Defaults to `inflation_only` strategy

        profiles (list[SpendingProfile])
    """

    spending_strategy: SpendingOptions = SpendingOptions(
        inflation_only=StrategyConfig(chosen=True)
    )
    profiles: list[SpendingProfile]

    @model_validator(mode="after")
    def validate_profiles(self):
        """Spending profiles must be in order and last profile should have no end date"""
        _spending_profiles_validation(self.profiles)
        return self


class Kids(BaseModel):
    """
    Attributes
        cost_of_kid (float)

        birth_years (list[float])
    """

    fraction_of_spending: float
    years_of_support: int
    birth_years: list[float]


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


def _income_profiles_in_order(income_profiles: Optional[list[IncomeProfile]]):
    """Income profiles must be in order"""
    if income_profiles:
        for i in range(1, len(income_profiles)):
            if income_profiles[i].last_date < income_profiles[i - 1].last_date:
                raise ValueError("Income profiles must be in order")


class Partner(BaseModel):
    """
    Attributes
        age (int)

        social_security_pension (SocialSecurity): Defaults to default `SocialSecurity`

        income_profiles (list[IncomeProfile]): Defaults to None
    """

    age: int
    social_security_pension: SocialSecurity = SocialSecurity()
    income_profiles: Optional[list[IncomeProfile]] = None


class TPAWPlanner(BaseModel):
    """
    Attributes
        group_tol (float): Defaults to 1.0
        inflation_rate (float): Optional constant real annual inflation rate (e.g. 0.02 for 2%).
            When set, the TPAW planner export notebook can override
            the simulated inflation path with a deterministic one based on this rate.
            Defaults to None.
    """

    group_tol: float = 1.0
    inflation_rate: Optional[float] = None


class DisabilityCoverage(BaseModel):
    """
    Attributes
        percentage (float): Defaults to 0.0
        duration_years (int): Defaults to 0
    """

    percentage: float = 0.0
    duration_years: int = 0


class DisabilityInsuranceCalculator(BaseModel):
    """
    Attributes
        user_disability_coverage (DisabilityCoverage): Defaults to DisabilityCoverage()
        partner_disability_coverage (DisabilityCoverage): Defaults to DisabilityCoverage()
    """

    user_disability_coverage: DisabilityCoverage = DisabilityCoverage()
    partner_disability_coverage: DisabilityCoverage = DisabilityCoverage()


class Admin(BaseModel):
    """
    Attributes
        pension (Pension)
    """

    pension: Pension


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

        kids (Kids): Defaults to None

        income_profiles (list[IncomeProfile]): Defaults to None

        partner (Partner): Defaults to None

        tpaw_planner (TPAWPlanner): Defaults to None

        admin (Admin): Defaults to None
    """

    age: int
    trial_quantity: int = 500
    calculate_til: float = (
        None  # pyright: ignore[reportAssignmentType] # field_validator will set this to a float
    )
    net_worth_target: Optional[float] = None
    portfolio: Portfolio
    social_security_pension: SocialSecurity = SocialSecurity()
    spending: Spending
    state: Optional[str] = None
    kids: Optional[Kids] = None
    income_profiles: Optional[list[IncomeProfile]] = None
    partner: Optional[Partner] = None
    tpaw_planner: TPAWPlanner = TPAWPlanner()
    disability_insurance_calculator: Optional[DisabilityInsuranceCalculator] = None
    admin: Optional[Admin] = None

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
        if (
            self.social_security_pension.strategy.enabled_strategies
            and "same" in self.social_security_pension.strategy.enabled_strategies
        ):
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


def attribute_filler(obj, attr: str, fill_value):
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
                attribute_filler(field_value, attr, fill_value)


def get_config(config_path: Path) -> User:
    """Populate the Python object from the YAML configuration file

    Args:
        config_path (Path)

    Returns:
        User
    """
    with open(
        config_path, "r", encoding="utf-8"
    ) as file:  # pylint:disable=redefined-outer-name
        yaml_content = yaml.safe_load(file)
    try:
        config = User(**yaml_content)
    except ValidationError as error:
        raise error

    # config.net_worth_target is considered global
    # and overwrites any net_worth_target value left unspecified
    if config.net_worth_target:
        attribute_filler(config, "net_worth_target", config.net_worth_target)

    return config


def read_config_file(config_path: Path = constants.CONFIG_PATH) -> str:
    """Reads the config file and returns the text"""
    with open(config_path, "r", encoding="utf-8") as config_file:
        config_text = config_file.read()
    return config_text


def write_config_file(config_text: str, config_path: Path = constants.CONFIG_PATH):
    """Writes the config file after validation"""
    try:
        data_as_yaml = yaml.safe_load(config_text)
        User(**data_as_yaml)
    except (yaml.YAMLError, TypeError) as error:
        print(f"Invalid YAML format: {error}")
        raise error
    except ValidationError as error:
        print(f"Invalid config: {error}")
        raise error
    with open(config_path, "w", encoding="utf-8") as config_file:
        config_file.write(config_text)

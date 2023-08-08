"""Module for representing portfolio allocation strategies

Classes:
    AllocationRatios: Dataclass of allocation ratios for a portfolio
    Controller: Manages strategy and allocation generation
        gen_allocation(self, state: State) -> AllocationRatios: 
        Returns allocation ratios for a given state
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import numpy as np
from app.models.financial.state import State
from app.models.config import User
from app.models import config
from app import util


@dataclass
class AllocationRatios:
    """Dataclass of allocation ratios for a portfolio

    A more detailed version of a RiskRatio

    Attributes
        stock (float)

        bond (float)

        real_estate (float)

        annuity (float)
    """

    stock: float
    bond: float
    real_estate: float
    annuity: float


@dataclass
class RiskRatios:
    """Dataclass for risk ratio of a portfolio

    A less detailed version of an AllocationRatios.

    At least one attribute needs to be provided. If only one is provided,
    the other will be set to `1-provided attribute`

    Attributes
        low (float): Ratio of portfolio with low risk

        high (float): Ratio of portfolio with high risk
    """

    low: Optional[float] = None
    high: Optional[float] = None

    def __post_init__(self):
        if not self.low:
            self.low = 1 - self.high
        if not self.high:
            self.high = 1 - self.low


class Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:

        risk_ratio(self, state:State) -> RiskRatio
    """

    @abstractmethod
    def risk_ratio(self, state: State) -> RiskRatios:
        """Generate risk ratios for a portfolio

        Args:
            state (financial.State): current state

        Returns:
            RiskRatios
        """


@dataclass
class FlatBond(Strategy):
    """Implementation of a flat bond strategy.

    Attributes
        config (config.FlatBondStrategy)

    Methods
        risk_ratio(self, state:State) -> RiskRatio:
        Low risk ratio is equal to `flat_bond_target` from user config.
    """

    config: config.FlatBondStrategy

    def risk_ratio(self, state: State):
        low_risk = self.config.flat_bond_target
        return RiskRatios(low=low_risk)


@dataclass
class XMinusAge(Strategy):
    """Implementation of an X Minus Age strategy.

    Attributes
        config (config.XMinusAgeStrategy)

    Methods
        risk_ratio(self, state:State) -> RiskRatio:
        High risk ratio is equal to x minus average current age of users
    """

    config: config.XMinusAgeStrategy

    def risk_ratio(self, state: State):
        if state.user.partner:
            average_age = (state.user.age + state.user.partner.age) / 2
        else:
            average_age = state.user.age
        current_age = average_age + state.interval_cnt
        high_risk = util.constrain((self.config.x - current_age) / 100, low=0, high=1)
        return RiskRatios(high=high_risk)


@dataclass
class BondTent(Strategy):
    """Implementation of a bond tent strategy.

    Attributes
        config (config.BondTentStrategy)

    Methods
        risk_ratio(self, state:State) -> RiskRatio:
        Low risk ratio follows bond tent path defined in config
    """

    config: config.BondTentStrategy

    def risk_ratio(self, state: State):
        if state.date <= self.config.start_date:
            # Initial flat period
            low_risk = self.config.start_allocation
        elif state.date < self.config.peak_date:
            # Climb to peak
            low_risk = np.interp(
                state.date,
                [self.config.start_date, self.config.peak_date],
                [self.config.start_allocation, self.config.peak_allocation],
            )
        elif state.date == self.config.peak_date:
            # Peak point
            low_risk = self.config.peak_allocation
        elif state.date < self.config.end_date:
            # Descend to new flat
            low_risk = np.interp(
                state.date,
                [self.config.peak_date, self.config.end_date],
                [self.config.peak_allocation, self.config.end_allocation],
            )
        elif state.date >= self.config.end_date:
            # Flat period
            low_risk = self.config.end_allocation
        return RiskRatios(low=low_risk)


@dataclass
class LifeCycle(Strategy):
    """Implementation of a Life Cycle strategy.

    Attributes
        config (config.LifeCycleStrategy)

    Methods
        risk_ratio(self, state:State) -> RiskRatio
        High risk ratio follows `equity_target` divided by `net_worth`
    """

    config: config.LifeCycleStrategy

    def risk_ratio(self, state: State):
        equity_target_present_value = state.inflation * self.config.equity_target
        risk_factor = util.constrain(
            equity_target_present_value / state.net_worth, low=0, high=1
        )
        return RiskRatios(high=risk_factor)


class Controller:
    """Manages strategy and allocation generation

    Attributes
        user (User)

    Methods
        allocation(self) -> AllocationRatios:
    """

    def __init__(self, user: User):
        self.user = user
        (
            strategy_str,
            strategy_obj,
        ) = user.portfolio.allocation_strategy.chosen_strategy
        if strategy_str == "flat_bond":
            self.strategy = FlatBond(config=strategy_obj)
        elif strategy_str == "x_minus_age":
            self.strategy = XMinusAge(config=strategy_obj)
        elif strategy_str == "bond_tent":
            self.strategy = BondTent(config=strategy_obj)
        elif strategy_str == "life_cycle":
            self.strategy = LifeCycle(config=strategy_obj)

    def gen_allocation(self, state: State) -> AllocationRatios:
        """Returns allocation ratios for a given state

        Args:
            state (State): current state

        Returns:
            AllocationRatios
        """
        risk_ratio = self.strategy.risk_ratio(state)
        if self.user.portfolio.annuities_instead_of_bonds:
            annuity = risk_ratio.low
            bond = 0
        else:
            bond = risk_ratio.low
            annuity = 0
        real_estate = risk_ratio.high * self.user.portfolio.real_estate.equity_ratio
        stock = risk_ratio.high - real_estate
        return AllocationRatios(
            stock=stock, bond=bond, real_estate=real_estate, annuity=annuity
        )

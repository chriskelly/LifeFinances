"""Module for representing portfolio allocation strategies

Classes:
    AllocationRatios: Dataclass of allocation ratios for a portfolio
    Controller: Manages strategy and allocation generation
        gen_allocation(self, state: State) -> AllocationRatios: 
        Returns allocation ratios for a given state
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from app.models.financial.state import State
from app.models.config import User
from app.models import config


@dataclass
class AllocationRatios:
    """Dataclass of allocation ratios for a portfolio

    A more detailed version of a RiskRatio

    Attributes
        assets (np.ndarray): array of allocation ratios for each asset
    """

    assets: np.ndarray


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:

        gen_allocation(self, state: State) -> AllocationRatios:
    """

    @abstractmethod
    def gen_allocation(self, state: State) -> AllocationRatios:
        """Generate risk ratios for a portfolio

        Args:
            state (financial.State): current state

        Returns:
            AllocationRatios
        """
        return NotImplementedError


@dataclass
class _FlatAllocationStrategy(_Strategy):
    """Implementation of a flat bond strategy.

    Attributes
        config (config.FlatBondStrategy)

        asset_lookup (dict[str, int]): lookup table for asset names

    Methods
        gen_allocation(self, state:State) -> AllocationRatios:
    """

    config: config.FlatAllocationStrategyConfig
    asset_lookup: dict[str, int]

    def gen_allocation(self, state: State):
        allocation = np.zeros(len(self.asset_lookup))
        for asset, ratio in self.config.allocation.items():
            allocation[self.asset_lookup[asset]] = ratio
        return AllocationRatios(assets=allocation)


class Controller:
    """Manages strategy and allocation generation

    Attributes
        user (User)

    Methods
        allocation(self) -> AllocationRatios:
    """

    def __init__(self, user: User, asset_lookup: dict[str, int]):
        self.user = user
        (
            strategy_str,
            strategy_obj,
        ) = user.portfolio.allocation_strategy.chosen_strategy
        match strategy_str:
            case "flat":
                self.strategy = _FlatAllocationStrategy(
                    config=strategy_obj, asset_lookup=asset_lookup
                )
            case _:
                raise ValueError(
                    f"Invalid strategy: {user.portfolio.allocation_strategy.chosen_strategy}"
                )

    def gen_allocation(self, state: State) -> AllocationRatios:
        """Returns allocation ratios for a given state

        Args:
            state (State): current state

        Returns:
            AllocationRatios
        """
        return self.strategy.gen_allocation(state)

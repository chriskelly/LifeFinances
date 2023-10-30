"""Module for representing portfolio allocation strategies

Classes:
    Controller: Manages strategy and allocation generation
        gen_allocation(self, state: State) -> np.ndarray: 
        Returns allocation ratios for a given state
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from app.models.financial.state import State
from app.models.config import User
from app.models import config


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:

        gen_allocation(self, state: State) -> np.ndarray:
    """

    @abstractmethod
    def gen_allocation(self, state: State) -> np.ndarray:
        """Generate risk ratios for a portfolio

        Args:
            state (financial.State): current state

        Returns:
            np.ndarray: Allocation ratios for each asset
        """
        return NotImplementedError


@dataclass
class _FlatAllocationStrategy(_Strategy):
    """Implementation of a flat bond strategy.

    Attributes
        config (config.FlatBondStrategy)

        asset_lookup (dict[str, int]): lookup table for asset names

    Methods
        gen_allocation(self, state:State) -> np.ndarray:
    """

    config: config.FlatAllocationStrategyConfig
    asset_lookup: dict[str, int]

    def gen_allocation(self, state: State):
        allocation = np.zeros(len(self.asset_lookup))
        for asset, ratio in self.config.allocation.items():
            allocation[self.asset_lookup[asset]] = ratio
        return allocation


class Controller:
    """Manages strategy and allocation generation

    Methods
        gen_allocation(self) -> np.ndarray:
    """

    def __init__(self, user: User, asset_lookup: dict[str, int]):
        (
            strategy_str,
            strategy_obj,
        ) = user.portfolio.allocation_strategy.chosen_strategy
        match strategy_str:
            case "flat":
                self._strategy = _FlatAllocationStrategy(
                    config=strategy_obj, asset_lookup=asset_lookup
                )
            case _:
                raise ValueError(
                    f"Invalid strategy: {user.portfolio.allocation_strategy.chosen_strategy}"
                )

    def gen_allocation(self, state: State) -> np.ndarray:
        """Returns allocation ratios for a given state

        Args:
            state (State): current state

        Returns:
            np.ndarray: Allocation ratios for each asset
        """
        return self._strategy.gen_allocation(state)

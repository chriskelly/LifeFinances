"""Module for representing portfolio allocation strategies

Classes:
    Controller: Manages strategy and allocation generation
        gen_allocation(self, state: State) -> np.ndarray:
        Returns allocation ratios for a given state
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import cast

import numpy as np

from app.models import config
from app.models.config import User
from app.models.financial.state import State


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:

        gen_allocation(self, state: State) -> np.ndarray:
    """

    @abstractmethod
    def gen_allocation(self, state: State) -> np.ndarray:
        """Generate allocation array for a portfolio

        Args:
            state (financial.State): current state

        Returns:
            np.ndarray: Allocation ratios for each asset
        """
        raise NotImplementedError


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
    allocation: np.ndarray = field(init=False)

    def __post_init__(self):
        self.allocation = _allocation_dict_to_array(
            allocation_dict=self.config.allocation, asset_lookup=self.asset_lookup
        )

    def gen_allocation(self, state: State) -> np.ndarray:
        return self.allocation


@dataclass
class _NetWorthPivotStrategy(_Strategy):
    config: config.NetWorthPivotStrategyConfig
    asset_lookup: dict[str, int]
    under_target_allocation: np.ndarray = field(init=False)
    over_target_allocation: np.ndarray = field(init=False)

    def __post_init__(self):
        self.under_target_allocation = _allocation_dict_to_array(
            allocation_dict=self.config.under_target_allocation,
            asset_lookup=self.asset_lookup,
        )
        self.over_target_allocation = _allocation_dict_to_array(
            allocation_dict=self.config.over_target_allocation,
            asset_lookup=self.asset_lookup,
        )

    def gen_allocation(self, state: State):
        present_value_net_worth = state.net_worth / state.inflation
        target_multiple = present_value_net_worth / self.config.net_worth_target
        if target_multiple <= 1:
            return self.under_target_allocation
        under_target_ratio = 1 / target_multiple
        over_target_ratio = 1 - under_target_ratio
        return (
            self.under_target_allocation * under_target_ratio
            + self.over_target_allocation * over_target_ratio
        )


def _allocation_dict_to_array(
    allocation_dict: dict[str, float], asset_lookup: dict[str, int]
) -> np.ndarray:
    """Converts an allocation dict to an array

    Args:
        allocation_dict (dict[str, float]): allocation dict
        asset_lookup (dict[str, int]): lookup table for asset names

    Returns:
        np.ndarray: allocation array
    """
    allocation = np.zeros(len(asset_lookup))
    for asset, ratio in allocation_dict.items():
        allocation[asset_lookup[asset]] = ratio
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
                    config=cast(config.FlatAllocationStrategyConfig, strategy_obj),
                    asset_lookup=asset_lookup,
                )
            case "net_worth_pivot":
                self._strategy = _NetWorthPivotStrategy(
                    config=cast(config.NetWorthPivotStrategyConfig, strategy_obj),
                    asset_lookup=asset_lookup,
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

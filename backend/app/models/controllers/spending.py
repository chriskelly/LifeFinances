"""Module for spending calculation strategies

Classes:
    Controller: Manages strategy and spending calculation
        calc_spending(self, state: State) -> float:
        Returns spending amount for a given state
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import cast

from app.data.constants import INTERVALS_PER_YEAR
from app.models import config
from app.models.config import User
from app.models.financial.state import State


class _Strategy(ABC):
    """Abstract spending strategy class.

    Required methods:
        calc_spending(self, state: State) -> float:
    """

    @abstractmethod
    def calc_spending(self, state: State) -> float:
        """Calculate spending amount for given state

        Args:
            state (State): current state

        Returns:
            float: Spending amount (negative value representing outflow)

        Raises:
            ValueError: If no valid profile found for state.date
        """
        raise NotImplementedError


@dataclass
class _InflationFollowingStrategy(_Strategy):
    """Implementation of inflation-following spending strategy.

    Selects appropriate spending profile based on date and applies
    inflation adjustment to the base yearly amount.

    Attributes:
        config (config.InflationFollowingConfig): Strategy configuration
        profiles (list[SpendingProfile]): Extracted profiles for efficient access

    Methods:
        calc_spending(self, state: State) -> float:
    """

    config: config.InflationFollowingConfig

    def __post_init__(self):
        """Extract profiles from config for efficient access"""
        self.profiles = self.config.profiles

    def calc_spending(self, state: State) -> float:
        """Calculate spending using profile selection and inflation adjustment

        Algorithm:
        1. Iterate through profiles in order
        2. Select first profile where (end_date is None) OR (state.date <= end_date)
        3. Calculate: -yearly_amount / INTERVALS_PER_YEAR * state.inflation
        4. Return negative value (outflow)

        Args:
            state (State): Current simulation state

        Returns:
            float: Negative spending amount for the interval

        Raises:
            ValueError: If no profile matches (should never happen with valid config)
        """
        for profile in self.profiles:
            if profile.end_date is None or state.date <= profile.end_date:
                return -(profile.yearly_amount / INTERVALS_PER_YEAR) * state.inflation

        # Should never reach here if validation worked correctly
        raise ValueError(
            f"No spending profile found for the current date: {state.date}"
        )


class Controller:
    """Manages spending strategy and spending calculation

    Public interface for spending subsystem. Selects appropriate strategy
    based on user configuration and delegates calculation to that strategy.

    Methods:
        calc_spending(self, state: State) -> float:
    """

    def __init__(self, user: User):
        """Initialize controller with appropriate strategy

        Args:
            user: User configuration containing spending_strategy

        Raises:
            ValueError: If invalid strategy name selected
        """
        (
            strategy_str,
            strategy_obj,
        ) = user.spending_strategy.chosen_strategy

        match strategy_str:
            case "inflation_following":
                self._strategy = _InflationFollowingStrategy(
                    config=cast(config.InflationFollowingConfig, strategy_obj)
                )
            case _:
                raise ValueError(
                    f"Invalid spending strategy: {strategy_str}. "
                    f"Expected 'inflation_following'."
                )

    def calc_spending(self, state: State) -> float:
        """Calculate spending amount for current state

        Delegates to the selected strategy.

        Args:
            state: Current simulation state

        Returns:
            float: Spending amount (negative value)

        Raises:
            ValueError: If strategy cannot calculate spending for given state
        """
        return self._strategy.calc_spending(state=state)

"""Module for representing portfolio allocation strategies

Classes:
    Controller: Manages strategy and allocation generation
        gen_allocation(self, state: State) -> np.ndarray:
        Returns allocation ratios for a given state
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

import numpy as np
import numpy_financial as npf

from app.data import constants
from app.models import config
from app.models.config import User
from app.models.controllers.economic_data import CsvVariableMixRepo
from app.models.financial.state import State
from app.util import constrain, interval_yield

if TYPE_CHECKING:
    from app.models.controllers import Controllers


class _Strategy(ABC):
    """Abstract allocation strategy class.

    Required methods:

        gen_allocation(self, state: State, controllers: Controllers | None) -> np.ndarray:
    """

    @abstractmethod
    def gen_allocation(
        self, state: State, controllers: "Controllers | None" = None
    ) -> np.ndarray:
        """Generate allocation array for a portfolio

        Args:
            state (State): current state
            controllers (Controllers | None): Controllers object for accessing other controllers.
                Defaults to None. Some strategies may require this parameter.

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

    def gen_allocation(
        self, state: State, controllers: "Controllers | None" = None
    ) -> np.ndarray:
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

    def gen_allocation(
        self, state: State, controllers: "Controllers | None" = None
    ) -> np.ndarray:
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


class _FakeState:
    """Lightweight stand-in for State used when precomputing future income.

    Accessing `net_worth` on this fake state is prohibited to ensure that
    benefit timing does not depend on future net worth during precomputation.
    """

    def __init__(self, *, user: User, date: float, interval_idx: int, inflation: float):
        self.user = user
        self.date = date
        self.interval_idx = interval_idx
        self.inflation = inflation

    @property  # pragma: no cover - defensive safety
    def net_worth(self) -> float:
        raise RuntimeError(
            "net_worth access is not allowed on fake states used for income precomputation"
        )


@dataclass
class _TotalPortfolioStrategy(_Strategy):
    """Implementation of total portfolio allocation strategy.

    This strategy calculates allocation based on total portfolio value
    (current savings + present value of future income) and relative risk aversion.

    Attributes:
        config (config.TotalPortfolioStrategyConfig): Strategy configuration
        asset_lookup (dict[str, int]): Lookup table for asset names

    Methods:
        gen_allocation(self, state: State, controllers: Controllers | None) -> np.ndarray:
    """

    config: config.TotalPortfolioStrategyConfig
    asset_lookup: dict[str, int]

    # Allocation arrays
    high_risk_allocation: np.ndarray = field(init=False)
    low_risk_allocation: np.ndarray = field(init=False)

    # Expected return / risk metrics (annualized)
    expected_high_risk_return: float = field(init=False)
    expected_high_risk_stdev: float = field(init=False)
    expected_low_risk_return: float = field(init=False)
    merton_share: float = field(init=False)

    # Precomputed income arrays (per interval)
    job_income_by_interval: np.ndarray | None = field(init=False, default=None)
    benefit_income_by_interval: np.ndarray | None = field(init=False, default=None)
    future_income_by_interval: np.ndarray | None = field(init=False, default=None)

    # Internal flag to detect division-by-zero in Merton Share denominator
    _merton_division_by_zero: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        """Convert allocations to arrays and compute expected returns / risk metrics."""
        # Convert allocations to arrays aligned with asset_lookup
        self.low_risk_allocation = _allocation_dict_to_array(
            allocation_dict=self.config.low_risk_allocation,
            asset_lookup=self.asset_lookup,
        )
        self.high_risk_allocation = _allocation_dict_to_array(
            allocation_dict=self.config.high_risk_allocation,
            asset_lookup=self.asset_lookup,
        )

        # Read variable statistics once using existing CSV repo
        repo = CsvVariableMixRepo(statistics_path=constants.STATISTICS_PATH)
        variable_mix = repo.get_variable_mix()

        # Build returns and stdevs dicts from VariableMix
        returns: dict[str, float] = {}
        stdevs: dict[str, float] = {}
        for label, idx in variable_mix.lookup_table.items():
            if label == "Inflation":
                # Inflation is not an investable asset in allocations
                continue
            stat = variable_mix.variable_stats[idx]
            # Convert yield (e.g., 1.092) to return (e.g., 0.092)
            returns[label] = stat.mean_yield - 1.0
            stdevs[label] = stat.stdev

        # Validate that all assets in allocations have stats
        missing_assets: set[str] = set()
        for allocation_dict in (
            self.config.low_risk_allocation,
            self.config.high_risk_allocation,
        ):
            for asset in allocation_dict:
                if asset not in returns:
                    missing_assets.add(asset)
        if missing_assets:
            missing_str = ", ".join(sorted(missing_assets))
            raise ValueError(
                f"Missing asset statistics for asset(s): {missing_str} in variable_statistics.csv"
            )

        # Helper to compute weighted averages
        def _weighted_avg(
            allocation_dict: dict[str, float], values: dict[str, float]
        ) -> float:
            return sum(
                allocation_dict[asset] * values[asset] for asset in allocation_dict
            )

        self.expected_high_risk_return = _weighted_avg(
            self.config.high_risk_allocation, returns
        )
        self.expected_low_risk_return = _weighted_avg(
            self.config.low_risk_allocation, returns
        )
        self.expected_high_risk_stdev = _weighted_avg(
            self.config.high_risk_allocation, stdevs
        )

        # Compute Merton Share, guarding against division by zero
        denominator = self.config.RRA * (self.expected_high_risk_stdev**2)
        if denominator <= 0:
            # Division by zero or invalid denominator – fall back to low-risk allocation
            self._merton_division_by_zero = True
            self.merton_share = 0.0
        else:
            raw_merton_share = (
                self.expected_high_risk_return - self.expected_low_risk_return
            ) / denominator
            # Cap Merton Share to [0, 1] as per spec
            self.merton_share = constrain(raw_merton_share, 0.0, 1.0)

    # ---- Internal helpers -------------------------------------------------

    def _ensure_income_arrays(
        self, *, state: State, controllers: "Controllers"
    ) -> None:
        """Precompute job, benefit, and total future income per interval.

        This is called lazily on first allocation calculation, once Controllers
        is available, and then reused for all subsequent intervals.
        """
        if self.future_income_by_interval is not None:
            return

        intervals_per_trial = state.user.intervals_per_trial
        # Initialize arrays
        job_income = np.zeros(intervals_per_trial, dtype=float)
        benefit_income = np.zeros(intervals_per_trial, dtype=float)

        ss_controller = controllers.social_security
        pension_controller = controllers.pension

        for interval_idx in range(intervals_per_trial):
            job_income[interval_idx] = controllers.job_income.get_total_income(
                interval_idx
            )

            # Get actual cumulative inflation for this interval
            economic_data = controllers.economic_data.get_economic_state_data(
                interval_idx
            )

            # Fake state for benefits – forbid net_worth access
            fake_state = _FakeState(
                user=state.user,
                date=constants.TODAY_YR_QT
                + interval_idx * constants.YEARS_PER_INTERVAL,
                interval_idx=interval_idx,
                inflation=economic_data.inflation,
            )

            # Calculate benefit payments (controllers may return zero if not configured)
            # Type ignore: _FakeState is compatible with State for controller methods
            ss_user, ss_partner = ss_controller.calc_payment(fake_state)  # type: ignore[arg-type]
            pension_payment = pension_controller.calc_payment(fake_state)  # type: ignore[arg-type]

            benefit_income[interval_idx] = ss_user + ss_partner + pension_payment

        self.job_income_by_interval = job_income
        self.benefit_income_by_interval = benefit_income
        self.future_income_by_interval = job_income + benefit_income

    # ---- Public API -------------------------------------------------------

    def gen_allocation(
        self, state: State, controllers: "Controllers | None" = None
    ) -> np.ndarray:
        """Generate allocation array for total portfolio strategy.

        Args:
            state (State): Current simulation state
            controllers (Controllers | None): Controllers object (required for this strategy)

        Returns:
            np.ndarray: Allocation ratios for each asset

        Raises:
            ValueError: If controllers is None
        """
        if controllers is None:
            raise ValueError(
                "controllers parameter is required for total_portfolio strategy"
            )

        # Lazily precompute income arrays when Controllers is first available
        self._ensure_income_arrays(state=state, controllers=controllers)

        # Step 1: Calculate present value of future income using discount rate
        discount_rate_annual = self.expected_low_risk_return
        discount_rate_interval = interval_yield(1.0 + discount_rate_annual) - 1.0

        # Slice future income from the next interval onward
        assert self.future_income_by_interval is not None  # For type checkers
        start_idx = state.interval_idx + 1
        if start_idx >= len(self.future_income_by_interval):
            income_array = np.array([], dtype=float)
        else:
            income_array = self.future_income_by_interval[start_idx:]

        if income_array.size == 0:
            future_income_pv = 0.0
        else:
            # NOTE: numpy_financial.npv treats values[0] as occurring at time 0 (undiscounted).
            # Our income_array starts at the *next* interval (t=1), so prepend a 0 at t=0
            # to ensure the first future payment is discounted correctly.
            npv_values = np.concatenate(([0.0], income_array.astype(float)))
            future_income_pv = float(
                npf.npv(rate=discount_rate_interval, values=npv_values)
            )

        # Step 2: Calculate total portfolio and handle edge cases
        savings = state.net_worth
        total_portfolio = future_income_pv + savings

        if total_portfolio <= 0:
            # Zero or negative total portfolio – return low-risk allocation
            return self.low_risk_allocation

        if self._merton_division_by_zero:
            # If Merton Share denominator was invalid, fall back to low-risk allocation
            return self.low_risk_allocation

        # Step 3: Apply Merton Share
        # Merton Share already capped in __post_init__, but guard again defensively
        merton_share = constrain(self.merton_share, 0.0, 1.0)

        total_high_risk_amount = merton_share * total_portfolio

        # Step 4: Compute savings high/low risk ratios
        if savings <= 0:
            savings_high_risk_ratio = 0.0
        else:
            savings_high_risk_ratio = min(1.0, total_high_risk_amount / savings)

        savings_low_risk_ratio = 1.0 - savings_high_risk_ratio

        # Step 5: Blend high and low risk allocations
        allocation = (
            self.high_risk_allocation * savings_high_risk_ratio
            + self.low_risk_allocation * savings_low_risk_ratio
        )

        # Numerical safety: ensure allocation sums to 1.0
        total = float(allocation.sum())
        if not np.isclose(total, 1.0):
            if total > 0:
                allocation = allocation / total
            else:
                allocation = self.low_risk_allocation
                print(
                    f"Allocation did not blend correctly, returning low-risk allocation: {allocation}"
                )

        return allocation


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
        gen_allocation(self, state: State, controllers: Controllers | None) -> np.ndarray:
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
            case "total_portfolio":
                # Create strategy instance (controllers will be passed in gen_allocation)
                self._strategy = _TotalPortfolioStrategy(
                    config=cast(config.TotalPortfolioStrategyConfig, strategy_obj),
                    asset_lookup=asset_lookup,
                )
            case _:
                raise ValueError(
                    f"Invalid strategy: {user.portfolio.allocation_strategy.chosen_strategy}"
                )

    def gen_allocation(
        self, state: State, controllers: "Controllers | None" = None
    ) -> np.ndarray:
        """Returns allocation ratios for a given state

        Args:
            state (State): current state
            controllers (Controllers | None): Controllers object for accessing other controllers.
                Defaults to None. Required for some strategies (e.g., total_portfolio).

        Returns:
            np.ndarray: Allocation ratios for each asset
        """
        return self._strategy.gen_allocation(state=state, controllers=controllers)

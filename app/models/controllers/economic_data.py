"""Generates randomized economic data for stocks, bonds, real estate and inflation.

Return/rate/yield definitions: something that has a 3% growth is a
0.03 return/rate and 1.03 yield

This file contains the following functions:

    * main() - Generates and returns stock, bond, real estate, and inflation returns
"""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from scipy import stats
from app.data.constants import (
    BOND_ANNUAL_HIGH,
    BOND_ANNUAL_LOW,
    BOND_MEAN,
    BOND_STDEV,
    INFLATION_MEAN,
    INFLATION_SKEW,
    INFLATION_STDEV,
    INTERVALS_PER_YEAR,
    RE_ANNUAL_HIGH,
    RE_ANNUAL_LOW,
    RE_MEAN,
    RE_STDEV,
    STOCK_ANNUAL_HIGH,
    STOCK_ANNUAL_LOW,
    STOCK_MEAN,
    STOCK_STDEV,
)
from app.models.financial.state import State
from app.util import interval_stdev, interval_yield

rng = np.random.default_rng()


@dataclass
class _StatisticBehavior(ABC):
    mean_yield: float
    stdev: float

    @abstractmethod
    def gen_interval_behavior(self):
        """Returns Behavior object with modified mean_yield and stdev for a given interval"""


@dataclass
class InvestmentBehavior(_StatisticBehavior):
    """Characteristics for a given investment asset class

    Attributes:
        mean (float): Geometric average yield

        stdev (float): Standard deviation of returns

        annualized_high (float): Highest allowed annualized lifetime yield,
        based on historical data of rolling time periods

        annualized_low (float): Lowest allowed annualized lifetime yield

    Methods:
        gen_interval_behavior(intervals_per_year: int):
        Returns InflationBehavior object with modified
        mean_yield and stdev for a given interval
    """

    annualized_high: float
    annualized_low: float

    def gen_interval_behavior(self):
        return InvestmentBehavior(
            mean_yield=interval_yield(self.mean_yield),
            stdev=interval_stdev(self.stdev),
            annualized_high=self.annualized_high,
            annualized_low=self.annualized_low,
        )


STOCK_BEHAVIOR = InvestmentBehavior(
    mean_yield=STOCK_MEAN,
    stdev=STOCK_STDEV,
    annualized_high=STOCK_ANNUAL_HIGH,
    annualized_low=STOCK_ANNUAL_LOW,
)
BOND_BEHAVIOR = InvestmentBehavior(
    mean_yield=BOND_MEAN,
    stdev=BOND_STDEV,
    annualized_high=BOND_ANNUAL_HIGH,
    annualized_low=BOND_ANNUAL_LOW,
)
REAL_ESTATE_BEHAVIOR = InvestmentBehavior(
    mean_yield=RE_MEAN,
    stdev=RE_STDEV,
    annualized_high=RE_ANNUAL_HIGH,
    annualized_low=RE_ANNUAL_LOW,
)


class InflationBehavior(_StatisticBehavior):
    """Characteristics for inflation

    By default, an instance of this class is created with constants

    Attributes:
        mean (float): Geometric average yield

        stdev (float): Standard deviation of returns

        skew (float): Skew of the distribution

    Methods:
        gen_interval_behavior(intervals_per_year: int):
        Returns InflationBehavior object with modified
        mean_yield and stdev for a given interval
    """

    def __init__(
        self,
        mean_yield=INFLATION_MEAN,
        stdev=INFLATION_STDEV,
        skew=INFLATION_SKEW,
    ):
        super().__init__(mean_yield=mean_yield, stdev=stdev)
        self.skew = skew

    def gen_interval_behavior(self):
        return InflationBehavior(
            mean_yield=interval_yield(self.mean_yield),
            stdev=interval_stdev(self.stdev),
            skew=self.skew,
        )


INFLATION_BEHAVIOR = InflationBehavior()


@dataclass
class EconomicStateData:
    """Economic data for a single state

    Attributes:
        stock_return (float)

        bond_return (float)

        real_estate_return (float)

        inflation (float)
    """

    stock_return: float
    bond_return: float
    real_estate_return: float
    inflation: float

    def __repr__(self) -> str:
        return "Economic Data"


@dataclass
class EconomicTrialData:
    """1D arrays of economic data

    Attributes:
        stock_returns (np.ndarray)

        bond_returns (np.ndarray)

        real_estate_returns (np.ndarray)

        inflation (list)

    Methods:
        get_state_data(interval_idx: int): Returns a single state's economic data
    """

    stock_returns: np.ndarray
    bond_returns: np.ndarray
    real_estate_returns: np.ndarray
    inflation: list

    def __repr__(self) -> str:
        return "Economic Data"

    def get_state_data(self, interval_idx) -> EconomicStateData:
        """Returns a single state's economic data

        Args:
            interval_idx (int): interval count

        Returns:
            EconomicStateData: Economic data for a single state
        """
        return EconomicStateData(
            stock_return=self.stock_returns[interval_idx],
            bond_return=self.bond_returns[interval_idx],
            real_estate_return=self.real_estate_returns[interval_idx],
            inflation=self.inflation[interval_idx],
        )


@dataclass
class EconomicEngineData:
    """2D arrays of economic data

    Attributes:
        stock_returns (list[np.ndarray])

        bond_returns (list[np.ndarray])

        real_estate_returns (list[np.ndarray])

        inflation (list[list])

    Methods:
        get_trial_data(trial: int): Returns a single trial's economic data
    """

    stock_returns: list[np.ndarray]
    bond_returns: list[np.ndarray]
    real_estate_returns: list[np.ndarray]
    inflation: list[list]

    def __repr__(self) -> str:
        return "Economic Data"

    def get_trial_data(self, trial: int) -> EconomicTrialData:
        """Returns a single trial's economic data

        Args:
            trial (int): trial number

        Returns:
            EconomicTrialData: 1D arrays of economic data
        """
        return EconomicTrialData(
            stock_returns=self.stock_returns[trial],
            bond_returns=self.bond_returns[trial],
            real_estate_returns=self.real_estate_returns[trial],
            inflation=self.inflation[trial],
        )


@dataclass
class Generator:
    """Generates economic data for a simulation

    Attributes:
        intervals_per_trial (int): number of intervals per trial
        (ex: 42 for 10.5 years of quarterly intervals)

        trial_qty (int): number of trials to run
    """

    intervals_per_trial: int
    trial_qty: int

    def gen_economic_engine_data(self) -> EconomicEngineData:
        """Generates and returns stock, bond, real estate, and inflation data

        Returns:
            EconomicData: 2D arrays of economic data
        """
        return EconomicEngineData(
            stock_returns=self._generate_2d_rates(STOCK_BEHAVIOR),
            bond_returns=self._generate_2d_rates(BOND_BEHAVIOR),
            real_estate_returns=self._generate_2d_rates(REAL_ESTATE_BEHAVIOR),
            inflation=self._generate_2d_inflation(),
        )

    def _generate_2d_rates(
        self, investment_behavior: InvestmentBehavior
    ) -> list[np.ndarray]:
        """Generate a two dimensional array of rates.

        An array of rates for each simulation trial.

        Parameters:
            investment_behavior (InvestmentBehavior): characteristics of the investment

        Returns:
            list[np.ndarray]: 2D array. Outer list is each trial run. Inner list is rates.

        """
        rate_matrix = [
            self._generate_1d_restricted_rates(
                investment_behavior.gen_interval_behavior()
            )[0]
            for _ in range(self.trial_qty)
        ]
        return rate_matrix

    def _generate_1d_restricted_rates(
        self, interval_behavior: InvestmentBehavior
    ) -> tuple[np.ndarray, int]:
        """Uses brute force to generate a single dimension array of rates with
        an annualized return that is within the given bounds.



        Parameters:
            interval_behavior (InvestmentBehavior): interval characteristics of the investment,
            created using the `<InvestmentBehavior>.gen_interval_behavior` method

        Returns:
            np.ndarray: array of rates

            int: number of iterations to find a valid set of rates
        """
        # Since values need to be tested against annualized limits,
        # slightly more data may be generated since years need to be tested
        # in whole quantities, not fractional. Ex: If you need 10 quarters
        # (2.5 years) of data. year_qty must be 3
        year_qty = math.ceil(self.intervals_per_trial / INTERVALS_PER_YEAR)
        # In the case of 4 intervals per year, interval_behavior is the
        # behavior of the investment over the course of a single quarter.
        iter_cnt = 0
        annualized_return = 0
        while (
            annualized_return < interval_behavior.annualized_low
            or annualized_return > interval_behavior.annualized_high
        ):
            yields = rng.normal(
                loc=interval_behavior.mean_yield,
                scale=interval_behavior.stdev,
                size=year_qty * INTERVALS_PER_YEAR,
            )
            annualized_return = pow(np.prod(yields), 1 / year_qty)
            iter_cnt += 1
        rates = yields - 1
        trimmed_rates = rates[: self.intervals_per_trial]
        return trimmed_rates, iter_cnt

    def _generate_2d_inflation(self) -> list[list]:
        """Generate randomized inflation with a skew

        Returns:
            list[list]: each list has inflation growing cumulatively
        """
        interval_behavior = INFLATION_BEHAVIOR.gen_interval_behavior()
        distribution = self._create_skew_dist(
            interval_behavior.mean_yield,
            interval_behavior.stdev,
            interval_behavior.skew,
            size=self.intervals_per_trial * self.trial_qty,
            debug=False,
        )
        random.shuffle(distribution)  # create_skew_dist returns ordered items
        # convert to np array for split, then convert back to 2D list
        array = np.array(distribution)
        chunked_arrays = np.array_split(array, indices_or_sections=self.trial_qty)
        inflation_matrix = [list(array) for array in chunked_arrays]
        # convert individual inflation yields to cumulative inflation yields
        for i in range(self.trial_qty):
            for j in range(1, self.intervals_per_trial):
                inflation_matrix[i][j] *= inflation_matrix[i][j - 1]
        return inflation_matrix

    def _create_skew_dist(
        self, mean: float, stdev: float, skew: float, size: int, debug: bool = False
    ) -> np.ndarray:
        """Creates a single dimension array with skewed distribution given skew parameter

        https://stackoverflow.com/questions/49801071/how-can-i-use-skewnorm-to-produce-a-distribution-with-the-specified-skew/58111859#58111859

        Args:
            mean (float)

            std (float): standard diviation

            skew (float)

            size (int): total qty desired

            debug (bool, optional): Create plot of distribution. Defaults to False

        Returns:
            np.ndarray: list skewed values with size = size
        """

        # Calculate the degrees of freedom 1 required to obtain the
        # specific skewness statistic, derived from simulations
        loglog_slope = -2.211897875506251
        loglog_intercept = 1.002555437670879
        df2 = 500
        df1 = 10 ** (loglog_slope * np.log10(abs(skew)) + loglog_intercept)

        # Sample from F distribution
        fsample = np.sort(stats.f(df1, df2).rvs(size=size))

        # Adjust the variance by scaling the distance from each point to
        # the distribution mean by a constant, derived from simulations
        k1_slope = 0.5670830069364579
        k1_intercept = -0.09239985798819927
        k2_slope = 0.5823114978219056
        k2_intercept = -0.11748300123471256

        scaling_slope = abs(skew) * k1_slope + k1_intercept
        scaling_intercept = abs(skew) * k2_slope + k2_intercept

        scale_factor = (stdev - scaling_intercept) / scaling_slope
        new_dist = (fsample - np.mean(fsample)) * scale_factor + fsample

        # flip the distribution if specified skew is negative
        if skew < 0:
            new_dist = np.mean(new_dist) - new_dist

        # adjust the distribution mean to the specified value
        final_dist = new_dist + (mean - np.mean(new_dist))

        if debug:
            import matplotlib.pyplot as plt  # pylint: disable=import-outside-toplevel # lazy import
            import seaborn as sns  # pylint: disable=import-outside-toplevel # lazy import

            print("Input mean: ", mean)
            print("Result mean: ", np.mean(final_dist), "\n")

            print("Input SD: ", stdev)
            print("Result SD: ", np.std(final_dist), "\n")

            print("Input skew: ", skew)
            print("Result skew: ", stats.skew(final_dist))
            # inspect the plots & moments, try random sample
            _, axis = plt.subplots(figsize=(12, 7))
            sns.distplot(
                final_dist,
                hist=True,
                ax=axis,
                color="green",
                label="generated distribution",
            )
            axis.legend()
            plt.show()

        return final_dist


class Controller:
    """Manages trial economic data

    Args:
        economic_engine_data (EconomicEngineData): Full set of economic data

        trial (int): trial number

    Methods:
        get_economic_state_data(state: State): Returns economic data for a single state
    """

    def __init__(self, economic_engine_data: EconomicEngineData, trial: int):
        self._economic_trial_data = economic_engine_data.get_trial_data(trial)

    def get_economic_state_data(self, state: State) -> EconomicStateData:
        """Returns economic data for a single state"""
        return self._economic_trial_data.get_state_data(state.interval_idx)

"""Generates randomized economic data for stocks, bonds, real estate and inflation.

Return/rate/yield definitions: something that has a 3% growth is a
0.03 return/rate and 1.03 yield

This module contains the following classes:

    * VariableMix: A collection of variables and their statistics
    * VariableMixRepo: Abstract base class for repositories that provide a mix of economic variables
    * CsvVariableMixRepo: A VariableMixRepo that reads data from CSV files
    * EconomicStateData: Economic data for a single state
    * EconomicTrialData: Economic data for a single trial
    * EconomicSimData: Economic data for the entire simulation
    * EconomicEngine: A class representing an economic engine that generates simulated economic data
    * Controller: Manages trial economic data
"""

from abc import ABC, abstractmethod
import csv
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np
from numpy.typing import NDArray
from app.util import interval_stdev, interval_yield

rng = np.random.default_rng()


@dataclass
class _StatisticBehavior:
    mean_yield: float
    stdev: float

    def gen_interval_behavior(self):
        """Returns Behavior object with modified mean_yield and stdev for the defined interval"""
        return _StatisticBehavior(
            mean_yield=interval_yield(self.mean_yield),
            stdev=interval_stdev(self.stdev),
        )


@dataclass
class VariableMix:
    """A collection of variables and their statistics

    Attributes:
        variable_stats (list[_StatisticBehavior]): list of variable statistics

        correlation_matrix (np.ndarray): matrix of variable correlations

        lookup_table (dict[str, int]): lookup table for variable names
    """

    variable_stats: list[_StatisticBehavior]
    correlation_matrix: NDArray[np.floating]
    lookup_table: dict[str, int]


class VariableMixRepo(ABC):
    """Abstract base class for repositories that provide a mix of economic variables."""

    @abstractmethod
    def get_variable_mix(self) -> VariableMix:
        """Get a mix of economic variables.

        Returns:
            VariableMix: An object representing a mix of economic variables.
        """
        raise NotImplementedError


class CsvVariableMixRepo(VariableMixRepo):
    """A VariableMixRepo that reads data from CSV files.

    Methods:
        get_variable_mix(): Get a mix of economic variables.
    """

    def __init__(self, statistics_path: Path, correlation_path: Path):
        self._statistics_path = statistics_path
        self._correlation_path = correlation_path
        self._lookup_table = {}
        self._variable_mix = self._gen_variable_mix()

    def get_variable_mix(self) -> VariableMix:
        return self._variable_mix

    def _gen_variable_mix(self) -> VariableMix:
        variable_stats = self._process_statistics_data()
        correlation_matrix = self._process_correlation_data()
        return VariableMix(
            variable_stats=variable_stats,
            correlation_matrix=correlation_matrix,
            lookup_table=self._lookup_table,
        )

    def _process_statistics_data(self) -> list[_StatisticBehavior]:
        with open(self._statistics_path, "r", encoding="utf-8") as file:
            csv_reader = csv.reader(file, skipinitialspace=True)
            next(csv_reader)
            label_idx = 0
            mean_idx = 1
            stdev_idx = 2
            data = []
            for idx, csv_row in enumerate(csv_reader):
                data.append(
                    _StatisticBehavior(
                        mean_yield=float(csv_row[mean_idx]),
                        stdev=float(csv_row[stdev_idx]),
                    )
                )
                self._lookup_table[csv_row[label_idx]] = idx
            return data

    def _process_correlation_data(self):
        with open(self._correlation_path, "r", encoding="utf-8") as file:
            csv_reader = csv.reader(file, skipinitialspace=True)
            next(csv_reader)
            variable_1_idx = 0
            variable_2_idx = 1
            correlation_idx = 2
            correlation_matrix = np.ones(
                (len(self._lookup_table), len(self._lookup_table))
            )
            for csv_row in csv_reader:
                variable_1 = csv_row[variable_1_idx]
                variable_2 = csv_row[variable_2_idx]
                correlation_matrix[self._lookup_table[variable_1]][
                    self._lookup_table[variable_2]
                ] = csv_row[correlation_idx]
                correlation_matrix[self._lookup_table[variable_2]][
                    self._lookup_table[variable_1]
                ] = csv_row[correlation_idx]
            return correlation_matrix


def _gen_covariance_matrix(variable_mix: VariableMix):
    standard_deviations = np.array(
        [asset.gen_interval_behavior().stdev for asset in variable_mix.variable_stats]
    )
    return (
        np.outer(standard_deviations, standard_deviations)
        * variable_mix.correlation_matrix
    )


def _gen_covariated_data(
    variable_mix: VariableMix,
    trial_qty: int,
    intervals_per_trial: int,
    seeded: bool = False,
) -> np.ndarray:
    """
    Generates correlated rates for a given variable mix.

    Args:
        variable_mix (VariableMix): The variables to generate rates for.
        trial_qty (int): The number of trials to run.
        intervals_per_trial (int): The number of intervals per trial.
        seeded (bool, optional): Whether or not to seed the random number generator.
        Defaults to False.

    Returns:
        np.ndarray: A 3D array of covariated data.
    """
    if seeded:
        np.random.seed(0)
    covariance_matrix = _gen_covariance_matrix(variable_mix)
    interval_yields = [
        asset.gen_interval_behavior().mean_yield
        for asset in variable_mix.variable_stats
    ]
    yield_matrix = np.random.multivariate_normal(
        mean=interval_yields,
        cov=covariance_matrix,
        size=(trial_qty, intervals_per_trial),
    )
    return yield_matrix


@dataclass
class EconomicStateData:
    """Economic data for a single state

    Attributes:
        asset_rates (np.ndarray): 1D array of asset rates

        inflation (float)

        asset_lookup (dict[str, int])
    """

    asset_rates: NDArray[np.floating]
    inflation: float
    asset_lookup: dict[str, int]

    def __repr__(self) -> str:
        return "Economic Data"


@dataclass
class EconomicTrialData:
    """Economic data for a single trial

    Attributes:
        asset_rates (np.ndarray): 2D array of asset rates

        inflation (np.ndarray): 1D array of inflation rates

        asset_lookup (dict[str, int])

    Methods:
        get_state_data(interval_idx: int): Returns a single state's economic data
    """

    asset_rates: NDArray[np.floating]
    inflation: NDArray[np.floating]
    asset_lookup: dict[str, int]

    def __repr__(self) -> str:
        return "Economic Data"

    def get_state_data(self, interval: int) -> EconomicStateData:
        """Returns a single state's economic data

        Args:
            interval_idx (int): interval count

        Returns:
            EconomicStateData: Economic data for a single state
        """
        return EconomicStateData(
            asset_rates=self.asset_rates[interval],
            inflation=self.inflation[interval],
            asset_lookup=self.asset_lookup,
        )


@dataclass
class EconomicSimData:
    """Economic data for the entire simulation

    Attributes:
        asset_rates (np.ndarray): 3D array of asset rates

        inflation (np.ndarray): 2D array of inflation rates

        asset_lookup (dict[str, int])

    Methods:
        get_trial_data(trial: int): Returns a single trial's economic data
    """

    asset_rates: NDArray[np.floating]
    inflation: NDArray[np.floating]
    asset_lookup: dict[str, int]

    def __repr__(self) -> str:
        return "Economic Data"

    def _get_trial_data(self, trial: int) -> EconomicTrialData:
        """Returns a single trial's economic data

        Args:
            trial (int): trial number

        Returns:
            EconomicTrialData: 1D arrays of economic data
        """
        return EconomicTrialData(
            asset_rates=self.asset_rates[trial],
            inflation=self.inflation[trial],
            asset_lookup=self.asset_lookup,
        )


class EconomicEngine:
    """A class representing an economic engine that generates simulated economic data.

    Attributes:
        data (EconomicSimData): Economic data for the entire simulation
    """

    def __init__(
        self,
        intervals_per_trial: int,
        trial_qty: int,
        variable_mix_repo: VariableMixRepo,
    ):
        self._intervals_per_trial = intervals_per_trial
        self._trial_qty = trial_qty
        self._variable_mix = variable_mix_repo.get_variable_mix()
        self._asset_data: Optional[NDArray[np.floating]] = None
        self._inflation_data: Optional[NDArray[np.floating]] = None
        self._lookup_table: Optional[dict[str, int]] = None
        self.data = self._gen_data()

    def _gen_data(self) -> EconomicSimData:
        covariated_data = _gen_covariated_data(
            variable_mix=self._variable_mix,
            trial_qty=self._trial_qty,
            intervals_per_trial=self._intervals_per_trial,
        )
        self._split_inflation_from_assets(covariated_data)
        assert self._asset_data is not None
        assert self._inflation_data is not None
        assert self._lookup_table is not None
        self._make_inflation_cumulative()

        return EconomicSimData(
            asset_rates=self._asset_data - 1,
            inflation=self._inflation_data,
            asset_lookup=self._lookup_table,
        )

    def _split_inflation_from_assets(self, data: NDArray[np.floating]):
        inflation_idx = self._variable_mix.lookup_table["Inflation"]
        self._inflation_data = data[:, :, inflation_idx]
        self._asset_data = np.delete(data, inflation_idx, axis=2)
        self._lookup_table = {
            k: idx
            for k, idx in self._variable_mix.lookup_table.items()
            if idx != inflation_idx
        }
        for k, idx in self._lookup_table.items():
            if idx > inflation_idx:
                self._lookup_table[k] = idx - 1

    def _make_inflation_cumulative(self):
        assert self._inflation_data is not None
        for i in range(self._trial_qty):
            for j in range(1, self._intervals_per_trial):
                self._inflation_data[i][j] *= self._inflation_data[i][j - 1]


class Controller:
    """Manages trial economic data

    Args:
        economic_engine_data (EconomicEngineData): Full set of economic data

        trial (int): trial number

    Methods:
        get_economic_state_data(state: State): Returns economic data for a single state
    """

    def __init__(self, economic_sim_data: EconomicSimData, trial: int):
        self._economic_trial_data = economic_sim_data._get_trial_data(trial)

    def get_economic_state_data(self, state_interval_idx: int) -> EconomicStateData:
        """Returns economic data for a single state"""
        return self._economic_trial_data.get_state_data(state_interval_idx)

    def get_economic_trial_data(self) -> EconomicTrialData:
        """Returns economic data for the associated trial"""
        return self._economic_trial_data

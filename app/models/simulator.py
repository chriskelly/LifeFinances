"""Simulator module

Engine is responsible for generating trials,
trials are responsible for generating intervals,
intervals are responsible for generating states and StateChangeComponentss.
Generation functions should be in the same module as the class they generate.

Classes:
    SimulationTrial: A single simulation trial representing one modeled lifetime
    
    ResultsLabels: Labels for the columns in the results DataFrame
    
    Results: Results of a series of simulation trials
    
    SimulationEngine: Simulation Controller

Functions:
    gen_simulation_results(): Generates a Results object
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import pandas as pd
from app.data import constants
from app.models.config import User, get_config
from app.models.controllers import (
    Controllers,
    allocation,
    economic_data,
    job_income,
    pension,
    social_security,
    annuity,
)
from app.models.financial.interval import gen_first_interval


class SimulationTrial:
    """A single simulation trial representing one modeled lifetime

    Allocation and Job Income controllers are passed in
    since the same controller can be used for all Trials.

    Remaining controllers are generated fresh
    for every Trial.

    Arguments:
        user_config (User)

        allocation_controller (allocation.Controller)

        economic_data_controller (economic_data.Controller)

        job_income_controller (job_income.Controller)

    Attributes:
        intervals (list[Interval])
    """

    def __init__(
        self,
        user_config: User,
        allocation_controller: allocation.Controller,
        economic_data_controller: economic_data.Controller,
        job_income_controller: job_income.Controller,
    ):
        self._user_config = user_config
        self.controllers = Controllers(
            allocation=allocation_controller,
            economic_data=economic_data_controller,
            job_income=job_income_controller,
            social_security=social_security.Controller(
                user_config=user_config, income_controller=job_income_controller
            ),
            pension=pension.Controller(user_config),
            annuity=annuity.Controller(user_config),
        )
        self.intervals = [gen_first_interval(user_config, self.controllers)]
        for _ in range(self._user_config.intervals_per_trial - 1):
            self.intervals.append(
                self.intervals[-1].gen_next_interval(self.controllers)
            )

    def get_success(self) -> bool:
        """Returns True if the trial ended with a positive net worth"""
        return self.intervals[-1].state.net_worth > 0


class ResultLabels(Enum):
    """Labels for the columns in the results DataFrame"""

    DATE = "Date"
    NET_WORTH = "Net Worth"
    INFLATION = "Inflation"
    JOB_INCOME = "Job Income"
    SS_USER = "SS User"
    SS_PARTNER = "SS Partner"
    PENSION = "Pension"
    TOTAL_INCOME = "Total Income"
    SPENDING = "Spending"
    KIDS = "Kids"
    INCOME_TAXES = "Income Taxes"
    MEDICARE_TAXES = "Medicare Taxes"
    SOCIAL_SECURITY_TAXES = "Social Security Taxes"
    PORTFOLIO_TAXES = "Portfolio Taxes"
    TOTAL_TAXES = "Total Taxes"
    TOTAL_COSTS = "Total Costs"
    PORTFOLIO_RETURN = "Portfolio Return"
    ANNUITY = "Annuity"
    NET_TRANSACTION = "Net Transaction"


@dataclass
class Results:
    """Results of a series of simulation trials

    Attributes
        trials (list[SimulationTrial])
    """

    trials: list[SimulationTrial] = None
    _state_columns = [label.value for label in ResultLabels]
    _allocation_columns: list[str] = None
    _performance_columns: list[str] = None

    def as_dataframes(self) -> list[pd.DataFrame]:
        """
        Returns a list of pandas DataFrames, where each DataFrame
        represents a trial in the simulator.
        """
        self._set_asset_columns()
        dataframes = []
        for trial in self.trials:
            states_df = self._gen_states_df(trial)
            allocations_df = self._gen_allocations_df(trial)
            asset_performances_df = self._gen_asset_performances_df(trial)
            df = pd.concat([states_df, allocations_df, asset_performances_df], axis=1)
            dataframes.append(df)
        return dataframes

    def _set_asset_columns(self) -> list[str]:
        """Sets asset column names"""
        asset_lookup = (
            self.trials[0]
            .controllers.economic_data.get_economic_trial_data()
            .asset_lookup
        )
        asset_columns = [None] * len(asset_lookup)
        for asset, index in asset_lookup.items():
            asset_columns[index] = asset
        self._allocation_columns = [f"{asset}_%" for asset in asset_columns]
        self._performance_columns = [f"{asset}_rate" for asset in asset_columns]

    def _gen_states_df(self, trial: SimulationTrial) -> pd.DataFrame:
        data = [
            [
                interval.state.date,
                interval.state.net_worth,
                interval.state.inflation,
                interval.state_change_components.net_transactions.income.job_income,
                interval.state_change_components.net_transactions.income.social_security_user,
                interval.state_change_components.net_transactions.income.social_security_partner,
                interval.state_change_components.net_transactions.income.pension,
                interval.state_change_components.net_transactions.income.sum,
                interval.state_change_components.net_transactions.costs.spending,
                interval.state_change_components.net_transactions.costs.kids,
                interval.state_change_components.net_transactions.costs.taxes.income,
                interval.state_change_components.net_transactions.costs.taxes.medicare,
                interval.state_change_components.net_transactions.costs.taxes.social_security,
                interval.state_change_components.net_transactions.costs.taxes.portfolio,
                interval.state_change_components.net_transactions.costs.taxes.sum,
                interval.state_change_components.net_transactions.costs.sum,
                interval.state_change_components.net_transactions.portfolio_return,
                interval.state_change_components.net_transactions.annuity,
                interval.state_change_components.net_transactions.sum,
            ]
            for interval in trial.intervals
        ]
        return pd.DataFrame(data, columns=self._state_columns)

    def _gen_allocations_df(self, trial: SimulationTrial) -> pd.DataFrame:
        """Returns a DataFrame of allocation data"""
        return pd.DataFrame(
            [
                interval.state_change_components.allocation
                for interval in trial.intervals
            ],
            columns=self._allocation_columns,
        )

    def _gen_asset_performances_df(self, trial: SimulationTrial) -> pd.DataFrame:
        """Returns a DataFrame of asset performance data"""
        economic_trial_data = trial.controllers.economic_data.get_economic_trial_data()
        return pd.DataFrame(
            economic_trial_data.asset_rates, columns=self._performance_columns
        )

    def calc_success_rate(self) -> float:
        """Returns the rate of trials that ended with a positive net worth"""
        return sum(trial.get_success() for trial in self.trials) / len(self.trials)

    def calc_success_percentage(self) -> str:
        """Returns the formatted percentage of trials that ended with a positive net worth"""
        return str(round(100 * self.calc_success_rate(), ndigits=1))


class SimulationEngine:
    """Simulation Controller

    Args:
        config_path (Path): Path to user config file. Defaults to constants.CONFIG_PATH.
        trial_qty (int): Number of trials to run

    Attributes
        results (Results)

    Methods
        gen_all_trials()
    """

    def __init__(
        self, config_path: Path = constants.CONFIG_PATH, trial_qty: int = None
    ):
        self._user_config = get_config(config_path)
        self.results: Results = Results()
        self._trial_qty = trial_qty or self._user_config.trial_quantity
        self._economic_sim_data = economic_data.EconomicEngine(
            intervals_per_trial=self._user_config.intervals_per_trial,
            trial_qty=self._trial_qty,
            variable_mix_repo=economic_data.CsvVariableMixRepo(
                statistics_path=constants.STATISTICS_PATH,
                correlation_path=constants.CORRELATION_PATH,
            ),
        ).data

    def gen_all_trials(self):
        """Create trials and save to `self.results`"""
        allocation_controller = allocation.Controller(
            user=self._user_config, asset_lookup=self._economic_sim_data.asset_lookup
        )
        job_income_controller = job_income.Controller(self._user_config)

        self.results.trials = [
            SimulationTrial(
                user_config=self._user_config,
                allocation_controller=allocation_controller,
                economic_data_controller=economic_data.Controller(
                    economic_sim_data=self._economic_sim_data, trial=i
                ),
                job_income_controller=job_income_controller,
            )
            for i in range(self._trial_qty)
        ]


def gen_simulation_results() -> Results:
    """Runs a simulation and returns the results"""
    engine = SimulationEngine()
    engine.gen_all_trials()
    return engine.results

"""Simulator module

Engine is responsible for generating trials,
trials are responsible for generating intervals,
intervals are responsible for generating states and StateChangeComponentss.
Generation functions should be in the same module as the class they generate.

Classes:
    SimulationTrial: A single simulation trial representing one modeled lifetime
    
    Results:
    
    SimulationEngine:
"""
from dataclasses import dataclass
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
        self._controllers = Controllers(
            allocation=allocation_controller,
            economic_data=economic_data_controller,
            job_income=job_income_controller,
            social_security=social_security.Controller(
                user_config=user_config, income_controller=job_income_controller
            ),
            pension=pension.Controller(user_config),
            annuity=annuity.Controller(user_config),
        )
        self.intervals = [gen_first_interval(user_config, self._controllers)]
        for _ in range(self._user_config.intervals_per_trial - 1):
            self.intervals.append(
                self.intervals[-1].gen_next_interval(self._controllers)
            )


@dataclass
class Results:
    """Results of a series of simulation trials

    Attributes
        trials (list[SimulationTrial])
    """

    trials: list[SimulationTrial] = None

    def as_dataframes(self) -> list[pd.DataFrame]:
        """
        Returns a list of pandas DataFrames, where each DataFrame
        represents a trial in the simulator.
        """
        columns = [
            "Date",
            "Net Worth",
            "Inflation",
            "Job Income",
            "SS User",
            "SS Partner",
            "Pension",
            "Total Income",
            "Spending",
            "Kids",
            "Income Taxes",
            "Medicare Taxes",
            "Social Security Taxes",
            "Portfolio Taxes",
            "Total Taxes",
            "Total Costs",
            "Portfolio Return",
            "Annuity",
            "Net Transaction",
        ]
        dataframes = []
        for trial in self.trials:
            data = [
                [
                    interval.state.date,
                    interval.state.net_worth,
                    interval.state.inflation,
                    interval.state_change_components.net_transactions.income.job_income,
                    interval.state_change_components.net_transactions.income.social_security_user,
                    interval.state_change_components.net_transactions.income.social_security_partner,
                    interval.state_change_components.net_transactions.income.pension,
                    interval.state_change_components.net_transactions.income,
                    interval.state_change_components.net_transactions.costs.spending,
                    interval.state_change_components.net_transactions.costs.kids,
                    interval.state_change_components.net_transactions.costs.taxes.income,
                    interval.state_change_components.net_transactions.costs.taxes.medicare,
                    interval.state_change_components.net_transactions.costs.taxes.social_security,
                    interval.state_change_components.net_transactions.costs.taxes.portfolio,
                    interval.state_change_components.net_transactions.costs.taxes,
                    interval.state_change_components.net_transactions.costs,
                    interval.state_change_components.net_transactions.portfolio_return,
                    interval.state_change_components.net_transactions.annuity,
                    interval.state_change_components.net_transactions,
                ]
                for interval in trial.intervals
            ]
            df = pd.DataFrame(data, columns=columns)
            dataframes.append(df)
        return dataframes

    def success_rate(self) -> float:
        """Returns the percentage of trials that ended with a positive net worth"""
        return sum(
            trial.intervals[-1].state.net_worth > 0 for trial in self.trials
        ) / len(self.trials)


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

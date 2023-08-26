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
from dataclasses import dataclass, field
from app.models.config import User, get_config
from app.models.controllers import (
    Controllers,
    allocation,
    economic_data,
    job_income,
    social_security,
)
from app.models.financial.interval import Interval, gen_first_interval


@dataclass
class SimulationTrial:
    """A single simulation trial representing one modeled lifetime

    Attributes
        user_config (User)

        controllers (Controllers)

        intervals (list[Interval])

    Methods
        run()
    """

    user_config: User = None
    controllers: Controllers = Controllers()
    intervals: list[Interval] = field(default_factory=list)

    def run(self):
        """Generates subsequent intervals"""
        for _ in range(self.user_config.intervals_per_trial - 1):
            self.intervals.append(
                self.intervals[-1].gen_next_interval(self.controllers)
            )


def gen_trial(
    user_config: User,
    allocation_controller: allocation.Controller,
    economic_data_controller: economic_data.Controller,
    job_income_controller: job_income.Controller,
) -> SimulationTrial:
    """Generate a single simulation trial given the current user config

    Allocation and Job Income controllers are passed in
    since the same controller can be used for all Trials.

    Social Security, Annuity, and Pension controllers are generated fresh
    for every Trial.

    Economic Engine Data is parsed into individual Trial data classes before
    being passed in.

    Args:
        economic_data_controller (economic_data.Controller)
    """
    trial = SimulationTrial(user_config)
    trial.controllers.allocation = allocation_controller
    trial.controllers.economic_data = economic_data_controller
    trial.controllers.job_income = job_income_controller
    trial.controllers.social_security = social_security.Controller(
        user_config=user_config, income_controller=job_income_controller
    )
    # trial.controllers.annuity=annuity.Controller(),
    # trial.controllers.pension=pension.Controller(),
    trial.intervals.append(gen_first_interval(trial.user_config, trial.controllers))
    trial.run()
    return trial


@dataclass
class Results:
    """Results of a series of simulation trials

    Attributes
        trials (list[SimulationTrial])
    """

    trials: list[SimulationTrial] = None


class SimulationEngine:
    """Simulation Controller

    Attributes
        results (Results)

        trial_qty (int): Number of trials to run

        economic_data (EconomicData): Full set of economic data

    Methods
        gen_all_trials()
    """

    def __init__(self, trial_qty: int = None):
        user_config = get_config()
        self.results: Results = Results()
        self.trial_qty = trial_qty or user_config.trial_quantity
        self.economic_engine_data = economic_data.Generator(
            intervals_per_trial=user_config.intervals_per_trial,
            trial_qty=self.trial_qty,
        ).gen_economic_engine_data()

    def gen_all_trials(self):
        """Create trials and save to `self.results`"""
        user_config = get_config()
        allocation_controller = allocation.Controller(user_config)
        job_income_controller = job_income.Controller(user_config)

        self.results.trials = [
            gen_trial(
                user_config=user_config,
                allocation_controller=allocation_controller,
                economic_data_controller=economic_data.Controller(
                    self.economic_engine_data, i
                ),
                job_income_controller=job_income_controller,
            )
            for i in range(self.trial_qty)
        ]

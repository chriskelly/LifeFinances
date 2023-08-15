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
from app.data import constants
from app.models.config import User, get_config
from app.models.controllers import Controllers, allocation, economic_data
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


def gen_trial(economic_data_controller: economic_data.Controller) -> SimulationTrial:
    """Generate a single simulation trial given the current user config

    Args:
        economic_data_controller (economic_data.Controller)
    """
    trial = SimulationTrial(user_config=get_config())
    trial.controllers.allocation = allocation.Controller(trial.user_config)
    trial.controllers.economic_data = economic_data_controller
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

    def __init__(self):
        user_config = get_config()
        self.results: Results = Results()
        self.trial_qty = user_config.trial_quantity
        self.economic_engine_data = economic_data.Generator(
            intervals_per_trial=int(
                (user_config.calculate_til - constants.TODAY_YR_QT) / 0.25
            ),
            intervals_per_year=4,
            trial_qty=user_config.trial_quantity,
        ).gen_economic_engine_data()

    def gen_all_trials(self):
        """Create trials and save to `self.results`"""

        self.results.trials = [
            gen_trial(economic_data.Controller(self.economic_engine_data, i))
            for i in range(self.trial_qty)
        ]

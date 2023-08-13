"""Simulator module

Classes:
    SimulationTrial: A single simulation trial representing one modeled lifetime
    
    Results:
    
    SimulationEngine:
"""
from dataclasses import dataclass, field
from app.models.config import User, get_config
from app.models.controllers import Controllers, allocation
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


def gen_trial() -> SimulationTrial:
    """Generate a single simulation trial given the current user config"""
    trial = SimulationTrial(user_config=get_config())
    trial.controllers.allocation = allocation.Controller(trial.user_config)
    trial.intervals.append(gen_first_interval(trial.user_config))
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

    Methods
        gen_all_trials()
    """

    def __init__(self, trial_qty: int = 1):
        self.results: Results = Results()
        self.trial_qty = trial_qty

    def gen_all_trials(self):
        """Create trials and save to `self.results`"""

        self.results.trials = [gen_trial() for _ in range(self.trial_qty)]

"""Simulator module

Classes:
    SimulationTrial: A single simulation trial representing one modeled lifetime
    
    Results:
    
    SimulationEngine:
"""
from dataclasses import dataclass
from app.models.financial.interval import Interval, gen_first_interval


class SimulationTrial:
    """A single simulation trial representing one modeled lifetime

    Attributes
        intervals (list[Interval])

    Methods
        run()
    """

    def __init__(self):
        self.intervals: list[Interval] = [gen_first_interval()]
        self.run()

    def run(self):
        """Generates subsequent intervals"""


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

    Methods
        gen_num_trials(n: int)
    """

    def __init__(self):
        self.results: Results = Results()

    def gen_num_trials(self, num: int):
        """Create n trials and save to `self.results`"""
        self.results.trials = [SimulationTrial() for _ in range(num)]

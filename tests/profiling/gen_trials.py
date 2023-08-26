"""Generate all trials for profiling.
Reference for Snakeviz: https://jiffyclub.github.io/snakeviz/
"""
from app.models.simulator import SimulationEngine


engine = SimulationEngine()
engine.gen_all_trials()

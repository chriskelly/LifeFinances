"""Generate all trials for profiling. Cmd `make profile` to run.
Reference for Snakeviz: https://jiffyclub.github.io/snakeviz/
"""

from app.models.simulator import SimulationEngine

engine = SimulationEngine(trial_qty=1000)
engine.gen_all_trials()

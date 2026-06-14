"""Monthly TPAW simulation engine."""

from core.timeline import horizon_months, person_end_date

from simulation.result import STUB_VERSION, SimulationResult
from simulation.stub import run_simulation

__all__ = [
    "STUB_VERSION",
    "SimulationResult",
    "horizon_months",
    "person_end_date",
    "run_simulation",
]

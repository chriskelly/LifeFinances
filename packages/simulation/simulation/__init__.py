"""Monthly TPAW simulation engine."""

from core.timeline import horizon_months, person_end_date

from simulation.engine import simulate_monthly
from simulation.market_data import (
    HistoricalReturns,
    InflationResolved,
    ReturnPaths,
    build_return_paths,
    load_historical_returns,
    resolve_inflation,
)
from simulation.preprocess import preprocess
from simulation.result import ENGINE_VERSION, SimulationResult
from simulation.stub import run_simulation

__all__ = [
    "ENGINE_VERSION",
    "HistoricalReturns",
    "InflationResolved",
    "ReturnPaths",
    "SimulationResult",
    "build_return_paths",
    "horizon_months",
    "load_historical_returns",
    "person_end_date",
    "preprocess",
    "resolve_inflation",
    "run_simulation",
    "simulate_monthly",
]

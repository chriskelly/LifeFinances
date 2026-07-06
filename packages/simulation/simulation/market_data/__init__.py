"""Market data: vendored historical returns, bootstrap sampler, inflation, live feeds."""

from simulation.market_data.bootstrap import ReturnPaths, build_return_paths
from simulation.market_data.inflation import InflationResolved, resolve_inflation
from simulation.market_data.returns import HistoricalReturns, load_historical_returns
from simulation.market_data.sp500 import SP500Resolved, resolve_latest_sp500_close
from simulation.market_data.treasury import (
    TreasuryYieldsResolved,
    resolve_treasury_real_yields,
)

__all__ = [
    "HistoricalReturns",
    "InflationResolved",
    "ReturnPaths",
    "SP500Resolved",
    "TreasuryYieldsResolved",
    "build_return_paths",
    "load_historical_returns",
    "resolve_inflation",
    "resolve_latest_sp500_close",
    "resolve_treasury_real_yields",
]

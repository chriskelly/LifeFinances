from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from core.models import Plan

from simulation.market_data import load_historical_returns


@dataclass(frozen=True)
class PlanningReturns:
    annual_stocks: float
    annual_bonds: float
    annual_stock_log_variance: float


@lru_cache(maxsize=1)
def annual_stock_log_variance() -> float:
    stocks_log = load_historical_returns().stocks_log
    return float(np.var(stocks_log) * 12.0)


def resolve_planning_returns(plan: Plan) -> PlanningReturns:
    config = plan.planning_returns
    return PlanningReturns(
        annual_stocks=float(config.expected_annual_return_stocks),
        annual_bonds=float(config.expected_annual_return_bonds),
        annual_stock_log_variance=annual_stock_log_variance(),
    )

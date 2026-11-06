"""Resolve the market inputs shared by preprocessing and display-only summaries."""

from __future__ import annotations

from datetime import date, datetime

from core.models import Plan

from simulation.market_data.inflation import InflationResolved, resolve_inflation
from simulation.planning_returns import PlanningReturns, resolve_planning_returns


def resolve_market_inputs(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> tuple[InflationResolved, PlanningReturns]:
    """Resolve inflation and planning returns with one set of arguments."""
    today = today or date.today()
    inflation = resolve_inflation(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        api_key=fred_api_key,
    )
    planning = resolve_planning_returns(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        eod_api_key=eod_api_key,
    )
    return inflation, planning

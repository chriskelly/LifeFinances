"""Resolve the assumptions a simulation would use, without running one.

Display-only consumers (the Market assumptions editor) need the inflation and
planning-return snapshot, not the cashflow projection, return paths, or the
engine. This entrypoint skips all of them and leaves market-data refresh off by
default.
"""

from __future__ import annotations

from datetime import date, datetime

from core.models import Plan

from simulation.market_data.inflation import resolve_inflation
from simulation.planning_returns import resolve_planning_returns
from simulation.result import ResolvedAssumptions, build_resolved_assumptions


def resolve_assumptions(
    plan: Plan,
    *,
    today: date | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> ResolvedAssumptions:
    """Resolve the assumption snapshot without running the simulation."""
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
    return build_resolved_assumptions(
        inflation=inflation,
        planning=planning,
        preset=plan.planning_returns.preset,
    )

from __future__ import annotations

from datetime import date, datetime

from core.models import Plan

from simulation.engine import simulate_monthly
from simulation.market_data import build_return_paths
from simulation.preprocess import preprocess
from simulation.result import SimulationResult


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
    allow_refresh: bool = False,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> SimulationResult:
    _ = percentiles  # reserved for Phase 3d aggregation
    today = today or date.today()
    ran_at = ran_at or datetime.now()

    processed = preprocess(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        fred_api_key=fred_api_key,
        eod_api_key=eod_api_key,
    )
    paths = build_return_paths(plan, months_per_run=processed.months, today=today)
    return simulate_monthly(
        processed,
        stocks_return=paths.stocks_log_to_simple(),
        bonds_return=paths.bonds_log_to_simple(),
        ran_at=ran_at,
    )

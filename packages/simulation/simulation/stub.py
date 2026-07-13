from __future__ import annotations

from datetime import date, datetime

from core.models import Plan, normalize_percentiles

from simulation.aggregate import build_public_result
from simulation.composition import wealth_by_income_source
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
    now: datetime | None = None,
    fred_api_key: str | None = None,
    eod_api_key: str | None = None,
) -> SimulationResult:
    today = today or date.today()
    ran_at = ran_at or datetime.now()
    resolved = normalize_percentiles(
        percentiles if percentiles is not None else plan.advanced.percentiles
    )

    # `now` (tz-aware, drives market-data cache staleness) is intentionally
    # independent from `ran_at` (naive, only stamps the result) — the resolvers
    # default `now` to `datetime.now(tz=UTC)` on their own when unset.
    processed = preprocess(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        fred_api_key=fred_api_key,
        eod_api_key=eod_api_key,
    )
    paths = build_return_paths(plan, months_per_run=processed.months, today=today)
    raw = simulate_monthly(
        processed,
        stocks_return=paths.stocks_log_to_simple(),
        bonds_return=paths.bonds_log_to_simple(),
        ran_at=ran_at,
    )

    composition = wealth_by_income_source(
        gross_job=processed.gross_job,
        gross_social_security=processed.gross_social_security,
        gross_pension=processed.gross_pension,
        gross_manual=processed.gross_manual,
        taxes=processed.taxes,
        monthly_inflation=processed.monthly_inflation,
        monthly_bond_rate=processed.monthly_planning_bonds,
    )

    return build_public_result(
        raw,
        percentiles=resolved,
        composition=composition,
        start_month=(today.year, today.month),
    )

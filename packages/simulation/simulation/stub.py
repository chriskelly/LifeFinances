from __future__ import annotations

from datetime import date, datetime

import numpy as np
from core.models import Plan, normalize_percentiles

from domain import build_monthly_cashflows
from simulation.aggregate import build_public_result
from simulation.composition import wealth_by_income_source
from simulation.engine import simulate_monthly
from simulation.market_data import build_return_paths, resolve_inflation
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

    cashflows = build_monthly_cashflows(plan, today=today)
    inflation = resolve_inflation(
        plan,
        today=today,
        allow_refresh=allow_refresh,
        now=now,
        api_key=fred_api_key,
    )
    composition = wealth_by_income_source(
        gross_job=np.array([float(v) for v in cashflows.gross_job], dtype=np.float64),
        gross_social_security=np.array(
            [float(v) for v in cashflows.gross_social_security], dtype=np.float64
        ),
        gross_pension=np.array(
            [float(v) for v in cashflows.gross_pension], dtype=np.float64
        ),
        gross_manual=np.array(
            [float(v) for v in cashflows.gross_manual], dtype=np.float64
        ),
        taxes=np.array(
            [float(v) for v in cashflows.taxes.stored_total], dtype=np.float64
        ),
        monthly_inflation=inflation.monthly,
        monthly_bond_rate=processed.monthly_planning_bonds,
    )

    return build_public_result(
        raw,
        percentiles=resolved,
        composition=composition,
        start_month=(today.year, today.month),
    )

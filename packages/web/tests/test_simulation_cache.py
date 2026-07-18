from __future__ import annotations

from datetime import date, datetime

import numpy as np
from core.defaults import default_plan
from fastapi import FastAPI
from simulation.result import SimulationResult
from web.simulation_cache import CACHE_MAX_SIZE, fingerprint_plan, get_or_run_simulation


def _make_result() -> SimulationResult:
    horizon_months = 2
    percentiles = [5, 50, 95]
    shape = (len(percentiles), horizon_months)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon_months,
        num_runs=10,
        percentiles=list(percentiles),
        start_month=(2026, 1),
        balance_start=series.copy(),
        withdrawals_essential=series.copy(),
        withdrawals_discretionary=series.copy(),
        withdrawals_general=series.copy(),
        withdrawals_total=series.copy(),
        savings_stock_allocation=series.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
    )


def test_fingerprint_ignores_plan_name() -> None:
    plan = default_plan()
    renamed = plan.model_copy(update={"name": "Renamed plan"})

    assert fingerprint_plan(plan) == fingerprint_plan(renamed)


def test_different_today_reruns_simulation() -> None:
    app = FastAPI()
    plan = default_plan()
    call_count = {"n": 0}

    def run(plan, **kwargs):
        call_count["n"] += 1
        return _make_result()

    day_one = date(2026, 1, 1)
    day_two = date(2026, 1, 2)
    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=day_one,
    )
    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=day_two,
    )

    assert call_count["n"] == 2


def test_lru_evicts_oldest_entry_and_retains_recent_hit() -> None:
    app = FastAPI()
    plan = default_plan()
    call_count = {"n": 0}

    def run(plan, **kwargs):
        call_count["n"] += 1
        return _make_result()

    fixed_today = date(2026, 6, 1)
    for plan_id in range(CACHE_MAX_SIZE):
        get_or_run_simulation(
            app,
            plan_id=plan_id,
            plan=plan,
            fred_api_key=None,
            eod_api_key=None,
            run=run,
            today=fixed_today,
        )
    assert call_count["n"] == CACHE_MAX_SIZE

    # Touch oldest entry so it becomes most-recently used.
    get_or_run_simulation(
        app,
        plan_id=0,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE

    get_or_run_simulation(
        app,
        plan_id=CACHE_MAX_SIZE,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 1

    # plan_id=0 was touched; plan_id=1 should have been evicted.
    get_or_run_simulation(
        app,
        plan_id=0,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 1

    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        fred_api_key=None,
        eod_api_key=None,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 2

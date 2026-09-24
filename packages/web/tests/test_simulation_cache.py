from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pytest
from core.defaults import default_plan
from core.models import AppSettings
from fastapi import FastAPI
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult
from web.simulation_cache import CACHE_MAX_SIZE, fingerprint_plan, get_or_run_simulation


def _resolved_assumptions() -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.02,
        annual_stock_return=0.05,
        annual_bond_return=0.02,
        annual_stock_log_variance=0.03,
        planning_preset="fixed",
        inflation_source="manual",
    )


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
        diagnostics=empty_diagnostics(months=horizon_months),
        resolved_assumptions=_resolved_assumptions(),
    )


def _empty_settings() -> AppSettings:
    return AppSettings()


def test_fingerprint_ignores_plan_name() -> None:
    plan = default_plan()
    renamed = plan.model_copy(update={"name": "Renamed plan"})

    assert fingerprint_plan(plan) == fingerprint_plan(renamed)


def test_different_today_reruns_simulation() -> None:
    app = FastAPI()
    plan = default_plan()
    call_count = {"n": 0}
    settings = _empty_settings()

    def run(plan, **kwargs):
        call_count["n"] += 1
        return _make_result()

    day_one = date(2026, 1, 1)
    day_two = date(2026, 1, 2)
    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        settings=settings,
        run=run,
        today=day_one,
    )
    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        settings=settings,
        run=run,
        today=day_two,
    )

    assert call_count["n"] == 2


def test_lru_evicts_oldest_entry_and_retains_recent_hit() -> None:
    app = FastAPI()
    plan = default_plan()
    call_count = {"n": 0}
    settings = _empty_settings()

    def run(plan, **kwargs):
        call_count["n"] += 1
        return _make_result()

    fixed_today = date(2026, 6, 1)
    for plan_id in range(CACHE_MAX_SIZE):
        get_or_run_simulation(
            app,
            plan_id=plan_id,
            plan=plan,
            settings=settings,
            run=run,
            today=fixed_today,
        )
    assert call_count["n"] == CACHE_MAX_SIZE

    # Touch oldest entry so it becomes most-recently used.
    get_or_run_simulation(
        app,
        plan_id=0,
        plan=plan,
        settings=settings,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE

    get_or_run_simulation(
        app,
        plan_id=CACHE_MAX_SIZE,
        plan=plan,
        settings=settings,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 1

    # plan_id=0 was touched; plan_id=1 should have been evicted.
    get_or_run_simulation(
        app,
        plan_id=0,
        plan=plan,
        settings=settings,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 1

    get_or_run_simulation(
        app,
        plan_id=1,
        plan=plan,
        settings=settings,
        run=run,
        today=fixed_today,
    )
    assert call_count["n"] == CACHE_MAX_SIZE + 2


def test_simulation_failure_logs_traceback_and_reraises(caplog) -> None:
    app = FastAPI()
    plan = default_plan()
    failure_message = "engine blew up"

    def run(plan, **kwargs):
        raise RuntimeError(failure_message)

    with pytest.raises(RuntimeError, match=failure_message):
        get_or_run_simulation(
            app,
            plan_id=1,
            plan=plan,
            settings=_empty_settings(),
            run=run,
            today=date(2026, 1, 1),
        )

    assert "Simulation failed for plan_id=1" in caplog.text
    assert failure_message in caplog.text

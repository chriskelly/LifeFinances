from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import numpy as np
import pytest
from core.defaults import default_plan
from core.models import AppSettings
from fastapi import FastAPI
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult
from web.simulation_cache import (
    CACHE_MAX_SIZE,
    fingerprint_plan,
    get_or_run_simulation,
    previous_result,
)


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
    num_runs = 10
    series = np.zeros(shape, dtype=np.float64)
    run_matrix = np.zeros((num_runs, horizon_months), dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon_months,
        num_runs=num_runs,
        percentiles=list(percentiles),
        start_month=(2026, 1),
        balance_start=series.copy(),
        withdrawals_essential=series.copy(),
        withdrawals_discretionary=series.copy(),
        withdrawals_general=series.copy(),
        withdrawals_total=series.copy(),
        withdrawals_total_by_run=run_matrix,
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


def test_fingerprint_ignores_summary_spending_threshold() -> None:
    plan = default_plan()
    changed = plan.model_copy(update={"summary_spending_threshold": Decimal("12000")})

    assert fingerprint_plan(plan) == fingerprint_plan(changed)


def test_fingerprint_tracks_an_economic_plan_change() -> None:
    plan = default_plan()
    changed = plan.model_copy(update={"legacy_target": Decimal("1000")})

    assert fingerprint_plan(plan) != fingerprint_plan(changed)


def _run_once(
    app: FastAPI,
    *,
    plan_id: int,
    plan,
    result: SimulationResult,
    today: date,
) -> SimulationResult:
    return get_or_run_simulation(
        app,
        plan_id=plan_id,
        plan=plan,
        settings=_empty_settings(),
        run=lambda plan, **kwargs: result,
        today=today,
    )


def test_previous_result_is_none_before_the_first_miss() -> None:
    app = FastAPI()

    assert previous_result(app, plan_id=1) is None


def test_previous_result_is_none_after_one_miss_without_an_earlier_run() -> None:
    app = FastAPI()
    _run_once(
        app,
        plan_id=1,
        plan=default_plan(),
        result=_make_result(),
        today=date(2026, 6, 1),
    )

    assert previous_result(app, plan_id=1) is None


def test_previous_result_returns_the_result_before_the_last_miss() -> None:
    app = FastAPI()
    plan = default_plan()
    changed = plan.model_copy(update={"legacy_target": Decimal("1000")})
    first = _make_result()
    second = _make_result()
    fixed_today = date(2026, 6, 1)

    _run_once(app, plan_id=1, plan=plan, result=first, today=fixed_today)
    _run_once(app, plan_id=1, plan=changed, result=second, today=fixed_today)

    assert previous_result(app, plan_id=1) is first


def test_cache_hit_does_not_move_the_previous_result() -> None:
    app = FastAPI()
    plan = default_plan()
    changed = plan.model_copy(update={"legacy_target": Decimal("1000")})
    first = _make_result()
    second = _make_result()
    hit_result = _make_result()
    fixed_today = date(2026, 6, 1)

    _run_once(app, plan_id=1, plan=plan, result=first, today=fixed_today)
    _run_once(app, plan_id=1, plan=changed, result=second, today=fixed_today)
    returned = _run_once(
        app, plan_id=1, plan=changed, result=hit_result, today=fixed_today
    )

    assert returned is second
    assert previous_result(app, plan_id=1) is first


def test_cache_hit_on_a_different_plan_moves_the_previous_result() -> None:
    app = FastAPI()
    plan_a = default_plan()
    plan_b = plan_a.model_copy(update={"legacy_target": Decimal("1000")})
    plan_c = plan_a.model_copy(update={"legacy_target": Decimal("2000")})
    result_a = _make_result()
    result_b = _make_result()
    result_c = _make_result()
    fixed_today = date(2026, 6, 1)

    _run_once(app, plan_id=1, plan=plan_a, result=result_a, today=fixed_today)
    _run_once(app, plan_id=1, plan=plan_b, result=result_b, today=fixed_today)
    _run_once(app, plan_id=1, plan=plan_c, result=result_c, today=fixed_today)
    returned = _run_once(
        app, plan_id=1, plan=plan_a, result=result_a, today=fixed_today
    )

    assert returned is result_a
    assert previous_result(app, plan_id=1) is result_c


def test_failed_run_does_not_move_the_previous_result() -> None:
    app = FastAPI()
    plan = default_plan()
    first = _make_result()
    second = _make_result()
    fixed_today = date(2026, 6, 1)
    _run_once(app, plan_id=1, plan=plan, result=first, today=fixed_today)
    _run_once(
        app,
        plan_id=1,
        plan=plan.model_copy(update={"legacy_target": Decimal("1000")}),
        result=second,
        today=fixed_today,
    )

    def boom(plan, **kwargs):
        raise RuntimeError("engine exploded")

    with pytest.raises(RuntimeError, match="engine exploded"):
        get_or_run_simulation(
            app,
            plan_id=1,
            plan=plan.model_copy(update={"legacy_target": Decimal("2000")}),
            settings=_empty_settings(),
            run=boom,
            today=fixed_today,
        )

    assert previous_result(app, plan_id=1) is first


def test_previous_result_is_none_after_eviction() -> None:
    app = FastAPI()
    plan = default_plan()
    fixed_today = date(2026, 6, 1)
    _run_once(app, plan_id=1, plan=plan, result=_make_result(), today=fixed_today)
    _run_once(
        app,
        plan_id=1,
        plan=plan.model_copy(update={"legacy_target": Decimal("1000")}),
        result=_make_result(),
        today=fixed_today,
    )
    for plan_id in range(2, CACHE_MAX_SIZE + 2):
        _run_once(
            app,
            plan_id=plan_id,
            plan=plan.model_copy(update={"name": f"Plan {plan_id}"}),
            result=_make_result(),
            today=fixed_today,
        )

    assert previous_result(app, plan_id=1) is None


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

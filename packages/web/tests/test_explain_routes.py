from datetime import datetime

import numpy as np
from core.models import Plan
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult
from web.explain import (
    AMBIGUOUS_PLAN,
    INVALID_QUERY,
    PLAN_NOT_FOUND,
    SIMULATION_FAILED,
)
from web.routes import (
    API_PLAN,
    API_PLANS,
    API_RESULT_DIAGNOSTICS,
    API_RESULT_SERIES,
    API_RESULT_SUMMARY,
)


def _make_result() -> SimulationResult:
    horizon_months = 2
    percentiles = [5, 50, 95]
    shape = (len(percentiles), horizon_months)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    scheduled_wealth = np.array([101.0, 202.0], dtype=np.float64)
    diagnostics = empty_diagnostics(months=horizon_months).model_copy(
        update={"scheduled_wealth": scheduled_wealth}
    )
    return SimulationResult(
        ran_at=datetime(2026, 9, 23),
        horizon_months=horizon_months,
        num_runs=10,
        percentiles=percentiles,
        start_month=(2026, 9),
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
        diagnostics=diagnostics,
        resolved_assumptions=ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.02,
            annual_stock_log_variance=0.03,
            planning_preset="fixed",
            inflation_source="manual",
        ),
    )


def test_diagnostics_and_summary_share_one_cached_run(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return result

    monkeypatch.setattr("web.explain.run_simulation", run)

    diagnostics = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})
    summary = client.get(API_RESULT_SUMMARY, params={"plan_id": plan_id})

    assert diagnostics.status_code == 200
    assert summary.status_code == 200
    assert calls["n"] == 1
    assert (
        diagnostics.json()["scheduled_wealth"]
        == result.diagnostics.scheduled_wealth.tolist()
    )
    assert summary.json()["plan_id"] == plan_id


def test_simulation_failure_returns_only_error_fields_and_is_not_cached(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    message = "simulation exploded"
    result = _make_result()
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError(message)
        return result

    monkeypatch.setattr("web.explain.run_simulation", run)

    failure = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})
    success = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})

    assert failure.status_code == 422
    assert failure.json()["error"] == SIMULATION_FAILED
    assert failure.json()["message"] == message
    assert "diagnostics" not in failure.json()
    assert "spending" not in failure.json()
    assert "rows" not in failure.json()
    assert success.status_code == 200
    assert calls["n"] == 2


def test_plans_lists_bootstrapped_default_without_running_simulation(
    client: TestClient, plan_id: int, repo: PlanRepository, monkeypatch
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.explain.run_simulation", run)

    response = client.get(API_PLANS)

    assert response.status_code == 200
    assert response.json()["plans"] == [
        {"id": plan_id, "name": stored.name, "is_default": True}
    ]
    assert calls["n"] == 0


def test_plan_by_name_returns_round_trippable_stored_plan(
    client: TestClient, plan_id: int, repo: PlanRepository
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None

    response = client.get(API_PLAN, params={"name": stored.name})

    assert response.status_code == 200
    assert response.json()["plan_id"] == plan_id
    assert Plan.model_validate(response.json()["plan"]) == stored


def test_ambiguous_name_returns_conflict_with_candidate_ids(
    client: TestClient, plan_id: int, repo: PlanRepository
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None
    other_id, _ = repo.create(name=f"{stored.name} ")

    response = client.get(API_PLAN, params={"name": stored.name})

    assert response.status_code == 409
    assert response.json()["error"] == AMBIGUOUS_PLAN
    assert [item["id"] for item in response.json()["candidates"]] == [
        plan_id,
        other_id,
    ]


def test_missing_plan_id_returns_not_found(client: TestClient, plan_id: int) -> None:
    missing_id = plan_id + 999_999

    response = client.get(API_PLAN, params={"plan_id": missing_id})

    assert response.status_code == 404
    assert response.json()["error"] == PLAN_NOT_FOUND


def test_series_without_series_returns_invalid_query(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(API_RESULT_SERIES, params={"plan_id": plan_id})

    assert response.status_code == 400
    assert response.json()["error"] == INVALID_QUERY

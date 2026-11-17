from __future__ import annotations

import sys
from datetime import datetime
from decimal import Decimal

import numpy as np
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from simulation.diagnostics import empty_diagnostics
from simulation.result import ResolvedAssumptions, SimulationResult
from web.app import _SIMULATION_FAILURE_MESSAGE
from web.routes import RESULTS, RESULTS_SUMMARY_THRESHOLD

from web import forms, spending_summary


def _resolved_assumptions() -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=0.02,
        annual_stock_return=0.05,
        annual_bond_return=0.02,
        annual_stock_log_variance=0.03,
        planning_preset="fixed",
        inflation_source="manual",
    )


def _summary_result(
    *, initial: float = 1_200.0, matrix: np.ndarray | None = None
) -> SimulationResult:
    percentiles = [5, 50, 95]
    if matrix is None:
        matrix = np.array(
            [
                [600.0] * 12 + [1_200.0] * 12,
                [1_200.0] * 24,
                [1_500.0] * 24,
                [2_000.0] * 24,
            ],
            dtype=np.float64,
        )
    horizon = matrix.shape[1]
    totals = np.zeros((len(percentiles), horizon), dtype=np.float64)
    if horizon:
        totals[0, 0] = initial
    months = np.zeros(horizon, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon,
        num_runs=matrix.shape[0],
        percentiles=percentiles,
        start_month=(2026, 1),
        balance_start=totals.copy(),
        withdrawals_essential=totals.copy(),
        withdrawals_discretionary=totals.copy(),
        withdrawals_general=totals.copy(),
        withdrawals_total=totals,
        withdrawals_total_by_run=matrix.astype(np.float64),
        savings_stock_allocation=totals.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
        diagnostics=empty_diagnostics(months=horizon),
        resolved_assumptions=_resolved_assumptions(),
    )


def _install_result(monkeypatch, result: SimulationResult) -> None:
    app_module = sys.modules["web.simulation_cache"]
    monkeypatch.setattr(app_module, "run_simulation", lambda plan, **kwargs: result)


def _seed_threshold(repo: PlanRepository, plan_id: int, value: Decimal | None) -> None:
    plan = repo.get_by_id(plan_id)
    assert plan is not None
    repo.save(
        plan_id,
        plan.model_copy(update={"summary_spending_threshold": value}),
    )


def test_results_renders_levels_and_odds_columns(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))
    _install_result(monkeypatch, _summary_result())

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert spending_summary.LEVELS_TITLE in response.text
    assert spending_summary.ODDS_TITLE in response.text
    for label in (
        spending_summary.INITIAL_SPENDING_LABEL,
        spending_summary.LOWEST_PERCENTILE_YEAR_LABEL,
        spending_summary.MEDIAN_FINAL_YEAR_LABEL,
        spending_summary.BAD_YEAR_LABEL,
        spending_summary.BAD_MONTH_LABEL,
    ):
        assert label in response.text
    assert "data-tooltip=" in response.text


def test_results_without_threshold_shows_prompt_and_no_odds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    _install_result(monkeypatch, _summary_result())

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert spending_summary.THRESHOLD_PROMPT in response.text
    assert spending_summary.BAD_YEAR_LABEL not in response.text


def test_results_with_zero_threshold_still_shows_odds(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _seed_threshold(repo, plan_id, Decimal(0))
    _install_result(monkeypatch, _summary_result())

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert spending_summary.THRESHOLD_PROMPT not in response.text
    assert "0% of runs" in response.text
    assert "0% of months" in response.text


def test_results_with_threshold_shows_percentages(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))
    _install_result(monkeypatch, _summary_result())

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert "25% of runs" in response.text
    assert "12.5% of months" in response.text


def test_results_short_horizon_shows_unavailable_year_metrics(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))
    matrix = np.array([[100.0] * 3, [2_000.0] * 3], dtype=np.float64)
    _install_result(monkeypatch, _summary_result(matrix=matrix))

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert "unavailable" in response.text
    assert spending_summary.BAD_MONTH_LABEL in response.text


def test_post_threshold_saves_and_returns_the_partial(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _install_result(monkeypatch, _summary_result())

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "$1,000"},
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.summary_spending_threshold == Decimal("1000")
    assert "25% of runs" in response.text
    assert "<html" not in response.text
    assert 'id="results-panel"' not in response.text


def test_post_blank_threshold_clears(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))
    _install_result(monkeypatch, _summary_result())

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: ""},
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.summary_spending_threshold is None
    assert spending_summary.THRESHOLD_PROMPT in response.text


def test_post_unparsable_threshold_returns_422_and_keeps_value(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "abc"},
    )

    assert response.status_code == 422
    assert "Enter a dollar amount" in response.text
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.summary_spending_threshold == Decimal("1000")


def test_post_negative_threshold_returns_422_with_field_label(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    _seed_threshold(repo, plan_id, Decimal("1000"))

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "-5"},
    )

    assert response.status_code == 422
    assert "Spending threshold" in response.text
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.summary_spending_threshold == Decimal("1000")


def test_post_threshold_does_not_rerun_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    calls = {"n": 0}
    result = _summary_result()
    app_module = sys.modules["web.simulation_cache"]

    def run(plan, **kwargs):
        calls["n"] += 1
        return result

    monkeypatch.setattr(app_module, "run_simulation", run)
    client.get(f"{RESULTS}?plan={plan_id}")

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "$1,000"},
    )

    assert response.status_code == 200
    assert calls["n"] == 1


def test_threshold_form_posts_outside_the_plan_prefix(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    _install_result(monkeypatch, _summary_result())
    page = client.get(f"{RESULTS}?plan={plan_id}")

    assert f'hx-post="{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}"' in page.text
    assert "hx-patch" not in page.text

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "$1,000"},
    )
    assert response.headers.get("HX-Trigger") is None


def test_post_threshold_persists_when_simulation_fails(
    client: TestClient, repo: PlanRepository, plan_id: int, monkeypatch
) -> None:
    app_module = sys.modules["web.simulation_cache"]

    def boom(plan, **kwargs):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(app_module, "run_simulation", boom)

    response = client.post(
        f"{RESULTS_SUMMARY_THRESHOLD}?plan={plan_id}",
        data={forms.SUMMARY_SPENDING_THRESHOLD: "$1,000"},
    )

    assert response.status_code == 422
    assert _SIMULATION_FAILURE_MESSAGE in response.text
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.summary_spending_threshold == Decimal("1000")

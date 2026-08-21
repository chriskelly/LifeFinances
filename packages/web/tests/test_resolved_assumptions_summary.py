from __future__ import annotations

import math
import sys
from datetime import date, datetime
from html import unescape

import numpy as np
import pytest
from core.models import DEFAULT_PERCENTILES, PlanningPreset
from fastapi.testclient import TestClient
from simulation.result import ResolvedAssumptions, SimulationResult
from web.percent import format_percent
from web.resolved_assumptions import (
    UNAVAILABLE_MESSAGE,
    annual_stock_log_volatility,
)
from web.routes import EDITOR_MARKET_ASSUMPTIONS, HOME, RESULTS
from web.sections import MARKET_ASSUMPTIONS_TITLE

from web import forms


def _assumptions(
    *,
    annual_stock_log_variance: float,
    planning_preset: PlanningPreset = "regression_prediction",
    inflation_source: str = "vendored",
    inflation_observation_date: date | None = date(2026, 4, 30),
    sp500_source: str | None = "cache",
    sp500_observation_date: date | None = date(2026, 5, 1),
    treasury_source: str | None = "live",
    treasury_observation_date: date | None = date(2026, 5, 2),
    annual_inflation: float = 0.023,
    annual_stock_return: float = 0.051,
    annual_bond_return: float = 0.018,
) -> ResolvedAssumptions:
    return ResolvedAssumptions(
        annual_inflation=annual_inflation,
        annual_stock_return=annual_stock_return,
        annual_bond_return=annual_bond_return,
        annual_stock_log_variance=annual_stock_log_variance,
        planning_preset=planning_preset,
        inflation_source=inflation_source,  # type: ignore[arg-type]
        inflation_observation_date=inflation_observation_date,
        sp500_source=sp500_source,  # type: ignore[arg-type]
        sp500_observation_date=sp500_observation_date,
        treasury_source=treasury_source,  # type: ignore[arg-type]
        treasury_observation_date=treasury_observation_date,
    )


def _make_result(assumptions: ResolvedAssumptions) -> SimulationResult:
    horizon = 3
    percentiles = list(DEFAULT_PERCENTILES)
    shape = (len(percentiles), horizon)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1, 12, 0, 0),
        horizon_months=horizon,
        num_runs=10,
        percentiles=percentiles,
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
        resolved_assumptions=assumptions,
    )


def _stub_run(monkeypatch, result: SimulationResult) -> None:
    app_module = sys.modules["web.app"]

    def stub_run_simulation(plan, **kwargs):
        return result

    monkeypatch.setattr(app_module, "run_simulation", stub_run_simulation)


def _stub_failure(monkeypatch) -> None:
    app_module = sys.modules["web.app"]

    def boom_run_simulation(plan, **kwargs):
        raise RuntimeError("engine exploded")

    monkeypatch.setattr(app_module, "run_simulation", boom_run_simulation)


def test_stock_volatility_is_square_root_of_resolved_variance() -> None:
    annual_variance = 0.0324
    expected_volatility = math.sqrt(annual_variance)
    assumptions = _assumptions(annual_stock_log_variance=annual_variance)

    actual = annual_stock_log_volatility(assumptions)

    assert actual == pytest.approx(expected_volatility)


def test_home_renders_resolved_assumptions_from_cached_result(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    annual_inflation = 0.023
    annual_stock_return = 0.051
    annual_bond_return = 0.018
    annual_variance = 0.0324
    inflation_date = date(2026, 4, 30)
    sp500_date = date(2026, 5, 1)
    treasury_date = date(2026, 5, 2)
    assumptions = _assumptions(
        annual_stock_log_variance=annual_variance,
        annual_inflation=annual_inflation,
        annual_stock_return=annual_stock_return,
        annual_bond_return=annual_bond_return,
        inflation_observation_date=inflation_date,
        sp500_observation_date=sp500_date,
        treasury_observation_date=treasury_date,
    )
    _stub_run(monkeypatch, _make_result(assumptions))

    response = client.get(f"{HOME}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert MARKET_ASSUMPTIONS_TITLE in body
    assert format_percent(annual_inflation) in body
    assert format_percent(annual_stock_return) in body
    assert format_percent(annual_bond_return) in body
    assert format_percent(math.sqrt(annual_variance)) in body
    assert forms.PLANNING_PRESET_LABELS["regression_prediction"] in body
    assert "Vendored fallback" in body
    assert inflation_date.isoformat() in body
    assert "Cached" in body
    assert sp500_date.isoformat() in body
    assert "Live" in body
    assert treasury_date.isoformat() in body
    assert UNAVAILABLE_MESSAGE not in body


def test_home_simulation_failure_renders_unavailable_without_numeric_values(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    _stub_failure(monkeypatch)

    response = client.get(f"{HOME}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert UNAVAILABLE_MESSAGE in body
    assert 'class="resolved-assumptions"' not in body
    assert "Inflation source:" not in body


def test_results_success_contains_exactly_one_oob_target_with_current_values(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    annual_inflation = 0.027
    annual_variance = 0.04
    assumptions = _assumptions(
        annual_stock_log_variance=annual_variance,
        annual_inflation=annual_inflation,
    )
    _stub_run(monkeypatch, _make_result(assumptions))

    response = client.get(f"{RESULTS}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert body.count('id="resolved-assumptions-summary"') == 1
    assert body.count('hx-swap-oob="innerHTML"') == 1
    assert format_percent(annual_inflation) in body
    assert format_percent(math.sqrt(annual_variance)) in body


def test_results_simulation_failure_oob_shows_unavailable(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    _stub_failure(monkeypatch)

    response = client.get(f"{RESULTS}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert 'id="resolved-assumptions-summary"' in body
    assert 'hx-swap-oob="innerHTML"' in body
    assert UNAVAILABLE_MESSAGE in body
    assert 'class="resolved-assumptions"' not in body


def test_market_assumptions_get_renders_cached_assumptions(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    annual_bond_return = 0.021
    assumptions = _assumptions(
        annual_stock_log_variance=0.03,
        annual_bond_return=annual_bond_return,
    )
    _stub_run(monkeypatch, _make_result(assumptions))

    response = client.get(f"{EDITOR_MARKET_ASSUMPTIONS}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert format_percent(annual_bond_return) in body
    assert forms.PLANNING_PRESET_LABELS["regression_prediction"] in body
    assert 'hx-swap-oob="innerHTML"' not in body


@pytest.mark.parametrize(
    ("preset", "expected_label"),
    [
        ("fixed", forms.PLANNING_PRESET_LABELS["fixed"]),
        ("historical", forms.PLANNING_PRESET_LABELS["historical"]),
    ],
)
def test_fixed_and_historical_presets_omit_market_source_dates(
    client: TestClient,
    plan_id: int,
    monkeypatch,
    preset: PlanningPreset,
    expected_label: str,
) -> None:
    annual_inflation = 0.019
    assumptions = _assumptions(
        annual_stock_log_variance=0.03,
        annual_inflation=annual_inflation,
        planning_preset=preset,
        inflation_source="manual",
        inflation_observation_date=None,
        sp500_source=None,
        sp500_observation_date=None,
        treasury_source=None,
        treasury_observation_date=None,
    )
    _stub_run(monkeypatch, _make_result(assumptions))

    response = client.get(f"{HOME}?plan={plan_id}")

    body = unescape(response.text)
    assert response.status_code == 200
    assert UNAVAILABLE_MESSAGE not in body
    assert format_percent(annual_inflation) in body
    assert f"<dd>{expected_label}</dd>" in body
    assert "S&P 500 source:" not in body
    assert "Treasury source:" not in body
    assert "Inflation source: Manual" in body

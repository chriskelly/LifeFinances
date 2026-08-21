from decimal import Decimal
from html import unescape
from typing import get_args

import pytest
from core.models import (
    DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS,
    DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS,
    InflationConfig,
    PlanningPreset,
    PlanningReturnsConfig,
    SamplingConfig,
)
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from web.percent import format_percent
from web.routes import EDITOR_MARKET_ASSUMPTIONS, PLAN_MARKET_ASSUMPTIONS
from web.sections import MARKET_ASSUMPTIONS_TITLE

from web import forms


def _market_form_data(
    *,
    inflation_mode: str = "suggested",
    planning_preset: str = "regression_prediction",
) -> dict[str, str]:
    return {
        forms.INFLATION_MODE: inflation_mode,
        forms.PLANNING_PRESET: planning_preset,
        forms.STOCK_VOLATILITY_SCALE: "1",
    }


def _preset_required_fields(preset: str) -> dict[str, str]:
    if preset == "fixed_equity_premium":
        return {
            forms.FIXED_EQUITY_PREMIUM: format_percent(
                forms.FIXED_EQUITY_PREMIUM_FORM_DEFAULT
            )
        }
    if preset == "custom":
        return {
            forms.CUSTOM_STOCKS_BASE: forms.CUSTOM_STOCKS_BASE_FORM_DEFAULT,
            forms.CUSTOM_BONDS_BASE: forms.CUSTOM_BONDS_BASE_FORM_DEFAULT,
        }
    if preset == "fixed":
        return {
            forms.EXPECTED_ANNUAL_RETURN_STOCKS: format_percent(
                DEFAULT_EXPECTED_ANNUAL_RETURN_STOCKS
            ),
            forms.EXPECTED_ANNUAL_RETURN_BONDS: format_percent(
                DEFAULT_EXPECTED_ANNUAL_RETURN_BONDS
            ),
        }
    return {}


@pytest.mark.parametrize("preset", get_args(PlanningPreset))
def test_patch_saves_each_planning_preset(
    client: TestClient, repo: PlanRepository, plan_id: int, preset: str
) -> None:
    data = {
        **_market_form_data(planning_preset=preset),
        **_preset_required_fields(preset),
    }

    response = client.patch(f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}", data=data)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.planning_returns.preset == preset


def test_switching_to_suggested_preserves_manual_inflation_rate(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stored_manual_rate = Decimal("0.027")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.inflation = InflationConfig(
        mode="manual", manual_annual_rate=stored_manual_rate
    )
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(inflation_mode="suggested"),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.inflation.mode == "suggested"
    assert saved.inflation.manual_annual_rate == stored_manual_rate


def test_manual_inflation_rate_round_trips(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    manual_rate = Decimal("0.031")

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data={
            **_market_form_data(inflation_mode="manual"),
            forms.INFLATION_MANUAL_ANNUAL_RATE: format_percent(manual_rate),
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.inflation.mode == "manual"
    assert saved.inflation.manual_annual_rate == manual_rate


def test_manual_inflation_without_rate_returns_422_without_changes(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    prior_inflation = seeded.inflation.model_copy()
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(inflation_mode="manual"),
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.inflation == prior_inflation


def test_fixed_equity_premium_without_premium_returns_422_without_changes(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    prior_returns = seeded.planning_returns.model_copy()
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(planning_preset="fixed_equity_premium"),
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.planning_returns == prior_returns


def test_custom_without_both_bases_returns_422_without_changes(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    prior_returns = seeded.planning_returns.model_copy()
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data={
            **_market_form_data(planning_preset="custom"),
            forms.CUSTOM_STOCKS_BASE: forms.CUSTOM_STOCKS_BASE_FORM_DEFAULT,
        },
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.planning_returns == prior_returns


def test_inactive_custom_values_preserved_after_switching_presets(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stocks_base = "historical"
    bonds_base = "historical"
    stocks_delta = Decimal("0.01")
    bonds_delta = Decimal("-0.005")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.planning_returns = PlanningReturnsConfig(
        preset="custom",
        custom_stocks_base=stocks_base,
        custom_bonds_base=bonds_base,
        custom_stocks_delta=stocks_delta,
        custom_bonds_delta=bonds_delta,
    )
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(planning_preset="historical"),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.planning_returns.preset == "historical"
    assert saved.planning_returns.custom_stocks_base == stocks_base
    assert saved.planning_returns.custom_bonds_base == bonds_base
    assert saved.planning_returns.custom_stocks_delta == stocks_delta
    assert saved.planning_returns.custom_bonds_delta == bonds_delta


def test_stock_volatility_scale_round_trips(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    scale = Decimal("1.25")

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data={
            **_market_form_data(),
            forms.STOCK_VOLATILITY_SCALE: str(scale),
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.planning_returns.stock_volatility_scale == scale


def test_patch_preserves_unrelated_sampling(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    prior_sampling = SamplingConfig(num_runs=42, seed=7)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.sampling = prior_sampling
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_MARKET_ASSUMPTIONS}?plan={plan_id}",
        data=_market_form_data(planning_preset="historical"),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.sampling == prior_sampling
    assert saved.planning_returns.preset == "historical"


def test_editor_market_assumptions_get_renders_title_and_all_presets(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_MARKET_ASSUMPTIONS}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert MARKET_ASSUMPTIONS_TITLE in body
    for preset in get_args(PlanningPreset):
        assert f'value="{preset}"' in body
        assert forms.PLANNING_PRESET_LABELS[preset] in body


def test_editor_market_assumptions_get_includes_conditional_hooks_and_defaults(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_MARKET_ASSUMPTIONS}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert 'data-condition-controller="inflation-mode"' in body
    assert 'data-condition-controller="planning-preset"' in body
    assert "data-condition-group" in body
    assert 'data-condition-controller-id="inflation-mode"' in body
    assert 'data-condition-controller-id="planning-preset"' in body
    assert 'data-condition-value="manual"' in body
    assert 'data-condition-value="fixed_equity_premium"' in body
    assert 'data-condition-value="custom"' in body
    assert 'data-condition-value="fixed"' in body
    assert "data-condition-input" in body
    assert "data-required-when-active" in body
    assert 'hx-validate="true"' in body
    assert f'name="{forms.FIXED_EQUITY_PREMIUM}"' in body
    assert format_percent(forms.FIXED_EQUITY_PREMIUM_FORM_DEFAULT) in body
    assert (
        f'value="{forms.CUSTOM_STOCKS_BASE_FORM_DEFAULT}"' in body
        or f'value="{forms.CUSTOM_STOCKS_BASE_FORM_DEFAULT}" selected' in body
    )
    assert forms.CUSTOM_STOCKS_BASE_FORM_DEFAULT in body
    assert forms.CUSTOM_BONDS_BASE_FORM_DEFAULT in body
    assert 'id="resolved-assumptions-summary"' in body
    assert "<summary>Customize</summary>" in body
    assert f'name="{forms.STOCK_VOLATILITY_SCALE}"' in body

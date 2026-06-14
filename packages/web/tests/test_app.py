from decimal import Decimal

import httpx
from core.defaults import DEFAULT_PLAN_NAME
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from web.forms import CURRENT_SAVINGS_BALANCE
from web.routes import HOME, PLAN_PORTFOLIO, RESULTS
from web.sections import HOUSEHOLD_TITLE, PORTFOLIO_TITLE


def test_home_shows_both_editor_sections(client: TestClient) -> None:
    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert HOUSEHOLD_TITLE in response.text
    assert PORTFOLIO_TITLE in response.text


def test_home_auto_creates_default_plan(
    client: TestClient, repo: PlanRepository
) -> None:
    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1  # intentionally pinned: first row in empty DB
    assert plan.name == DEFAULT_PLAN_NAME


def test_patch_portfolio_persists_balance_change(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    expected_balance = Decimal("750000")

    response: httpx.Response = client.patch(
        PLAN_PORTFOLIO,
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    _, plan = repo.get_or_create_default()
    assert plan.portfolio.current_savings_balance == expected_balance


def test_results_echoes_updated_balance(client: TestClient) -> None:
    expected_balance = Decimal("750000")
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    patch_response: httpx.Response = client.patch(
        PLAN_PORTFOLIO, data={CURRENT_SAVINGS_BALANCE: str(expected_balance)}
    )
    assert patch_response.status_code == 200

    response: httpx.Response = client.get(RESULTS)

    assert response.status_code == 200
    assert str(expected_balance) in response.text

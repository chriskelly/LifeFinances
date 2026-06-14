from decimal import Decimal

import httpx
from core.defaults import DEFAULT_PLAN_NAME, default_plan
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from web.forms import (
    CURRENT_SAVINGS_BALANCE,
    PERSON1_BIRTH_MONTH,
    PERSON1_BIRTH_YEAR,
    PERSON1_MAX_AGE_YEARS,
    PERSON2_BIRTH_MONTH,
    PERSON2_BIRTH_YEAR,
    PERSON2_MAX_AGE_YEARS,
)
from web.routes import HOME, PLAN_HOUSEHOLD, PLAN_PORTFOLIO, RESULTS
from web.sections import HOUSEHOLD_TITLE, PORTFOLIO_TITLE


def _household_form_data() -> dict[str, str]:
    plan = default_plan()
    p1 = plan.household.person1
    p2 = plan.household.person2
    return {
        PERSON1_BIRTH_MONTH: str(p1.birth_month),
        PERSON1_BIRTH_YEAR: str(p1.birth_year),
        PERSON1_MAX_AGE_YEARS: str(p1.max_age_years),
        PERSON2_BIRTH_MONTH: str(p2.birth_month),
        PERSON2_BIRTH_YEAR: str(p2.birth_year),
        PERSON2_MAX_AGE_YEARS: str(p2.max_age_years),
    }


def test_home_shows_both_editor_sections(client: TestClient) -> None:
    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert HOUSEHOLD_TITLE in response.text
    assert PORTFOLIO_TITLE in response.text


def test_home_auto_creates_default_plan(
    client: TestClient, repo: PlanRepository
) -> None:
    assert repo.get_by_id(1) is None

    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    plan = repo.get_by_id(1)

    assert plan is not None
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


def test_patch_household_invalid_value_returns_422_without_persisting(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    _, original = repo.get_or_create_default()
    invalid_max_age = "-200"
    form_data = _household_form_data()
    form_data[PERSON1_MAX_AGE_YEARS] = invalid_max_age

    response: httpx.Response = client.patch(PLAN_HOUSEHOLD, data=form_data)

    assert response.status_code == 422
    assert response.text  # surfaces a human-readable message
    _, after = repo.get_or_create_default()
    assert after.household == original.household


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

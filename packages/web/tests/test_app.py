from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME
from web.forms import CURRENT_SAVINGS_BALANCE
from web.routes import HOME, PLAN_PORTFOLIO, RESULTS
from web.sections import HOUSEHOLD_TITLE, PORTFOLIO_TITLE


def test_home_shows_both_editor_sections(client) -> None:
    response = client.get(HOME)

    assert response.status_code == 200
    assert HOUSEHOLD_TITLE in response.text
    assert PORTFOLIO_TITLE in response.text


def test_home_auto_creates_default_plan(client, repo) -> None:
    client.get(HOME)

    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1  # intentionally pinned: first row in empty DB
    assert plan.name == DEFAULT_PLAN_NAME


def test_patch_portfolio_persists_balance_change(client, repo) -> None:
    client.get(HOME)
    expected_balance = Decimal("750000")

    response = client.patch(
        PLAN_PORTFOLIO,
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    _, plan = repo.get_or_create_default()
    assert plan.portfolio.current_savings_balance == expected_balance


def test_results_echoes_updated_balance(client) -> None:
    expected_balance = Decimal("750000")
    client.get(HOME)
    client.patch(PLAN_PORTFOLIO, data={CURRENT_SAVINGS_BALANCE: str(expected_balance)})

    response = client.get(RESULTS)

    assert response.status_code == 200
    assert str(expected_balance) in response.text

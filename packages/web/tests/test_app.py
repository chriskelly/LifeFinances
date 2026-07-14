import re
from decimal import Decimal

import httpx2 as httpx
import pytest
from core.defaults import DEFAULT_PLAN_NAME, default_plan
from core.models import AppSettings
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi.testclient import TestClient
from web.forms import (
    CLEAR_FRED_API_KEY,
    CURRENT_SAVINGS_BALANCE,
    FRED_API_KEY,
    HAS_PARTNER,
    PERSON1_BIRTH_MONTH,
    PERSON1_BIRTH_YEAR,
    PERSON1_MAX_AGE_YEARS,
    PERSON2_BIRTH_MONTH,
    PERSON2_BIRTH_YEAR,
    PERSON2_MAX_AGE_YEARS,
)
from web.routes import HOME, PLAN_HOUSEHOLD, PLAN_PORTFOLIO, PLAN_SETTINGS, RESULTS
from web.sections import HOUSEHOLD_TITLE, PORTFOLIO_TITLE, SETTINGS_TITLE


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def _household_form_data() -> dict[str, str]:
    plan = default_plan()
    p1 = plan.household.person1
    p2 = plan.household.person2
    assert p2 is not None
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


def test_home_shows_settings_section(client: TestClient) -> None:
    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert SETTINGS_TITLE in response.text


def test_home_auto_creates_default_plan(
    client: TestClient, repo: PlanRepository
) -> None:
    assert repo.get_by_id(1) is None

    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    plan = repo.get_by_id(1)

    assert plan is not None
    assert plan.name == DEFAULT_PLAN_NAME


def test_home_without_plan_redirects_to_default(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    response: httpx.Response = client.get(HOME, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == f"{HOME}?plan={plan_id}"


def test_home_with_unknown_plan_returns_404(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.ensure_bootstrap(settings_repo=settings)

    response: httpx.Response = client.get(f"{HOME}?plan=999999")

    assert response.status_code == 404


def test_home_with_plan_serves_shell(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, plan = plans.ensure_bootstrap(settings_repo=settings)

    response: httpx.Response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert plan.name in response.text


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


def test_patch_settings_persists_fred_api_key(client: TestClient, db_path) -> None:
    expected_key = "fred-ui-key"
    response: httpx.Response = client.patch(
        PLAN_SETTINGS,
        data={FRED_API_KEY: expected_key},
    )

    assert response.status_code == 200
    loaded = SettingsRepository(db_path=db_path).get()
    assert loaded.fred_api_key == expected_key


def test_settings_section_never_echoes_stored_api_key(
    client: TestClient, db_path
) -> None:
    secret_key = "fred-secret-value"
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key=secret_key))

    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert secret_key not in response.text
    assert "FRED API key is set" in response.text
    assert "<button" in response.text
    assert "Clear stored FRED API key" in response.text


def test_blank_settings_patch_keeps_existing_key(client: TestClient, db_path) -> None:
    expected_key = "keep-existing-key"
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key=expected_key))

    response: httpx.Response = client.patch(PLAN_SETTINGS, data={FRED_API_KEY: ""})

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key == expected_key


def test_clear_settings_patch_removes_existing_key(client: TestClient, db_path) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="clear-me"))

    response: httpx.Response = client.patch(
        PLAN_SETTINGS,
        data={CLEAR_FRED_API_KEY: "true"},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key is None


def test_patch_household_without_partner_saves_single_person(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    form_data = _household_form_data()
    del form_data[PERSON2_BIRTH_MONTH]
    del form_data[PERSON2_BIRTH_YEAR]
    del form_data[PERSON2_MAX_AGE_YEARS]

    response: httpx.Response = client.patch(PLAN_HOUSEHOLD, data=form_data)

    assert response.status_code == 200
    loaded = repo.get_by_id(1)
    assert loaded is not None
    assert loaded.household.person2 is None
    assert loaded.household.resolved_filing_status == "single"


def test_patch_household_with_partner_saves_two_people(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    form_data = _household_form_data()
    form_data[HAS_PARTNER] = "on"

    response: httpx.Response = client.patch(PLAN_HOUSEHOLD, data=form_data)

    assert response.status_code == 200
    loaded = repo.get_by_id(1)
    assert loaded is not None
    assert loaded.household.person2 is not None
    assert loaded.household.resolved_filing_status == "married_filing_jointly"


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


@pytest.mark.parametrize("route", [HOME, RESULTS])
def test_real_run_passes_stored_keys_with_live_refresh_enabled(
    client: TestClient, db_path, monkeypatch, route: str
) -> None:
    import sys

    expected_fred_key = "fred-secret"
    expected_eod_key = "eod-secret"
    allow_live_refresh = True
    SettingsRepository(db_path=db_path).save(
        AppSettings(fred_api_key=expected_fred_key, eod_api_key=expected_eod_key)
    )

    app_module = sys.modules["web.app"]
    real_run_simulation = app_module.run_simulation
    captured: dict = {}

    def spy_run_simulation(plan, **kwargs):
        captured.update(kwargs)
        return real_run_simulation(plan, **kwargs)

    monkeypatch.setattr(app_module, "run_simulation", spy_run_simulation)

    client.get(route)

    assert captured.get("allow_refresh") is allow_live_refresh
    assert captured.get("fred_api_key") == expected_fred_key
    assert captured.get("eod_api_key") == expected_eod_key


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
    match = re.search(r"Starting balance: ([\d.eE+-]+)", response.text)
    assert match is not None, response.text
    assert float(match.group(1)) == pytest.approx(float(expected_balance))

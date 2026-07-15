import sqlite3
from decimal import Decimal

import httpx2 as httpx
import pytest
from core.defaults import DEFAULT_PLAN_NAME, default_plan
from core.models import AppSettings
from core.plan_names import copy_plan_name
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from fastapi.testclient import TestClient
from web.forms import (
    CLEAR_EOD_API_KEY,
    CLEAR_FRED_API_KEY,
    CURRENT_SAVINGS_BALANCE,
    EOD_API_KEY,
    FRED_API_KEY,
    HAS_PARTNER,
    PERSON1_BIRTH_MONTH,
    PERSON1_BIRTH_YEAR,
    PERSON1_MAX_AGE_YEARS,
    PERSON2_BIRTH_MONTH,
    PERSON2_BIRTH_YEAR,
    PERSON2_MAX_AGE_YEARS,
    PLAN_NAME,
    RETURN_PLAN,
)
from web.routes import (
    HOME,
    PLAN_CREATE,
    PLAN_DELETE,
    PLAN_DUPLICATE,
    PLAN_HOUSEHOLD,
    PLAN_PORTFOLIO,
    PLAN_RENAME,
    PLAN_SET_DEFAULT,
    PLAN_SETTINGS,
    RESULTS,
)
from web.sections import (
    CLEAR_EOD_API_KEY_LABEL,
    EOD_API_KEY_SET_PLACEHOLDER,
    HOUSEHOLD_TITLE,
    PORTFOLIO_TITLE,
    SETTINGS_TITLE,
)

from web import charts as web_charts


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


def test_home_loads_plotly_and_results_partial(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response: httpx.Response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert "plotly" in response.text.lower()
    assert 'id="results-chart"' in response.text
    assert "results-stub" not in response.text


def test_patch_portfolio_persists_balance_change(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_balance = Decimal("750000")

    response: httpx.Response = client.patch(
        f"{PLAN_PORTFOLIO}?plan={plan_id}",
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    plan = repo.get_by_id(plan_id)
    assert plan is not None
    assert plan.portfolio.current_savings_balance == expected_balance


def test_patch_portfolio_updates_only_queried_plan(client, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    a_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    b_id, _ = plans.create(name="Other")
    expected_balance = Decimal("750000")

    response = client.patch(
        f"{PLAN_PORTFOLIO}?plan={b_id}",
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    plan_a = plans.get_by_id(a_id)
    plan_b = plans.get_by_id(b_id)
    assert plan_a is not None and plan_b is not None
    assert plan_b.portfolio.current_savings_balance == expected_balance
    assert plan_a.portfolio.current_savings_balance != expected_balance


def test_patch_settings_persists_fred_api_key(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_key = "fred-ui-key"
    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
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
    plan_id = _bootstrap_plan(db_path)
    expected_key = "keep-existing-key"
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key=expected_key))

    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}", data={FRED_API_KEY: ""}
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key == expected_key


def test_blank_eod_settings_patch_keeps_existing_key(
    client: TestClient, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_key = "keep-existing-eod-key"
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key=expected_key))

    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}", data={EOD_API_KEY: ""}
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().eod_api_key == expected_key


def test_clear_settings_patch_removes_existing_key(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="clear-me"))

    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
        data={CLEAR_FRED_API_KEY: "true"},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key is None


def test_patch_settings_persists_eod_api_key(client: TestClient, db_path) -> None:
    expected_key = "eod-ui-key"
    plan_id = _bootstrap_plan(db_path)
    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
        data={EOD_API_KEY: expected_key},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().eod_api_key == expected_key


def test_clear_eod_settings_patch_removes_existing_key(
    client: TestClient, db_path
) -> None:
    key_to_clear = "clear-me"
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key=key_to_clear))
    plan_id = _bootstrap_plan(db_path)
    response: httpx.Response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
        data={CLEAR_EOD_API_KEY: "true"},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().eod_api_key is None


def test_settings_section_never_echoes_stored_eod_key(
    client: TestClient, db_path
) -> None:
    secret_key = "eod-secret-value"
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key=secret_key))
    plan_id = _bootstrap_plan(db_path)
    response: httpx.Response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert secret_key not in response.text
    assert EOD_API_KEY_SET_PLACEHOLDER in response.text
    assert CLEAR_EOD_API_KEY_LABEL in response.text


def test_patch_household_without_partner_saves_single_person(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    form_data = _household_form_data()
    del form_data[PERSON2_BIRTH_MONTH]
    del form_data[PERSON2_BIRTH_YEAR]
    del form_data[PERSON2_MAX_AGE_YEARS]

    response: httpx.Response = client.patch(
        f"{PLAN_HOUSEHOLD}?plan={plan_id}", data=form_data
    )

    assert response.status_code == 200
    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.household.person2 is None
    assert loaded.household.resolved_filing_status == "single"


def test_patch_household_with_partner_saves_two_people(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    form_data = _household_form_data()
    form_data[HAS_PARTNER] = "on"

    response: httpx.Response = client.patch(
        f"{PLAN_HOUSEHOLD}?plan={plan_id}", data=form_data
    )

    assert response.status_code == 200
    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.household.person2 is not None
    assert loaded.household.resolved_filing_status == "married_filing_jointly"


def test_patch_household_invalid_value_returns_422_without_persisting(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    original = repo.get_by_id(plan_id)
    assert original is not None
    invalid_max_age = "-200"
    form_data = _household_form_data()
    form_data[PERSON1_MAX_AGE_YEARS] = invalid_max_age

    response: httpx.Response = client.patch(
        f"{PLAN_HOUSEHOLD}?plan={plan_id}", data=form_data
    )

    assert response.status_code == 422
    assert response.text  # surfaces a human-readable message
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household == original.household


@pytest.mark.parametrize("route", [HOME, RESULTS])
def test_real_run_passes_stored_keys_with_live_refresh_enabled(
    client: TestClient, db_path, monkeypatch, route: str
) -> None:
    import sys

    plan_id = _bootstrap_plan(db_path)
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

    client.get(f"{route}?plan={plan_id}")

    assert captured.get("allow_refresh") is allow_live_refresh
    assert captured.get("fred_api_key") == expected_fred_key
    assert captured.get("eod_api_key") == expected_eod_key


def test_results_returns_chart_after_balance_update(
    client: TestClient, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_balance = Decimal("750000")
    patch_response: httpx.Response = client.patch(
        f"{PLAN_PORTFOLIO}?plan={plan_id}",
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )
    assert patch_response.status_code == 200

    response: httpx.Response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert 'id="chart-config"' in response.text


def test_results_renders_default_chart_selected(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{RESULTS}?plan={plan_id}")

    assert response.status_code == 200
    assert 'id="results-chart"' in response.text
    assert f'data-chart="{web_charts.DEFAULT_CHART}"' in response.text


def test_results_invalid_chart_falls_back_to_default(
    client: TestClient, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{RESULTS}?plan={plan_id}&chart=bogus")

    assert response.status_code == 200
    assert f'data-chart="{web_charts.DEFAULT_CHART}"' in response.text


def test_results_honors_valid_chart(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    chosen = web_charts.PORTFOLIO

    response = client.get(f"{RESULTS}?plan={plan_id}&chart={chosen}")

    assert response.status_code == 200
    assert f'data-chart="{chosen}"' in response.text


def test_create_plan_redirects_to_new_plan(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.ensure_bootstrap(settings_repo=settings)

    response = client.post(PLAN_CREATE, follow_redirects=False)

    assert response.status_code == 302
    new_summaries = plans.list()
    assert len(new_summaries) == 2
    new_id = max(s.id for s in new_summaries)
    assert response.headers["location"] == f"{HOME}?plan={new_id}"


def test_create_plan_sets_default_when_unset(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    assert plans.list() == []
    assert settings.get().default_plan_id is None

    response = client.post(PLAN_CREATE, follow_redirects=False)

    assert response.status_code == 302
    summaries = plans.list()
    assert len(summaries) == 1
    new_id = summaries[0].id
    assert settings.get().default_plan_id == new_id
    assert response.headers["location"] == f"{HOME}?plan={new_id}"


def test_duplicate_plan_redirects_to_copy(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    source_id, source = plans.ensure_bootstrap(settings_repo=settings)
    expected_balance = Decimal("123456")
    source.portfolio.current_savings_balance = expected_balance
    plans.save(source_id, source)
    expected_copy_name = copy_plan_name(
        original_name=source.name, existing=[source.name]
    )

    response = client.post(
        PLAN_DUPLICATE.format(plan_id=source_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    new_id = max(s.id for s in plans.list())
    assert new_id != source_id
    assert response.headers["location"] == f"{HOME}?plan={new_id}"
    copied = plans.get_by_id(new_id)
    assert copied is not None
    assert copied.name == expected_copy_name
    assert copied.portfolio.current_savings_balance == expected_balance


def test_rename_plan_updates_name(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    expected_name = "Renamed"

    response = client.post(
        PLAN_RENAME.format(plan_id=plan_id),
        data={PLAN_NAME: expected_name},
        follow_redirects=False,
    )

    assert response.status_code == 302
    loaded = plans.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name


def test_rename_plan_with_blank_name_returns_400(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    original_plan = plans.get_by_id(plan_id)
    assert original_plan is not None
    original_name = original_plan.name

    response = client.post(
        PLAN_RENAME.format(plan_id=plan_id),
        data={PLAN_NAME: "   "},
    )

    assert response.status_code == 400
    loaded = plans.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == original_name


def test_set_default_updates_settings(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    second_name = "Second"
    second_id, _ = plans.create(name=second_name)

    response = client.post(
        PLAN_SET_DEFAULT.format(plan_id=second_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert settings.get().default_plan_id == second_id
    assert first_id != second_id


def test_delete_plan_reassigns_default_when_needed(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings_repo = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings_repo)
    second_name = "Second"
    second_id, _ = plans.create(name=second_name)
    settings_repo.save(
        settings_repo.get().model_copy(update={"default_plan_id": second_id})
    )

    response = client.post(
        PLAN_DELETE.format(plan_id=second_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert plans.get_by_id(second_id) is None
    assert settings_repo.get().default_plan_id == first_id
    assert response.headers["location"] == f"{HOME}?plan={first_id}"


def test_delete_plan_redirects_to_real_id_when_default_is_none(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings_repo = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings_repo)
    second_name = "Second"
    second_id, _ = plans.create(name=second_name)
    settings_repo.save(settings_repo.get().model_copy(update={"default_plan_id": None}))

    response = client.post(
        PLAN_DELETE.format(plan_id=second_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert plans.get_by_id(second_id) is None
    assert settings_repo.get().default_plan_id == first_id
    assert response.headers["location"] == f"{HOME}?plan={first_id}"


def test_delete_last_plan_rejected(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    only_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    response = client.post(PLAN_DELETE.format(plan_id=only_id))

    assert response.status_code == 400
    assert len(plans.list()) == 1


def test_delete_last_loadable_rejected_when_corrupt_sibling_exists(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    good_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            ("Corrupt", "{not-valid-plan-json"),
        )
        conn.commit()
    finally:
        conn.close()

    response = client.post(PLAN_DELETE.format(plan_id=good_id))

    assert response.status_code == 400
    assert plans.get_by_id(good_id) is not None
    assert len(plans.list()) == 2


def test_delete_sibling_keeps_active_plan(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    active_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    sibling_id, _ = plans.create(name="Sibling")
    other_id, _ = plans.create(name="Other")
    settings.save(settings.get().model_copy(update={"default_plan_id": other_id}))

    response = client.post(
        PLAN_DELETE.format(plan_id=sibling_id),
        data={RETURN_PLAN: str(active_id)},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert plans.get_by_id(sibling_id) is None
    assert response.headers["location"] == f"{HOME}?plan={active_id}"


def test_delete_unknown_plan_returns_404(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.ensure_bootstrap(settings_repo=settings)
    before = plans.list()

    response = client.post(PLAN_DELETE.format(plan_id=999_999))

    assert response.status_code == 404
    assert plans.list() == before


def test_results_without_plan_returns_404(client: TestClient, db_path) -> None:
    _bootstrap_plan(db_path)

    response = client.get(RESULTS)

    assert response.status_code == 404


def test_patch_portfolio_without_plan_returns_404(client: TestClient, db_path) -> None:
    _bootstrap_plan(db_path)

    response = client.patch(
        PLAN_PORTFOLIO,
        data={CURRENT_SAVINGS_BALANCE: "1000"},
    )

    assert response.status_code == 404


def test_delete_unparseable_plan_succeeds_without_loading_json(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    good_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO plans (name, data) VALUES (?, ?)",
            ("Corrupt", "{not-valid-plan-json"),
        )
        conn.commit()
        corrupt_id = cur.lastrowid
    finally:
        conn.close()
    assert corrupt_id is not None

    response = client.post(
        PLAN_DELETE.format(plan_id=corrupt_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert plans.get_by_id(corrupt_id) is None
    assert plans.exists(good_id)
    assert response.headers["location"] == f"{HOME}?plan={good_id}"


def test_home_delete_form_requires_confirm(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)
    plans = PlanRepository(db_path=db_path)
    plans.create(name="Second")

    response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert 'onsubmit="return confirm(' in response.text
    assert PLAN_DELETE.format(plan_id=plan_id) in response.text

from decimal import Decimal

from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from core.streams import TimedStream
from fastapi.testclient import TestClient
from web.routes import EDITOR_MANUAL_INCOME, PLAN_MANUAL_INCOME
from web.sections import MANUAL_INCOME_TITLE


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_manual_income_adds_stream(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_label = "Rental"
    expected_amount = "2500"
    data = {
        "streams[0].label": expected_label,
        "streams[0].monthly_amount": expected_amount,
        "streams[0].annual_growth_rate": "0",
        "streams[0].start_kind": "now",
        "streams[0].end_kind": "none",
    }

    response = client.patch(f"{PLAN_MANUAL_INCOME}?plan={plan_id}", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    streams = after.manual_income_streams
    assert [s.label for s in streams] == [expected_label]
    assert streams[0].monthly_amount == Decimal(expected_amount)


def test_patch_manual_income_blank_monthly_amount_returns_422(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_label = "Rental"
    expected_amount = Decimal("2500")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.manual_income_streams = [
        TimedStream(label=expected_label, monthly_amount=expected_amount)
    ]
    repo.save(plan_id, seeded)
    invalid_amount = ""

    response = client.patch(
        f"{PLAN_MANUAL_INCOME}?plan={plan_id}",
        data={
            "streams[0].label": expected_label,
            "streams[0].monthly_amount": invalid_amount,
            "streams[0].annual_growth_rate": "0",
            "streams[0].start_kind": "now",
            "streams[0].end_kind": "none",
        },
    )

    assert response.status_code == 422
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.manual_income_streams[0].monthly_amount == expected_amount


def test_patch_manual_income_empty_clears_streams(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.manual_income_streams = [TimedStream(monthly_amount=Decimal("100"))]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_MANUAL_INCOME}?plan={plan_id}", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.manual_income_streams == []


def test_editor_manual_income_get_renders_section(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_MANUAL_INCOME}?plan={plan_id}")

    assert response.status_code == 200
    assert MANUAL_INCOME_TITLE in response.text

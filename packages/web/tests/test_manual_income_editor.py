from decimal import Decimal

from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, TimedStream
from fastapi.testclient import TestClient
from web.routes import EDITOR_MANUAL_INCOME, PLAN_MANUAL_INCOME
from web.sections import MANUAL_INCOME_TITLE

from web import boundaries


def test_patch_manual_income_adds_stream(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
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
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    expected_label = "Rental"
    expected_amount = Decimal("2500")
    stream_start = CalendarMonthBoundary(year=2010, month=1)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.manual_income_streams = [
        TimedStream(
            label=expected_label, monthly_amount=expected_amount, start=stream_start
        )
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
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stream_start = CalendarMonthBoundary(year=2010, month=1)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.manual_income_streams = [
        TimedStream(monthly_amount=Decimal("100"), start=stream_start)
    ]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_MANUAL_INCOME}?plan={plan_id}", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.manual_income_streams == []


def test_editor_manual_income_get_renders_section(
    client: TestClient, plan_id: int
) -> None:

    response = client.get(f"{EDITOR_MANUAL_INCOME}?plan={plan_id}")

    assert response.status_code == 200
    assert MANUAL_INCOME_TITLE in response.text


def test_editor_manual_income_start_omits_plan_start_option(
    client: TestClient, plan_id: int
) -> None:

    response = client.get(f"{EDITOR_MANUAL_INCOME}?plan={plan_id}")

    assert response.status_code == 200
    assert "Plan start" not in response.text
    assert "Plan horizon" in response.text
    assert 'value="now"' in response.text


def test_editor_manual_income_start_omits_max_age_option(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_MANUAL_INCOME}?plan={plan_id}")

    assert response.status_code == 200
    # Start control must not offer Max age (empty stream); End may still offer it.
    start_block = response.text.split("Start", 1)[1].split("End", 1)[0]
    assert f'value="{boundaries.KIND_PERSON_MAX_AGE}"' not in start_block
    end_block = response.text.split("End", 1)[1]
    assert f'value="{boundaries.KIND_PERSON_MAX_AGE}"' in end_block

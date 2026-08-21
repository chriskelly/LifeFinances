from decimal import Decimal
from html import unescape

from core.models import RiskConfig, SamplingConfig
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, TimedStream
from fastapi.testclient import TestClient
from web.currency import format_usd
from web.routes import EDITOR_SPENDING, PLAN_SPENDING
from web.sections import SPENDING_GOALS_TITLE

from web import boundaries, forms


def _stream_data(*, prefix: str, label: str, amount: str) -> dict[str, str]:
    return {
        f"{prefix}[0].label": label,
        f"{prefix}[0].monthly_amount": amount,
        f"{prefix}[0].annual_growth_rate": "0%",
        f"{prefix}[0].start_kind": boundaries.KIND_NOW,
        f"{prefix}[0].end_kind": boundaries.KIND_NONE,
    }


def test_patch_spending_keeps_categories_separate(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    essential_label = "Healthcare"
    discretionary_label = "Travel"
    essential_amount = "700"
    discretionary_amount = "500"
    legacy_target = "100000"
    data = {
        **_stream_data(
            prefix=forms.ESSENTIAL_PREFIX,
            label=essential_label,
            amount=essential_amount,
        ),
        **_stream_data(
            prefix=forms.DISCRETIONARY_PREFIX,
            label=discretionary_label,
            amount=discretionary_amount,
        ),
        forms.LEGACY_TARGET: legacy_target,
    }

    response = client.patch(f"{PLAN_SPENDING}?plan={plan_id}", data=data)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert [stream.label for stream in saved.extra_essential_spending] == [
        essential_label
    ]
    assert [stream.label for stream in saved.extra_discretionary_spending] == [
        discretionary_label
    ]
    assert saved.legacy_target == Decimal(legacy_target)


def test_patch_spending_is_nominal_sets_only_that_row(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    nominal_label = "Nominal healthcare"
    real_label = "Real travel"
    amount = "700"
    data = {
        **_stream_data(
            prefix=forms.ESSENTIAL_PREFIX,
            label=nominal_label,
            amount=amount,
        ),
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_IS_NOMINAL}": "on",
        **_stream_data(
            prefix=forms.DISCRETIONARY_PREFIX,
            label=real_label,
            amount=amount,
        ),
        forms.LEGACY_TARGET: "0",
    }

    response = client.patch(f"{PLAN_SPENDING}?plan={plan_id}", data=data)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.extra_essential_spending[0].is_nominal is True
    assert saved.extra_discretionary_spending[0].is_nominal is False


def test_patch_spending_empty_clears_lists_and_sets_legacy(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stream_start = CalendarMonthBoundary(year=2010, month=1)
    prior_legacy = Decimal("50000")
    submitted_legacy = "25000"
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.extra_essential_spending = [
        TimedStream(monthly_amount=Decimal("100"), start=stream_start)
    ]
    seeded.extra_discretionary_spending = [
        TimedStream(monthly_amount=Decimal("200"), start=stream_start)
    ]
    seeded.legacy_target = prior_legacy
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_SPENDING}?plan={plan_id}",
        data={forms.LEGACY_TARGET: submitted_legacy},
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.extra_essential_spending == []
    assert saved.extra_discretionary_spending == []
    assert saved.legacy_target == Decimal(submitted_legacy)


def test_patch_spending_invalid_amount_returns_422_without_changes(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stream_start = CalendarMonthBoundary(year=2010, month=1)
    essential_amount = Decimal("700")
    discretionary_amount = Decimal("500")
    prior_legacy = Decimal("100000")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.extra_essential_spending = [
        TimedStream(
            label="Healthcare",
            monthly_amount=essential_amount,
            start=stream_start,
        )
    ]
    seeded.extra_discretionary_spending = [
        TimedStream(
            label="Travel",
            monthly_amount=discretionary_amount,
            start=stream_start,
        )
    ]
    seeded.legacy_target = prior_legacy
    repo.save(plan_id, seeded)
    invalid_amount = ""

    response = client.patch(
        f"{PLAN_SPENDING}?plan={plan_id}",
        data={
            **_stream_data(
                prefix=forms.ESSENTIAL_PREFIX,
                label="Healthcare",
                amount=invalid_amount,
            ),
            forms.LEGACY_TARGET: "999",
        },
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.extra_essential_spending[0].monthly_amount == essential_amount
    assert saved.extra_discretionary_spending[0].monthly_amount == discretionary_amount
    assert saved.legacy_target == prior_legacy


def test_patch_spending_preserves_cent_amount_when_usd_display_is_echoed(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stored_amount = Decimal("700.50")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.extra_essential_spending = [
        TimedStream(
            label="Healthcare",
            monthly_amount=stored_amount,
            start=CalendarMonthBoundary(year=2010, month=1),
        )
    ]
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_SPENDING}?plan={plan_id}",
        data={
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.EXISTING_INDEX}": "0",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_LABEL}": "Healthcare",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_MONTHLY_AMOUNT}": format_usd(
                stored_amount
            ),
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_ANNUAL_GROWTH_RATE}": "0%",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_START}_kind": "calendar_month",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_START}_year": "2010",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_START}_month": "1",
            f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_END}_kind": "none",
            forms.LEGACY_TARGET: "0",
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.extra_essential_spending[0].monthly_amount == stored_amount


def test_patch_spending_sparse_indices_preserve_numeric_order(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    first_label = "Rent"
    second_label = "Insurance"
    first_amount = "1000"
    second_amount = "200"
    data = {
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_LABEL}": first_label,
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_MONTHLY_AMOUNT}": first_amount,
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_ANNUAL_GROWTH_RATE}": "0%",
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_START}_kind": boundaries.KIND_NOW,
        f"{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_END}_kind": boundaries.KIND_NONE,
        f"{forms.ESSENTIAL_PREFIX}[3].{forms.STREAM_LABEL}": second_label,
        f"{forms.ESSENTIAL_PREFIX}[3].{forms.STREAM_MONTHLY_AMOUNT}": second_amount,
        f"{forms.ESSENTIAL_PREFIX}[3].{forms.STREAM_ANNUAL_GROWTH_RATE}": "0%",
        f"{forms.ESSENTIAL_PREFIX}[3].{forms.STREAM_START}_kind": boundaries.KIND_NOW,
        f"{forms.ESSENTIAL_PREFIX}[3].{forms.STREAM_END}_kind": boundaries.KIND_NONE,
        forms.LEGACY_TARGET: "0",
    }

    response = client.patch(f"{PLAN_SPENDING}?plan={plan_id}", data=data)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert [stream.label for stream in saved.extra_essential_spending] == [
        first_label,
        second_label,
    ]


def test_patch_spending_preserves_unrelated_risk_and_sampling(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    prior_risk = RiskConfig(risk_tolerance_at_20=Decimal("18"))
    prior_sampling = SamplingConfig(num_runs=42, seed=7)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = prior_risk
    seeded.sampling = prior_sampling
    repo.save(plan_id, seeded)
    legacy_target = "1000"

    response = client.patch(
        f"{PLAN_SPENDING}?plan={plan_id}",
        data={forms.LEGACY_TARGET: legacy_target},
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk == prior_risk
    assert saved.sampling == prior_sampling
    assert saved.legacy_target == Decimal(legacy_target)


def test_editor_spending_get_renders_section_controls(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_SPENDING}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert SPENDING_GOALS_TITLE in body
    assert forms.LEGACY_TARGET_HELP in body
    assert "Plan horizon" in body

    essential_start = f'name="{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_START}_kind"'
    essential_end = f'name="{forms.ESSENTIAL_PREFIX}[0].{forms.STREAM_END}_kind"'
    discretionary_start = (
        f'name="{forms.DISCRETIONARY_PREFIX}[0].{forms.STREAM_START}_kind"'
    )
    discretionary_end = (
        f'name="{forms.DISCRETIONARY_PREFIX}[0].{forms.STREAM_END}_kind"'
    )
    assert essential_start in body
    assert essential_end in body
    assert discretionary_start in body
    assert discretionary_end in body

    for start_kind, end_kind in (
        (essential_start, essential_end),
        (discretionary_start, discretionary_end),
    ):
        start_select = body.split(start_kind, 1)[1].split("</select>", 1)[0]
        end_select = body.split(end_kind, 1)[1].split("</select>", 1)[0]
        max_age = f'value="{boundaries.KIND_PERSON_MAX_AGE}"'
        now = f'value="{boundaries.KIND_NOW}"'
        assert now in start_select
        assert max_age not in start_select
        assert max_age in end_select

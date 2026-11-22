import re
from decimal import Decimal
from html import unescape

import pytest
from core.models import RISK_TOLERANCE_NUM_VALUES, SamplingConfig
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, TimedStream
from fastapi.testclient import TestClient
from web.percent import format_percent
from web.routes import EDITOR_RISK, PLAN_RISK
from web.sections import RISK_TITLE
from web.simulation_cache import fingerprint_plan

from web import forms


def _risk_form_data(
    *,
    risk_tolerance_at_20: str = "12",
    additional_annual_spending_tilt: str = "0%",
    delta_at_max_age: str = "0",
    legacy_delta_from_at_20: str = "0",
    time_preference: str = "0%",
) -> dict[str, str]:
    return {
        forms.RISK_TOLERANCE_AT_20: risk_tolerance_at_20,
        forms.ADDITIONAL_ANNUAL_SPENDING_TILT: additional_annual_spending_tilt,
        forms.DELTA_AT_MAX_AGE: delta_at_max_age,
        forms.LEGACY_DELTA_FROM_AT_20: legacy_delta_from_at_20,
        forms.TIME_PREFERENCE: time_preference,
    }


def _input_tag(body: str, field_name: str) -> str:
    name_at = body.index(f'name="{field_name}"')
    tag_start = body.rindex("<input", 0, name_at)
    tag_end = body.index(">", name_at)
    return body[tag_start:tag_end]


def _input_value(body: str, field_name: str) -> str:
    match = re.search(r'value="([^"]*)"', _input_tag(body, field_name))
    assert match is not None
    return match.group(1)


def test_patch_risk_round_trips_visible_fields(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    tolerance = Decimal("14")
    tilt = Decimal("0.01")

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data={
            forms.RISK_TOLERANCE_AT_20: str(tolerance),
            forms.ADDITIONAL_ANNUAL_SPENDING_TILT: format_percent(tilt),
            forms.DELTA_AT_MAX_AGE: "0",
            forms.LEGACY_DELTA_FROM_AT_20: "0",
            forms.TIME_PREFERENCE: "0%",
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk.risk_tolerance_at_20 == tolerance
    assert saved.risk.additional_annual_spending_tilt == tilt


def test_patch_risk_round_trips_advanced_fields(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    delta_at_max_age = Decimal("2")
    legacy_delta = Decimal("3")
    time_preference = Decimal("0.02")

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data=_risk_form_data(
            delta_at_max_age=str(delta_at_max_age),
            legacy_delta_from_at_20=str(legacy_delta),
            time_preference=format_percent(-time_preference),
        ),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk.delta_at_max_age == delta_at_max_age
    assert saved.risk.legacy_delta_from_at_20 == legacy_delta
    assert saved.risk.time_preference == time_preference


def test_patch_risk_negative_tolerance_returns_422_without_changes(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    prior_risk = seeded.risk.model_copy()
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data=_risk_form_data(risk_tolerance_at_20="-1"),
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk == prior_risk


def test_patch_risk_preserves_unrelated_spending_and_sampling(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    stream_start = CalendarMonthBoundary(year=2010, month=1)
    prior_essential = [
        TimedStream(
            label="Healthcare", monthly_amount=Decimal("700"), start=stream_start
        )
    ]
    prior_sampling = SamplingConfig(num_runs=42, seed=7)
    prior_legacy = Decimal("100000")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.extra_essential_spending = prior_essential
    seeded.sampling = prior_sampling
    seeded.legacy_target = prior_legacy
    repo.save(plan_id, seeded)
    tolerance = Decimal("18")

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data=_risk_form_data(risk_tolerance_at_20=str(tolerance)),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.extra_essential_spending == prior_essential
    assert saved.sampling == prior_sampling
    assert saved.legacy_target == prior_legacy
    assert saved.risk.risk_tolerance_at_20 == tolerance


def test_editor_risk_get_renders_title_and_slider_bounds(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert RISK_TITLE in body
    assert 'min="0"' in body
    assert f'max="{RISK_TOLERANCE_NUM_VALUES - 1}"' in body
    assert 'step="1"' in body
    assert "Conservative" in body
    assert "Moderate" in body
    assert "Aggressive" in body


def test_editor_risk_get_shows_selected_tolerance_value(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    selected = Decimal("18")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = seeded.risk.model_copy(update={"risk_tolerance_at_20": selected})
    repo.save(plan_id, seeded)

    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert f">{selected}</output>" in body


def test_editor_risk_get_renders_percent_slider_bounds_for_tilt_and_time_preference(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    for field_name in (
        forms.ADDITIONAL_ANNUAL_SPENDING_TILT,
        forms.TIME_PREFERENCE,
    ):
        tag = _input_tag(body, field_name)
        assert f'id="{field_name}"' in tag
        assert f'min="{forms.PERCENT_SLIDER_MIN}"' in tag
        assert f'max="{forms.PERCENT_SLIDER_MAX}"' in tag
        assert f'step="{forms.PERCENT_SLIDER_STEP}"' in tag


def test_editor_risk_get_shows_selected_tilt_value(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    tilt = Decimal("0.0125")
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = seeded.risk.model_copy(
        update={"additional_annual_spending_tilt": tilt}
    )
    repo.save(plan_id, seeded)

    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert f">{format_percent(tilt)}</output>" in body


def test_editor_risk_labels_time_preference_as_preference_for_the_future(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert "Preference for the future" in body
    assert forms.PREFERENCE_FOR_THE_FUTURE_HELP in body
    assert "negative of this value" in body


@pytest.mark.parametrize(
    ("stored", "expected_points"),
    [
        (Decimal("0.02"), "-2"),
        (Decimal("0"), "0"),
        (Decimal("-0.025"), "2.5"),
        (Decimal("-0.08"), "8"),
    ],
)
def test_editor_risk_get_shows_negated_time_preference(
    client: TestClient,
    repo: PlanRepository,
    plan_id: int,
    stored: Decimal,
    expected_points: str,
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = seeded.risk.model_copy(update={"time_preference": stored})
    repo.save(plan_id, seeded)

    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert _input_value(body, forms.TIME_PREFERENCE) == expected_points
    assert f'for="{forms.TIME_PREFERENCE}">{expected_points}%</output>' in body


@pytest.mark.parametrize(
    ("submitted", "expected_stored"),
    [
        ("-2%", Decimal("0.02")),
        ("+1%", Decimal("-0.01")),
        ("0%", Decimal("0")),
    ],
)
def test_patch_risk_negates_time_preference_before_storing(
    client: TestClient,
    repo: PlanRepository,
    plan_id: int,
    submitted: str,
    expected_stored: Decimal,
) -> None:
    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data=_risk_form_data(time_preference=submitted),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk.time_preference == expected_stored


@pytest.mark.parametrize(
    "time_preference",
    [Decimal("0.02"), Decimal("0"), Decimal("-0.025")],
)
def test_untouched_risk_form_round_trip_preserves_plan_and_simulation_input(
    client: TestClient,
    repo: PlanRepository,
    plan_id: int,
    time_preference: Decimal,
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = seeded.risk.model_copy(
        update={
            "risk_tolerance_at_20": Decimal("18"),
            "delta_at_max_age": Decimal("2"),
            "legacy_delta_from_at_20": Decimal("3"),
            "time_preference": time_preference,
            "additional_annual_spending_tilt": Decimal("0.0125"),
        }
    )
    repo.save(plan_id, seeded)

    body = unescape(client.get(f"{EDITOR_RISK}?plan={plan_id}").text)
    rendered_form = {
        field_name: _input_value(body, field_name)
        for field_name in (
            forms.RISK_TOLERANCE_AT_20,
            forms.ADDITIONAL_ANNUAL_SPENDING_TILT,
            forms.DELTA_AT_MAX_AGE,
            forms.LEGACY_DELTA_FROM_AT_20,
            forms.TIME_PREFERENCE,
        )
    }

    response = client.patch(f"{PLAN_RISK}?plan={plan_id}", data=rendered_form)

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved == seeded
    assert fingerprint_plan(saved) == fingerprint_plan(seeded)


def test_patch_risk_accepts_slider_style_tilt_without_percent_suffix(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    tilt = Decimal("0.0125")

    response = client.patch(
        f"{PLAN_RISK}?plan={plan_id}",
        data=_risk_form_data(additional_annual_spending_tilt="1.25"),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk.additional_annual_spending_tilt == tilt


def test_editor_shows_default_max_age_decrease(
    client: TestClient, plan_id: int
) -> None:
    # Pinned: TPAW's displayed default decrease is 2.
    expected_decrease = Decimal(2)

    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert "Risk tolerance decrease by max age" in body
    assert _input_value(body, forms.DELTA_AT_MAX_AGE) == str(expected_decrease)


def test_editor_risk_get_advanced_details_contains_field_names(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_RISK}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    details_start = body.index('<details class="editor-subsection">')
    details_end = body.index("</details>", details_start)
    details = body[details_start:details_end]
    assert "Advanced risk settings" in details
    assert f'name="{forms.DELTA_AT_MAX_AGE}"' in details
    assert f'name="{forms.LEGACY_DELTA_FROM_AT_20}"' in details
    assert f'name="{forms.TIME_PREFERENCE}"' in details
    assert f'name="{forms.RISK_TOLERANCE_AT_20}"' not in details
    assert f'name="{forms.ADDITIONAL_ANNUAL_SPENDING_TILT}"' not in details

from decimal import Decimal
from html import unescape

import pytest
from core.models import RiskConfig
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from web.forms import parse_percentiles_field
from web.routes import EDITOR_SIMULATION_DETAILS, PLAN_SIMULATION_DETAILS
from web.sections import SIMULATION_DETAILS_TITLE

from web import forms


def _simulation_details_form_data(
    *,
    block_size_months: int = 48,
    num_runs: int = 300,
    stagger_run_starts: bool = True,
    seed: int = 9_876,
    percentiles: str = "5, 50, 95",
) -> dict[str, str]:
    data = {
        forms.BLOCK_SIZE_MONTHS: str(block_size_months),
        forms.NUM_RUNS: str(num_runs),
        forms.SAMPLING_SEED: str(seed),
        forms.PERCENTILES: percentiles,
    }
    if stagger_run_starts:
        data[forms.STAGGER_RUN_STARTS] = "on"
    return data


def test_parse_percentiles_field_sorts_and_delegates() -> None:
    submitted = [95, 5, 50]
    expected = sorted(submitted)

    assert parse_percentiles_field(", ".join(str(v) for v in submitted)) == expected


def test_parse_percentiles_field_rejects_empty() -> None:
    with pytest.raises(ValueError, match="comma-separated"):
        parse_percentiles_field("")


def test_parse_percentiles_field_rejects_malformed() -> None:
    with pytest.raises(ValueError, match="whole numbers"):
        parse_percentiles_field("5, abc, 50")


def test_parse_percentiles_field_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        parse_percentiles_field("5, 50, 5")


def test_parse_percentiles_field_rejects_out_of_range() -> None:
    with pytest.raises(ValueError, match="0..100"):
        parse_percentiles_field("5, 101")


@pytest.mark.parametrize(
    "invalid_field",
    [
        pytest.param({forms.SAMPLING_SEED: "-1"}, id="negative-seed"),
        pytest.param(
            {forms.BLOCK_SIZE_MONTHS: str(forms.MAX_BLOCK_SIZE_MONTHS + 1)},
            id="block-size-past-variance-table",
        ),
    ],
)
def test_patch_simulation_details_rejects_unrunnable_sampling(
    client: TestClient,
    repo: PlanRepository,
    plan_id: int,
    invalid_field: dict[str, str],
) -> None:
    # These values validate as plain ints but make every later simulation raise,
    # so they must be refused at save time rather than persisted.
    before = repo.get_by_id(plan_id)
    assert before is not None

    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data=_simulation_details_form_data() | invalid_field,
    )

    assert response.status_code == 422
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.sampling == before.sampling


def test_patch_simulation_details_updates_sampling_and_sorts_percentiles(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    block_size = 48
    num_runs = 300
    seed = 9_876
    submitted_percentiles = [95, 5, 50]
    expected_percentiles = sorted(submitted_percentiles)

    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data={
            forms.BLOCK_SIZE_MONTHS: str(block_size),
            forms.NUM_RUNS: str(num_runs),
            forms.STAGGER_RUN_STARTS: "on",
            forms.SAMPLING_SEED: str(seed),
            forms.PERCENTILES: ", ".join(str(value) for value in submitted_percentiles),
        },
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.sampling.block_size_months == block_size
    assert saved.sampling.num_runs == num_runs
    assert saved.sampling.stagger_run_starts is True
    assert saved.sampling.seed == seed
    assert saved.advanced.percentiles == expected_percentiles


def test_patch_unchecked_stagger_saves_false(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data=_simulation_details_form_data(stagger_run_starts=False),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.sampling.stagger_run_starts is False


@pytest.mark.parametrize(
    "percentiles",
    [
        "5, 50, 5",
        "",
        "5, 101",
        "5, abc",
        "5,,50",
    ],
)
def test_patch_invalid_percentiles_returns_422_without_save(
    client: TestClient,
    repo: PlanRepository,
    plan_id: int,
    percentiles: str,
) -> None:
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    prior_sampling = seeded.sampling.model_copy()
    prior_advanced = seeded.advanced.model_copy()
    repo.save(plan_id, seeded)

    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data=_simulation_details_form_data(percentiles=percentiles),
    )

    assert response.status_code == 422
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.sampling == prior_sampling
    assert saved.advanced == prior_advanced


def test_patch_preserves_unrelated_risk(
    client: TestClient, repo: PlanRepository, plan_id: int
) -> None:
    prior_risk = RiskConfig(
        risk_tolerance_at_20=Decimal("18"),
        additional_annual_spending_tilt=Decimal("0.01"),
    )
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.risk = prior_risk
    repo.save(plan_id, seeded)
    block_size = 36

    response = client.patch(
        f"{PLAN_SIMULATION_DETAILS}?plan={plan_id}",
        data=_simulation_details_form_data(block_size_months=block_size),
    )

    assert response.status_code == 200
    saved = repo.get_by_id(plan_id)
    assert saved is not None
    assert saved.risk == prior_risk
    assert saved.sampling.block_size_months == block_size


def test_editor_simulation_details_get_is_collapsed_by_default(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_SIMULATION_DETAILS}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert SIMULATION_DETAILS_TITLE in body
    details_start = body.index('<details class="editor-section">')
    details_end = body.index("</details>", details_start)
    details = body[details_start:details_end]
    assert " open" not in details
    assert ' open="' not in details


def test_editor_simulation_details_get_includes_sampling_field_names(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_SIMULATION_DETAILS}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert f'name="{forms.BLOCK_SIZE_MONTHS}"' in body
    assert f'name="{forms.NUM_RUNS}"' in body
    assert f'name="{forms.STAGGER_RUN_STARTS}"' in body
    assert f'name="{forms.SAMPLING_SEED}"' in body
    assert f'name="{forms.PERCENTILES}"' in body


def test_editor_simulation_details_get_includes_mapping_help(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(f"{EDITOR_SIMULATION_DETAILS}?plan={plan_id}")
    body = unescape(response.text)

    assert response.status_code == 200
    assert forms.PERCENTILES_WEALTH_MAPPING_HELP in body

import logging
from datetime import datetime
from http import HTTPStatus

import numpy as np
from core.models import Plan
from core.repository import PlanRepository
from fastapi.testclient import TestClient
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS, empty_diagnostics
from simulation.result import RAW_ARRAY_FIELDS, ResolvedAssumptions, SimulationResult
from web.app import create_app
from web.calendar_months import month_labels
from web.explain import (
    AMBIGUOUS_PLAN,
    DB_NOT_INITIALIZED,
    HTTP_BAD_REQUEST,
    HTTP_CONFLICT,
    HTTP_NOT_FOUND,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_UNPROCESSABLE,
    INVALID_QUERY,
    INVALID_RANGE,
    MONTH_OUT_OF_RANGE,
    PLAN_NOT_FOUND,
    SIMULATION_FAILED,
    UNKNOWN_FIELD,
    UNKNOWN_SERIES,
)
from web.routes import (
    API_PLAN,
    API_PLANS,
    API_RESULT_DIAGNOSTICS,
    API_RESULT_SERIES,
    API_RESULT_SUMMARY,
)

from .explain_fixtures import diagnostics_envelope, fields_in_source_order


def _make_result() -> SimulationResult:
    horizon_months = 2
    percentiles = [5, 50, 95]
    shape = (len(percentiles), horizon_months)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    scheduled_wealth = np.array([101.0, 202.0], dtype=np.float64)
    diagnostics = empty_diagnostics(months=horizon_months).model_copy(
        update={"scheduled_wealth": scheduled_wealth}
    )
    return SimulationResult(
        ran_at=datetime(2026, 9, 23),
        horizon_months=horizon_months,
        num_runs=10,
        percentiles=percentiles,
        start_month=(2026, 9),
        balance_start=series.copy(),
        withdrawals_essential=series.copy(),
        withdrawals_discretionary=series.copy(),
        withdrawals_general=series.copy(),
        withdrawals_total=series.copy(),
        savings_stock_allocation=series.copy(),
        wealth_job=months.copy(),
        wealth_social_security=months.copy(),
        wealth_pension=months.copy(),
        wealth_manual=months.copy(),
        num_runs_insufficient=0,
        diagnostics=diagnostics,
        resolved_assumptions=ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.02,
            annual_stock_log_variance=0.03,
            planning_preset="fixed",
            inflation_source="manual",
        ),
    )


def test_diagnostics_and_summary_share_one_cached_run(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    diagnostics = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})
    summary = client.get(API_RESULT_SUMMARY, params={"plan_id": plan_id})

    assert diagnostics.status_code == HTTPStatus.OK
    assert summary.status_code == HTTPStatus.OK
    assert calls["n"] == 1


def test_diagnostics_returns_scheduled_wealth_from_the_cached_run(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    diagnostics = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})

    assert (
        diagnostics.json()["scheduled_wealth"]
        == result.diagnostics.scheduled_wealth.tolist()
    )


def test_summary_echoes_resolved_plan_id(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    def run(plan, **kwargs):
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    summary = client.get(API_RESULT_SUMMARY, params={"plan_id": plan_id})

    assert summary.json()["plan_id"] == plan_id


def test_simulation_failure_returns_only_error_fields(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    message = "simulation exploded"

    def run(plan, **kwargs):
        raise ValueError(message)

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    failure = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})

    assert failure.status_code == HTTP_UNPROCESSABLE
    assert failure.json() == {"error": SIMULATION_FAILED, "message": message}


def test_simulation_failure_logs_traceback(
    client: TestClient, plan_id: int, monkeypatch, caplog
) -> None:
    message = "simulation exploded"

    def run(plan, **kwargs):
        raise ValueError(message)

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    with caplog.at_level(logging.ERROR, logger="web.simulation_cache"):
        client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})

    assert message in caplog.text
    assert "Traceback" in caplog.text


def test_simulation_failure_is_not_cached(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("simulation exploded")
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})
    success = client.get(API_RESULT_DIAGNOSTICS, params={"plan_id": plan_id})

    assert success.status_code == HTTPStatus.OK
    assert calls["n"] == 2


def test_plans_refuses_missing_database_without_creating_it(tmp_path) -> None:
    missing_db_path = tmp_path / "missing.db"
    app = create_app(db_path=missing_db_path)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(API_PLANS)

    assert response.status_code == HTTP_SERVICE_UNAVAILABLE
    assert response.json()["error"] == DB_NOT_INITIALIZED
    assert not missing_db_path.exists()


def test_plans_on_blank_database_does_not_create_a_plan(
    client: TestClient, db_path
) -> None:
    response = client.get(API_PLANS)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"plans": []}
    assert PlanRepository(db_path=db_path).list() == []


def test_summary_on_blank_database_does_not_create_a_plan(
    client: TestClient, db_path
) -> None:
    missing_id = 1

    response = client.get(API_RESULT_SUMMARY, params={"plan_id": missing_id})

    assert response.status_code == HTTP_NOT_FOUND
    assert PlanRepository(db_path=db_path).list() == []


def test_plans_lists_bootstrapped_default(
    client: TestClient, plan_id: int, repo: PlanRepository
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None

    response = client.get(API_PLANS)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["plans"] == [
        {"id": plan_id, "name": stored.name, "is_default": True}
    ]


def test_plans_does_not_run_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    client.get(API_PLANS)

    assert calls["n"] == 0


def test_plan_by_name_returns_round_trippable_stored_plan(
    client: TestClient, plan_id: int, repo: PlanRepository
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None

    response = client.get(API_PLAN, params={"name": stored.name})

    assert response.status_code == HTTPStatus.OK
    assert response.json()["plan_id"] == plan_id
    assert Plan.model_validate(response.json()["plan"]) == stored


def test_ambiguous_name_returns_conflict_with_candidate_ids(
    client: TestClient, plan_id: int, repo: PlanRepository
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None
    other_id, _ = repo.create(name=f"{stored.name} ")

    response = client.get(API_PLAN, params={"name": stored.name})

    assert response.status_code == HTTP_CONFLICT
    assert response.json()["error"] == AMBIGUOUS_PLAN
    assert [item["id"] for item in response.json()["candidates"]] == [
        plan_id,
        other_id,
    ]


def test_missing_plan_id_returns_not_found(client: TestClient, plan_id: int) -> None:
    missing_id = plan_id + 999_999

    response = client.get(API_PLAN, params={"plan_id": missing_id})

    assert response.status_code == HTTP_NOT_FOUND
    assert response.json()["error"] == PLAN_NOT_FOUND


def test_series_without_series_returns_invalid_query(
    client: TestClient, plan_id: int
) -> None:
    response = client.get(API_RESULT_SERIES, params={"plan_id": plan_id})

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == INVALID_QUERY


def test_unknown_series_returns_before_running_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    unknown_series = "not_a_public_series"
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={"plan_id": plan_id, "series": unknown_series},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == UNKNOWN_SERIES
    assert calls["n"] == 0


def test_diagnostics_month_slices_the_cached_arrays(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    month = 1

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": month},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["month"] == month
    assert body["scheduled_wealth"] == [result.diagnostics.scheduled_wealth[month]]


def test_diagnostics_repeated_fields_params_select_arrays(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    requested = (DIAGNOSTICS_ARRAY_FIELDS[0], DIAGNOSTICS_ARRAY_FIELDS[1])

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": list(requested)},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    expected_fields = fields_in_source_order(requested)
    assert list(body) == diagnostics_envelope(fields=expected_fields)


def test_diagnostics_comma_fields_param_selects_arrays(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    requested = (DIAGNOSTICS_ARRAY_FIELDS[1], DIAGNOSTICS_ARRAY_FIELDS[0])

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": ",".join(requested)},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    expected_fields = fields_in_source_order(requested)
    assert list(body) == diagnostics_envelope(fields=expected_fields)
    for field in expected_fields:
        assert body[field] == getattr(result.diagnostics, field).tolist()


def test_diagnostics_comma_fields_rejects_unknown_token(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    unknown = "not_a_diagnostics_field"
    fields = f"{DIAGNOSTICS_ARRAY_FIELDS[0]},{unknown}"

    def run(plan, **kwargs):
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": fields},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == UNKNOWN_FIELD
    assert unknown in response.json()["message"]


def test_unknown_field_returns_400_before_running_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    unknown = "not_a_diagnostics_field"
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": unknown},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    body = response.json()
    assert body["error"] == UNKNOWN_FIELD
    assert body["allowed"] == list(DIAGNOSTICS_ARRAY_FIELDS)
    assert unknown in body["message"]
    assert calls["n"] == 0


def test_missing_plan_wins_over_unknown_field(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)
    missing_id = plan_id + 999_999

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": missing_id, "fields": "not_a_diagnostics_field"},
    )

    assert response.status_code == HTTP_NOT_FOUND
    assert response.json()["error"] == PLAN_NOT_FOUND
    assert calls["n"] == 0


def test_diagnostics_mixed_comma_and_repeated_fields_params(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    first = DIAGNOSTICS_ARRAY_FIELDS[0]
    second = DIAGNOSTICS_ARRAY_FIELDS[2]
    third = DIAGNOSTICS_ARRAY_FIELDS[4]
    requested = (first, second, third)

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params=[
            ("plan_id", plan_id),
            ("fields", f"{first},{second}"),
            ("fields", third),
        ],
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    expected_fields = fields_in_source_order(requested)
    assert list(body) == diagnostics_envelope(fields=expected_fields)
    for field in expected_fields:
        assert body[field] == getattr(result.diagnostics, field).tolist()


def test_diagnostics_blank_fields_param_returns_every_array(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": ""},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert list(body) == diagnostics_envelope(fields=DIAGNOSTICS_ARRAY_FIELDS)
    assert (
        body[DIAGNOSTICS_ARRAY_FIELDS[0]]
        == getattr(result.diagnostics, DIAGNOSTICS_ARRAY_FIELDS[0]).tolist()
    )


def test_diagnostics_month_and_fields_combine_over_http(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    month = 0
    field = DIAGNOSTICS_ARRAY_FIELDS[0]

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": month, "fields": field},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body[field] == [getattr(result.diagnostics, field)[month]]
    assert list(body) == diagnostics_envelope(fields=[field], month=month)


def test_diagnostics_month_out_of_range_returns_bounds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    last_month = result.horizon_months - 1

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": result.horizon_months},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    # Pinned: catches accidental drift in the month_out_of_range wording.
    assert response.json() == {
        "error": MONTH_OUT_OF_RANGE,
        "message": f"month must be between 0 and {last_month} inclusive",
        "min": 0,
        "max": last_month,
    }


def test_unknown_field_wins_over_out_of_range_month(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    unknown = "not_a_diagnostics_field"

    def run(plan, **kwargs):
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "fields": unknown, "month": -1},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == UNKNOWN_FIELD


def test_ambiguous_plan_wins_over_unknown_field(
    client: TestClient, plan_id: int, repo: PlanRepository, monkeypatch
) -> None:
    stored = repo.get_by_id(plan_id)
    assert stored is not None
    repo.create(name=f"{stored.name} ")
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"name": stored.name, "fields": "not_a_diagnostics_field"},
    )

    assert response.status_code == HTTP_CONFLICT
    assert response.json()["error"] == AMBIGUOUS_PLAN
    assert calls["n"] == 0


def test_diagnostics_negative_month_returns_bounds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    last_month = result.horizon_months - 1

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": -1},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    body = response.json()
    assert body["error"] == MONTH_OUT_OF_RANGE
    assert body["min"] == 0
    assert body["max"] == last_month


def test_diagnostics_month_on_empty_horizon_returns_no_bounds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    empty = _make_result().model_copy(
        update={
            "horizon_months": 0,
            "diagnostics": empty_diagnostics(months=0),
        }
    )

    def run(plan, **kwargs):
        return empty

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": 0},
    )

    assert response.status_code == HTTP_BAD_REQUEST
    body = response.json()
    assert body["error"] == MONTH_OUT_OF_RANGE
    assert "min" not in body
    assert "max" not in body


def test_simulation_failure_wins_over_out_of_range_month(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    def run(plan, **kwargs):
        raise RuntimeError("simulation boom")

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_DIAGNOSTICS,
        params={"plan_id": plan_id, "month": -1},
    )

    assert response.status_code == HTTP_UNPROCESSABLE
    assert response.json()["error"] == SIMULATION_FAILED


def test_series_without_parameters_returns_the_pinned_envelope(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    series = RAW_ARRAY_FIELDS[0]

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={"plan_id": plan_id, "series": series},
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert list(body) == ["plan_id", "name", "series", "month", "labels", "rows"]
    assert body["month"] is None
    assert "month_from" not in body
    assert "month_to" not in body
    assert body["labels"] == month_labels(result.start_month, result.horizon_months)


def test_series_range_slices_values_and_echoes_bounds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    series = RAW_ARRAY_FIELDS[0]
    month_from, month_to = 0, 1
    # Distinct per-cell values so a wrong slice offset cannot pass on zeros.
    distinct = np.arange(
        1.0, 1.0 + len(result.percentiles) * result.horizon_months
    ).reshape(len(result.percentiles), result.horizon_months)
    result = result.model_copy(update={series: distinct})

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={
            "plan_id": plan_id,
            "series": series,
            "month_from": month_from,
            "month_to": month_to,
        },
    )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert list(body) == [
        "plan_id",
        "name",
        "series",
        "month",
        "month_from",
        "month_to",
        "labels",
        "rows",
    ]
    assert body["month"] is None
    assert body["month_from"] == month_from
    assert body["month_to"] == month_to
    assert (
        body["labels"]
        == month_labels(result.start_month, result.horizon_months)[
            month_from : month_to + 1
        ]
    )
    assert body["rows"] == [
        {
            "percentile": percentile,
            "values": distinct[index, month_from : month_to + 1].tolist(),
        }
        for index, percentile in enumerate(result.percentiles)
    ]


def test_series_duplicate_month_params_report_one_validation_detail(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    # Regression: declaring the month params in both the dependency and the
    # handler made FastAPI report each bad value twice.
    def run(plan, **kwargs):
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={"plan_id": plan_id, "series": RAW_ARRAY_FIELDS[0], "month": "abc"},
    )

    assert response.status_code == HTTP_UNPROCESSABLE
    details = response.json()["detail"]
    assert len(details) == 1
    assert details[0]["loc"] == ["query", "month"]


def test_series_month_with_range_fails_before_running_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={
            "plan_id": plan_id,
            "series": RAW_ARRAY_FIELDS[0],
            "month": 0,
            "month_from": 0,
        },
    )

    assert response.status_code == HTTP_BAD_REQUEST
    # Pinned: the message must name both valid shapes, not forbid month_from+month_to.
    assert response.json() == {
        "error": INVALID_QUERY,
        "message": "Provide either month or a month_from/month_to range, not both",
    }
    assert calls["n"] == 0


def test_series_inverted_range_fails_before_running_simulation(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    calls = {"n": 0}

    def run(plan, **kwargs):
        calls["n"] += 1
        return _make_result()

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={
            "plan_id": plan_id,
            "series": RAW_ARRAY_FIELDS[0],
            "month_from": 1,
            "month_to": 0,
        },
    )

    assert response.status_code == HTTP_BAD_REQUEST
    assert response.json()["error"] == INVALID_RANGE
    assert calls["n"] == 0


def test_series_month_from_at_horizon_returns_bounds(
    client: TestClient, plan_id: int, monkeypatch
) -> None:
    result = _make_result()
    last_month = result.horizon_months - 1

    def run(plan, **kwargs):
        return result

    monkeypatch.setattr("web.simulation_cache.run_simulation", run)

    response = client.get(
        API_RESULT_SERIES,
        params={
            "plan_id": plan_id,
            "series": RAW_ARRAY_FIELDS[0],
            "month_from": result.horizon_months,
        },
    )

    assert response.status_code == HTTP_BAD_REQUEST
    # Pinned: catches accidental drift in the range wording.
    assert response.json() == {
        "error": MONTH_OUT_OF_RANGE,
        "message": f"month_from must be between 0 and {last_month} inclusive",
        "min": 0,
        "max": last_month,
    }

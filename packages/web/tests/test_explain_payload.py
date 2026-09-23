from datetime import datetime

import numpy as np
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS, empty_diagnostics
from simulation.result import (
    PUBLIC_ARRAY_FIELDS,
    RAW_ARRAY_FIELDS,
    ResolvedAssumptions,
    SimulationResult,
)
from web.explain import (
    HTTP_BAD_REQUEST,
    MONTH_OUT_OF_RANGE,
    PERCENTILE_NOT_APPLICABLE,
    UNKNOWN_PERCENTILE,
    UNKNOWN_SERIES,
    ExplainFailure,
    diagnostics_payload,
    series_payload,
    summary_payload,
)

from web import spending_summary


def _result() -> SimulationResult:
    percentiles = [10, 50, 90]
    months = 4
    percentile_values = np.arange(
        1.0, 1.0 + len(percentiles) * months, dtype=np.float64
    ).reshape(len(percentiles), months)
    horizon_values = np.arange(101.0, 101.0 + months, dtype=np.float64)
    scheduled_wealth = np.arange(201.0, 201.0 + months, dtype=np.float64)
    diagnostics = empty_diagnostics(months=months).model_copy(
        update={
            "scheduled_wealth": scheduled_wealth,
            "legacy_stock_allocation": 0.37,
        }
    )
    return SimulationResult(
        ran_at=datetime(2026, 9, 23, 8, 30),
        horizon_months=months,
        num_runs=250,
        percentiles=percentiles,
        start_month=(2026, 9),
        balance_start=percentile_values.copy(),
        withdrawals_essential=percentile_values.copy(),
        withdrawals_discretionary=percentile_values.copy(),
        withdrawals_general=percentile_values.copy(),
        withdrawals_total=percentile_values.copy(),
        savings_stock_allocation=percentile_values.copy(),
        wealth_job=horizon_values,
        wealth_social_security=horizon_values + 10.0,
        wealth_pension=horizon_values + 20.0,
        wealth_manual=horizon_values + 30.0,
        num_runs_insufficient=7,
        diagnostics=diagnostics,
        resolved_assumptions=ResolvedAssumptions(
            annual_inflation=0.02,
            annual_stock_return=0.05,
            annual_bond_return=0.03,
            annual_stock_log_variance=0.04,
            planning_preset="fixed",
            inflation_source="manual",
        ),
    )


def test_summary_serializes_public_scalar_and_spending_fields() -> None:
    result = _result()
    plan_id = 17
    plan_name = "Retirement"
    spending = spending_summary.from_result(result)

    payload = summary_payload(plan_id=plan_id, plan_name=plan_name, result=result)

    assert payload == {
        "plan_id": plan_id,
        "name": plan_name,
        "ran_at": result.ran_at.isoformat(),
        "horizon_months": result.horizon_months,
        "num_runs": result.num_runs,
        "percentiles": list(result.percentiles),
        "start_month": list(result.start_month),
        "num_runs_insufficient": result.num_runs_insufficient,
        "resolved_assumptions": result.resolved_assumptions.model_dump(mode="json"),
        "spending": {
            "initial": spending.initial,
            "worst_case": spending.worst_case,
        },
    }
    assert "balance_start" not in payload
    assert "diagnostics" not in payload
    assert "engine_version" not in payload


def test_diagnostics_serializes_every_array_and_legacy_allocation() -> None:
    result = _result()
    plan_id = 18
    plan_name = "Diagnostics"

    payload = diagnostics_payload(
        plan_id=plan_id,
        plan_name=plan_name,
        result=result,
    )

    assert payload["plan_id"] == plan_id
    assert payload["name"] == plan_name
    assert payload["scheduled_wealth"] == result.diagnostics.scheduled_wealth.tolist()
    assert (
        payload["legacy_stock_allocation"] == result.diagnostics.legacy_stock_allocation
    )
    assert all(field in payload for field in DIAGNOSTICS_ARRAY_FIELDS)


def test_percentile_series_without_percentile_returns_every_row() -> None:
    result = _result()
    series = RAW_ARRAY_FIELDS[0]

    payload = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=series,
        month=None,
        percentile=None,
    )

    assert not isinstance(payload, ExplainFailure)
    assert payload["month"] is None
    assert payload["rows"] == [
        {"percentile": percentile, "values": getattr(result, series)[index].tolist()}
        for index, percentile in enumerate(result.percentiles)
    ]


def test_percentile_series_with_percentile_selects_that_row() -> None:
    result = _result()
    series = RAW_ARRAY_FIELDS[0]
    row_index = 1
    chosen_percentile = result.percentiles[row_index]

    payload = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=series,
        month=None,
        percentile=chosen_percentile,
    )

    assert not isinstance(payload, ExplainFailure)
    assert payload["rows"] == [
        {
            "percentile": chosen_percentile,
            "values": getattr(result, series)[row_index].tolist(),
        }
    ]


def test_percentile_series_with_month_returns_one_cell_per_row() -> None:
    result = _result()
    series = RAW_ARRAY_FIELDS[1]
    month = 2

    payload = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=series,
        month=month,
        percentile=None,
    )

    assert not isinstance(payload, ExplainFailure)
    assert payload["rows"] == [
        {
            "percentile": percentile,
            "values": [getattr(result, series)[index, month]],
        }
        for index, percentile in enumerate(result.percentiles)
    ]


def test_unknown_series_lists_allowed_public_series() -> None:
    result = _result()

    failure = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series="not-a-series",
        month=None,
        percentile=None,
    )

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == UNKNOWN_SERIES
    assert list(failure.allowed) == list(PUBLIC_ARRAY_FIELDS)
    body = failure.body()
    assert body["error"] == UNKNOWN_SERIES
    assert body["allowed"] == list(PUBLIC_ARRAY_FIELDS)


def test_unknown_percentile_lists_configured_percentiles() -> None:
    result = _result()
    unknown_percentile = max(result.percentiles) + 1

    failure = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=RAW_ARRAY_FIELDS[0],
        month=None,
        percentile=unknown_percentile,
    )

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == UNKNOWN_PERCENTILE
    assert list(failure.allowed) == result.percentiles
    body = failure.body()
    assert body["error"] == UNKNOWN_PERCENTILE
    assert body["allowed"] == result.percentiles


def test_horizon_series_without_percentile_returns_one_unlabeled_row() -> None:
    result = _result()
    series = "wealth_job"

    payload = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=series,
        month=None,
        percentile=None,
    )

    assert not isinstance(payload, ExplainFailure)
    assert payload["rows"] == [
        {"percentile": None, "values": result.wealth_job.tolist()}
    ]


def test_horizon_series_rejects_percentile() -> None:
    result = _result()

    failure = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series="wealth_job",
        month=None,
        percentile=result.percentiles[0],
    )

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == PERCENTILE_NOT_APPLICABLE
    body = failure.body()
    assert body["error"] == PERCENTILE_NOT_APPLICABLE


def test_month_equal_to_horizon_is_out_of_range() -> None:
    result = _result()

    failure = series_payload(
        plan_id=1,
        plan_name="Plan",
        result=result,
        series=RAW_ARRAY_FIELDS[0],
        month=result.horizon_months,
        percentile=None,
    )

    assert isinstance(failure, ExplainFailure)
    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == MONTH_OUT_OF_RANGE
    assert failure.min_month == 0
    assert failure.max_month == result.horizon_months - 1
    body = failure.body()
    assert body["error"] == MONTH_OUT_OF_RANGE
    assert body["min"] == 0
    assert body["max"] == result.horizon_months - 1

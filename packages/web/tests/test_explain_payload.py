from datetime import datetime

import numpy as np
import pytest
from core.defaults import default_plan
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS, empty_diagnostics
from simulation.result import (
    HORIZON_ARRAY_FIELDS,
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
    ApiError,
    ScopedResult,
    diagnostics_payload,
    series_payload,
    summary_payload,
)

from web import spending_summary


def _scoped(
    result: SimulationResult, *, plan_id: int = 1, plan_name: str = "Plan"
) -> ScopedResult:
    plan = default_plan().model_copy(update={"name": plan_name})
    return ScopedResult(plan_id=plan_id, plan=plan, result=result)


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

    payload = summary_payload(_scoped(result, plan_id=plan_id, plan_name=plan_name))

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

    payload = diagnostics_payload(_scoped(result, plan_id=plan_id, plan_name=plan_name))

    expected_keys = {
        "plan_id",
        "name",
        "legacy_stock_allocation",
        *DIAGNOSTICS_ARRAY_FIELDS,
    }
    assert set(payload.keys()) == expected_keys
    assert payload["plan_id"] == plan_id
    assert payload["name"] == plan_name
    assert (
        payload["legacy_stock_allocation"] == result.diagnostics.legacy_stock_allocation
    )
    for field in DIAGNOSTICS_ARRAY_FIELDS:
        assert payload[field] == getattr(result.diagnostics, field).tolist()


def test_percentile_series_without_percentile_returns_every_row() -> None:
    result = _result()
    series = RAW_ARRAY_FIELDS[0]
    plan_id = 1
    plan_name = "Plan"

    payload = series_payload(
        scoped=_scoped(result, plan_id=plan_id, plan_name=plan_name),
        series=series,
        month=None,
        percentile=None,
    )

    assert payload["plan_id"] == plan_id
    assert payload["name"] == plan_name
    assert payload["series"] == series
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
        scoped=_scoped(result, plan_id=1, plan_name="Plan"),
        series=series,
        month=None,
        percentile=chosen_percentile,
    )

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
        scoped=_scoped(result, plan_id=1, plan_name="Plan"),
        series=series,
        month=month,
        percentile=None,
    )

    assert payload["rows"] == [
        {
            "percentile": percentile,
            "values": [getattr(result, series)[index, month]],
        }
        for index, percentile in enumerate(result.percentiles)
    ]


def test_unknown_series_lists_allowed_public_series() -> None:
    result = _result()
    unknown_series = "not-a-series"

    with pytest.raises(ApiError) as raised:
        series_payload(
            scoped=_scoped(result),
            series=unknown_series,
            month=None,
            percentile=None,
        )
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == UNKNOWN_SERIES
    assert list(failure.allowed) == list(PUBLIC_ARRAY_FIELDS)
    expected_body = {
        "error": failure.code,
        "message": failure.message,
        "allowed": list(failure.allowed),
    }
    assert failure.body() == expected_body


def test_unknown_percentile_lists_configured_percentiles() -> None:
    result = _result()
    unknown_percentile = max(result.percentiles) + 1

    with pytest.raises(ApiError) as raised:
        series_payload(
            scoped=_scoped(result),
            series=RAW_ARRAY_FIELDS[0],
            month=None,
            percentile=unknown_percentile,
        )
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == UNKNOWN_PERCENTILE
    assert list(failure.allowed) == result.percentiles
    expected_body = {
        "error": failure.code,
        "message": failure.message,
        "allowed": list(failure.allowed),
    }
    assert failure.body() == expected_body


def test_horizon_series_without_percentile_returns_one_unlabeled_row() -> None:
    result = _result()
    series = "wealth_job"

    payload = series_payload(
        scoped=_scoped(result, plan_id=1, plan_name="Plan"),
        series=series,
        month=None,
        percentile=None,
    )

    assert payload["rows"] == [
        {"percentile": None, "values": result.wealth_job.tolist()}
    ]


def test_horizon_series_rejects_percentile() -> None:
    result = _result()

    with pytest.raises(ApiError) as raised:
        series_payload(
            scoped=_scoped(result),
            series="wealth_job",
            month=None,
            percentile=result.percentiles[0],
        )
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == PERCENTILE_NOT_APPLICABLE
    expected_body = {
        "error": failure.code,
        "message": failure.message,
    }
    assert failure.body() == expected_body


def test_empty_horizon_summary_has_no_spending_amounts() -> None:
    result = _result()
    plan_name = "Plan"
    empty = result.model_copy(
        update={
            "horizon_months": 0,
            "withdrawals_total": np.zeros(
                (len(result.percentiles), 0), dtype=np.float64
            ),
        }
    )

    payload = summary_payload(_scoped(empty, plan_name=plan_name))

    assert payload["horizon_months"] == 0
    assert payload["spending"] == {"initial": None, "worst_case": None}


def test_month_on_empty_horizon_does_not_invert_bounds() -> None:
    result = _result()
    empty = result.model_copy(update={"horizon_months": 0})
    month = 0

    with pytest.raises(ApiError) as raised:
        series_payload(
            scoped=_scoped(empty),
            series=RAW_ARRAY_FIELDS[0],
            month=month,
            percentile=None,
        )
    failure = raised.value

    assert failure.code == MONTH_OUT_OF_RANGE
    assert failure.month_bounds is None
    assert "min" not in failure.body()
    assert "max" not in failure.body()


def test_horizon_series_with_month_returns_one_element_list() -> None:
    result = _result()
    series = HORIZON_ARRAY_FIELDS[0]
    month = 1

    payload = series_payload(
        scoped=_scoped(result, plan_id=1, plan_name="Plan"),
        series=series,
        month=month,
        percentile=None,
    )

    expected_values = [getattr(result, series)[month]]

    assert payload["rows"] == [{"percentile": None, "values": expected_values}]


def test_month_equal_to_horizon_is_out_of_range() -> None:
    result = _result()

    with pytest.raises(ApiError) as raised:
        series_payload(
            scoped=_scoped(result),
            series=RAW_ARRAY_FIELDS[0],
            month=result.horizon_months,
            percentile=None,
        )
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == MONTH_OUT_OF_RANGE
    bounds = failure.month_bounds
    assert bounds is not None
    assert bounds == (0, result.horizon_months - 1)
    expected_body = {
        "error": failure.code,
        "message": failure.message,
        "min": bounds[0],
        "max": bounds[1],
    }
    assert failure.body() == expected_body

import numpy as np
import pytest
from simulation.diagnostics import DIAGNOSTICS_ARRAY_FIELDS, empty_diagnostics
from simulation.result import (
    HORIZON_ARRAY_FIELDS,
    PUBLIC_ARRAY_FIELDS,
    RAW_ARRAY_FIELDS,
)
from web.explain import (
    HTTP_BAD_REQUEST,
    MONTH_OUT_OF_RANGE,
    PERCENTILE_NOT_APPLICABLE,
    UNKNOWN_FIELD,
    UNKNOWN_PERCENTILE,
    UNKNOWN_SERIES,
    ApiError,
    diagnostics_payload,
    series_payload,
    summary_payload,
)

from web import spending_summary

from .explain_fixtures import diagnostics_envelope, fields_in_source_order
from .explain_fixtures import sample_simulation_result as _result
from .explain_fixtures import scoped_result as _scoped


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


def test_diagnostics_serializes_every_array_and_legacy_allocation() -> None:
    result = _result()
    plan_id = 18
    plan_name = "Diagnostics"

    payload = diagnostics_payload(_scoped(result, plan_id=plan_id, plan_name=plan_name))

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


def test_diagnostics_without_parameters_keeps_envelope_and_array_order() -> None:
    result = _result()

    payload = diagnostics_payload(_scoped(result))

    assert list(payload) == diagnostics_envelope(fields=DIAGNOSTICS_ARRAY_FIELDS)
    assert "month" not in payload


def test_diagnostics_month_slices_every_array_to_one_element() -> None:
    result = _result()
    month = 2

    payload = diagnostics_payload(_scoped(result), month=month)

    assert payload["month"] == month
    assert (
        payload["legacy_stock_allocation"] == result.diagnostics.legacy_stock_allocation
    )
    for field in DIAGNOSTICS_ARRAY_FIELDS:
        assert payload[field] == [getattr(result.diagnostics, field)[month]]


def test_diagnostics_month_zero_slices_the_first_element() -> None:
    result = _result()

    payload = diagnostics_payload(_scoped(result), month=0)

    for field in DIAGNOSTICS_ARRAY_FIELDS:
        assert payload[field] == [getattr(result.diagnostics, field)[0]]


def test_diagnostics_fields_selects_only_named_arrays_in_source_order() -> None:
    result = _result()
    requested = (DIAGNOSTICS_ARRAY_FIELDS[2], DIAGNOSTICS_ARRAY_FIELDS[0])
    fields = [requested[0], requested[1], requested[0]]

    payload = diagnostics_payload(_scoped(result), fields=fields)

    expected_fields = fields_in_source_order(requested)
    assert list(payload) == diagnostics_envelope(fields=expected_fields)


def test_diagnostics_fields_accepts_comma_separated_tokens() -> None:
    result = _result()
    requested = (DIAGNOSTICS_ARRAY_FIELDS[0], DIAGNOSTICS_ARRAY_FIELDS[3])
    fields = [f" {requested[0]} , {requested[1]} "]

    payload = diagnostics_payload(_scoped(result), fields=fields)

    expected_fields = fields_in_source_order(requested)
    assert list(payload) == diagnostics_envelope(fields=expected_fields)
    for field in expected_fields:
        assert payload[field] == getattr(result.diagnostics, field).tolist()


def test_diagnostics_bare_string_fields_are_accepted() -> None:
    result = _result()
    requested = (DIAGNOSTICS_ARRAY_FIELDS[0], DIAGNOSTICS_ARRAY_FIELDS[2])
    fields = f"{requested[0]},{requested[1]}"

    payload = diagnostics_payload(_scoped(result), fields=fields)

    assert list(payload) == diagnostics_envelope(
        fields=fields_in_source_order(requested)
    )


def test_diagnostics_bare_blank_string_returns_every_array() -> None:
    payload = diagnostics_payload(_scoped(_result()), fields="")

    assert list(payload) == diagnostics_envelope(fields=DIAGNOSTICS_ARRAY_FIELDS)


def test_diagnostics_blank_fields_returns_every_array() -> None:
    result = _result()

    payload = diagnostics_payload(_scoped(result), fields=["", " , "])

    assert list(payload) == diagnostics_envelope(fields=DIAGNOSTICS_ARRAY_FIELDS)


def test_diagnostics_month_and_fields_combine() -> None:
    result = _result()
    month = 1
    field = DIAGNOSTICS_ARRAY_FIELDS[1]

    payload = diagnostics_payload(_scoped(result), month=month, fields=[field])

    assert payload[field] == [getattr(result.diagnostics, field)[month]]
    assert list(payload) == diagnostics_envelope(fields=[field], month=month)


def test_diagnostics_unknown_field_is_rejected_with_allowed_list() -> None:
    unknown = "not_a_diagnostics_field"

    with pytest.raises(ApiError) as raised:
        diagnostics_payload(_scoped(_result()), fields=[unknown])
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == UNKNOWN_FIELD
    assert failure.allowed == DIAGNOSTICS_ARRAY_FIELDS
    assert failure.body()["allowed"] == list(DIAGNOSTICS_ARRAY_FIELDS)
    assert unknown in failure.message


def test_diagnostics_unknown_field_wins_over_out_of_range_month() -> None:
    unknown = "not_a_diagnostics_field"

    with pytest.raises(ApiError) as raised:
        diagnostics_payload(_scoped(_result()), month=-1, fields=[unknown])
    failure = raised.value

    assert failure.code == UNKNOWN_FIELD
    assert unknown in failure.message


@pytest.mark.parametrize("case", ["negative", "at_horizon"])
def test_diagnostics_month_out_of_range_reports_bounds(case: str) -> None:
    result = _result()
    month = -1 if case == "negative" else result.horizon_months

    with pytest.raises(ApiError) as raised:
        diagnostics_payload(_scoped(result), month=month)
    failure = raised.value

    assert failure.status_code == HTTP_BAD_REQUEST
    assert failure.code == MONTH_OUT_OF_RANGE
    assert failure.month_bounds == (0, result.horizon_months - 1)
    assert failure.body() == {
        "error": MONTH_OUT_OF_RANGE,
        "message": failure.message,
        "min": 0,
        "max": result.horizon_months - 1,
    }


def test_diagnostics_month_on_empty_horizon_has_no_bounds() -> None:
    empty = _result().model_copy(
        update={
            "horizon_months": 0,
            "diagnostics": empty_diagnostics(months=0),
        }
    )

    with pytest.raises(ApiError) as raised:
        diagnostics_payload(_scoped(empty), month=0)
    failure = raised.value

    assert failure.code == MONTH_OUT_OF_RANGE
    assert failure.month_bounds is None
    assert "min" not in failure.body()
    assert "max" not in failure.body()

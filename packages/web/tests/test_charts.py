from datetime import datetime

import numpy as np
import pytest
from simulation.result import SimulationResult

from web import charts


def _make_result(*, percentiles: list[int], horizon_months: int) -> SimulationResult:
    shape = (len(percentiles), horizon_months)
    series = np.zeros(shape, dtype=np.float64)
    months = np.zeros(horizon_months, dtype=np.float64)
    return SimulationResult(
        ran_at=datetime(2026, 1, 1),
        horizon_months=horizon_months,
        num_runs=10,
        percentiles=list(percentiles),
        start_month=(2026, 1),
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
    )


def test_default_chart_is_spending_total():
    assert charts.DEFAULT_CHART == charts.SPENDING_TOTAL


def test_resolve_returns_input_when_valid():
    expected = charts.PORTFOLIO
    assert charts.resolve_chart_type(expected) == expected


@pytest.mark.parametrize("raw", [None, "", "not-a-chart"])
def test_resolve_falls_back_to_default_when_invalid(raw):
    assert charts.resolve_chart_type(raw) == charts.DEFAULT_CHART


def test_all_chart_types_resolve_to_themselves():
    for chart_type in charts.CHART_TYPES:
        assert charts.resolve_chart_type(chart_type) == chart_type


def test_month_labels_length_matches_horizon():
    horizon = 5
    labels = charts.month_labels((2026, 1), horizon)
    assert len(labels) == horizon


def test_month_labels_start_and_year_rollover():
    start_year, start_month = 2026, 11
    labels = charts.month_labels((start_year, start_month), 3)
    assert labels == ["2026-11", "2026-12", "2027-01"]


def test_wealth_index_three_percentiles_maps_low_mid_high():
    n = 3
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_LOW, n) == 0
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_MID, n) == 1
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_HIGH, n) == 2


def test_wealth_index_other_lengths_use_first_middle_last():
    n = 5
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_LOW, n) == 0
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_MID, n) == n // 2
    assert charts.wealth_percentile_index(charts.WEALTH_COMPOSITION_HIGH, n) == n - 1


def test_wealth_index_rejects_non_wealth_chart():
    with pytest.raises(ValueError):
        charts.wealth_percentile_index(charts.PORTFOLIO, 3)


def test_portfolio_has_one_trace_per_percentile_named_by_percentile():
    percentiles = [5, 50, 95]
    horizon = 4
    result = _make_result(percentiles=percentiles, horizon_months=horizon)

    figure = charts.build_figure(result, charts.PORTFOLIO)

    traces = figure["data"]
    assert len(traces) == len(percentiles)
    assert [trace["name"] for trace in traces] == [f"{p}th" for p in percentiles]


def test_band_chart_x_axis_uses_start_month_labels():
    percentiles = [50]
    horizon = 3
    result = _make_result(percentiles=percentiles, horizon_months=horizon)

    figure = charts.build_figure(result, charts.SPENDING_TOTAL)

    expected_x = charts.month_labels(result.start_month, horizon)
    assert list(figure["data"][0]["x"]) == expected_x


def test_band_chart_y_comes_from_matching_source_row():
    percentiles = [5, 95]
    horizon = 2
    result = _make_result(percentiles=percentiles, horizon_months=horizon)
    result.withdrawals_total[1, :] = np.array([111.0, 222.0])

    figure = charts.build_figure(result, charts.SPENDING_TOTAL)

    assert list(figure["data"][1]["y"]) == [111.0, 222.0]


def test_wealth_composition_has_savings_plus_four_income_layers():
    percentiles = [5, 50, 95]
    result = _make_result(percentiles=percentiles, horizon_months=3)

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_MID)

    expected_names = ["Savings", "Job", "Social Security", "Pension", "Manual"]
    assert [trace["name"] for trace in figure["data"]] == expected_names


def test_wealth_composition_savings_trace_uses_selected_percentile_row():
    percentiles = [5, 50, 95]
    horizon = 2
    result = _make_result(percentiles=percentiles, horizon_months=horizon)
    high_index = charts.wealth_percentile_index(
        charts.WEALTH_COMPOSITION_HIGH, len(percentiles)
    )
    result.balance_start[high_index, :] = np.array([10.0, 20.0])

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_HIGH)

    savings_trace = figure["data"][0]
    assert savings_trace["name"] == "Savings"
    assert list(savings_trace["y"]) == [10.0, 20.0]


def test_wealth_composition_traces_share_one_stackgroup():
    result = _make_result(percentiles=[5, 50, 95], horizon_months=3)

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_LOW)

    stackgroups = {trace["stackgroup"] for trace in figure["data"]}
    assert len(stackgroups) == 1


def test_wealth_composition_traces_hover_on_points_not_fills():
    """Plotly's default fill hit-catcher for stackgroup traces sits above the
    drag layer but doesn't reliably trigger "x unified" hover (a known
    plotly.js limitation: https://github.com/plotly/plotly.js/issues/6325).
    Forcing hoveron="points" removes the fill hit-catcher's pointer capture
    so the mouse always reaches the drag layer underneath."""
    result = _make_result(percentiles=[5, 50, 95], horizon_months=3)

    figure = charts.build_figure(result, charts.WEALTH_COMPOSITION_LOW)

    assert all(trace["hoveron"] == "points" for trace in figure["data"])


def test_chart_options_cover_all_chart_types_in_order():
    result = _make_result(percentiles=[5, 50, 95], horizon_months=2)

    values = [value for value, _label in charts.chart_options(result)]

    assert values == list(charts.CHART_TYPES)


def test_chart_options_wealth_labels_use_actual_percentiles():
    percentiles = [5, 50, 95]
    result = _make_result(percentiles=percentiles, horizon_months=2)

    options = dict(charts.chart_options(result))

    low_idx = charts.wealth_percentile_index(
        charts.WEALTH_COMPOSITION_LOW, len(percentiles)
    )
    assert (
        options[charts.WEALTH_COMPOSITION_LOW] == f"Wealth · {percentiles[low_idx]}th"
    )


@pytest.mark.parametrize(
    "chart_type",
    [
        charts.PORTFOLIO,
        charts.SPENDING_TOTAL,
        charts.ASSET_ALLOCATION_SAVINGS,
        charts.WEALTH_COMPOSITION_LOW,
        charts.WEALTH_COMPOSITION_MID,
        charts.WEALTH_COMPOSITION_HIGH,
    ],
)
def test_build_figure_uses_unified_x_hovermode_for_stable_tooltips(chart_type):
    """Default Plotly hovermode ("closest") only shows a tooltip when the
    cursor is within pixel distance of a line, and flips between traces as
    the cursor's y drifts relative to line-only ("mode=lines") traces. Pinning
    hovermode to "x unified" shows every trace at the hovered x regardless of
    cursor y, so the tooltip is stable across the whole plot area."""
    result = _make_result(percentiles=[5, 50, 95], horizon_months=3)

    figure = charts.build_figure(result, chart_type)

    assert figure["layout"]["hovermode"] == "x unified"


def test_band_chart_hover_lists_lowest_percentile_last():
    """Traces are added in ascending percentile order (lowest first) so the
    legend and line z-order stay stable, but "x unified" hover otherwise
    lists them top-to-bottom in that same (ascending) order, showing the
    lowest percentile at the top. Reversing legend.traceorder flips only the
    hover listing so the lowest percentile appears at the bottom."""
    percentiles = [5, 50, 95]
    result = _make_result(percentiles=percentiles, horizon_months=2)

    figure = charts.build_figure(result, charts.SPENDING_TOTAL)

    assert figure["layout"]["legend"]["traceorder"] == "reversed"
    assert [trace["name"] for trace in figure["data"]] == [
        f"{p}th" for p in percentiles
    ]


@pytest.mark.parametrize(
    "chart_type",
    [
        charts.PORTFOLIO,
        charts.SPENDING_TOTAL,
        charts.WEALTH_COMPOSITION_LOW,
        charts.WEALTH_COMPOSITION_MID,
        charts.WEALTH_COMPOSITION_HIGH,
    ],
)
def test_dollar_charts_format_hover_as_whole_dollars(chart_type):
    result = _make_result(percentiles=[5, 50, 95], horizon_months=2)

    figure = charts.build_figure(result, chart_type)

    assert figure["layout"]["yaxis"]["hoverformat"] == charts.HOVERFORMAT_DOLLAR


def test_savings_allocation_formats_hover_as_percent_one_decimal():
    result = _make_result(percentiles=[5, 50, 95], horizon_months=2)

    figure = charts.build_figure(result, charts.ASSET_ALLOCATION_SAVINGS)

    assert figure["layout"]["yaxis"]["hoverformat"] == charts.HOVERFORMAT_PERCENT

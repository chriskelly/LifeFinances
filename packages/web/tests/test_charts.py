import pytest

from web import charts


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

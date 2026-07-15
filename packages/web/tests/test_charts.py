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

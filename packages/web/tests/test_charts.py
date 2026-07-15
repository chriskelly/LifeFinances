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

from __future__ import annotations

import plotly.graph_objects as go
from simulation.result import SimulationResult

from web.calendar_months import month_labels, padded_month_range

PORTFOLIO = "portfolio"
SPENDING_TOTAL = "spending-total"
INCOME_BY_SOURCE = "income-by-source"
ASSET_ALLOCATION_SAVINGS = "asset-allocation-savings-portfolio"
WEALTH_COMPOSITION_LOW = "wealth-composition-low"
WEALTH_COMPOSITION_MID = "wealth-composition-mid"
WEALTH_COMPOSITION_HIGH = "wealth-composition-high"

DEFAULT_CHART = SPENDING_TOTAL

CHART_TYPES: tuple[str, ...] = (
    PORTFOLIO,
    SPENDING_TOTAL,
    INCOME_BY_SOURCE,
    ASSET_ALLOCATION_SAVINGS,
    WEALTH_COMPOSITION_LOW,
    WEALTH_COMPOSITION_MID,
    WEALTH_COMPOSITION_HIGH,
)


def resolve_chart_type(raw: str | None) -> str:
    if raw in CHART_TYPES:
        return raw
    return DEFAULT_CHART


_WEALTH_CHART_TYPES = frozenset(
    {
        WEALTH_COMPOSITION_LOW,
        WEALTH_COMPOSITION_MID,
        WEALTH_COMPOSITION_HIGH,
    }
)


_STATIC_LABELS = {
    PORTFOLIO: "Portfolio balance",
    SPENDING_TOTAL: "Total spending",
    INCOME_BY_SOURCE: "Income by source",
    ASSET_ALLOCATION_SAVINGS: "Savings allocation",
}


def chart_options(result: SimulationResult) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    for value in CHART_TYPES:
        static = _STATIC_LABELS.get(value)
        if static is not None:
            options.append((value, static))
            continue
        idx = wealth_percentile_index(value, len(result.percentiles))
        options.append((value, f"Wealth · {result.percentiles[idx]}th"))
    return options


def wealth_percentile_index(chart_type: str, num_percentiles: int) -> int:
    if chart_type == WEALTH_COMPOSITION_LOW:
        return 0
    if chart_type == WEALTH_COMPOSITION_HIGH:
        return num_percentiles - 1
    if chart_type == WEALTH_COMPOSITION_MID:
        return num_percentiles // 2
    raise ValueError(f"not a wealth-composition chart: {chart_type!r}")


_BAND_SOURCE = {
    PORTFOLIO: "balance_start",
    SPENDING_TOTAL: "withdrawals_total",
    ASSET_ALLOCATION_SAVINGS: "savings_stock_allocation",
}

# Legend labels are shared by the two stacked charts so they cannot drift.
_INCOME_SOURCES = (
    ("Job", "job"),
    ("Social Security", "social_security"),
    ("Pension", "pension"),
    ("Manual", "manual"),
)

_WEALTH_INCOME_LAYERS = tuple(
    (label, f"wealth_{key}") for label, key in _INCOME_SOURCES
)

_WEALTH_STACKGROUP = "wealth"

# Post-tax real-dollar monthly flows on the expected path (one value per month,
# not a percentile band).
_INCOME_FLOW_LAYERS = tuple(
    (label, f"net_income_{key}") for label, key in _INCOME_SOURCES
)

_INCOME_STACKGROUP = "income"

# "x unified" matches on hovered x and shows every trace, so tooltips stay
# stable across the plot (unlike default "closest", which flips between lines).
_HOVERMODE = "x unified"

# d3-format via yaxis.hoverformat. Allocation is a 0–1 fraction (".1%" → one
# decimal percent). lock_percent_axis also pins range to PERCENT_Y_RANGE.
HOVERFORMAT_DOLLAR = "$,.0f"
HOVERFORMAT_PERCENT = ".1%"
TICKFORMAT_PERCENT = ".0%"
PERCENT_Y_RANGE = (0.0, 1.0)

# Classic Plotly blue; translucent band between outer percentiles only.
BAND_FILLCOLOR = "rgba(31, 119, 180, 0.2)"

# Blank axis on each side, one month per this many months of horizon (minimum
# one). Plotly's date-axis autorange is the data extent, which puts the first and
# last month exactly on the plot edges; on a long horizon the hit window at those
# edges is a sub-pixel sliver clipped by the boundary, so the pointer resolves to
# the neighbouring month. Scaling the margin with the horizon keeps it near 1% of
# the plot width (a few pixels), enough to clear the clipped edge at typical
# chart widths.
_X_HOVER_MARGIN_MONTHS_PER = 100


def _x_axis_range(result: SimulationResult) -> list[str]:
    horizon_months = max(result.horizon_months, 0)
    pad_months = max(1, horizon_months // _X_HOVER_MARGIN_MONTHS_PER)
    return padded_month_range(
        result.start_month,
        horizon_months,
        pad_months=pad_months,
    )


def _apply_shared_layout(
    figure: go.Figure,
    result: SimulationResult,
    *,
    yaxis: dict[str, object],
) -> None:
    """Apply the layout every chart shares.

    The x-axis is always the simulation month axis, so its range is always the
    padded month span.
    """
    figure.update_layout(
        hovermode=_HOVERMODE,
        legend={"traceorder": "reversed"},
        xaxis={"range": _x_axis_range(result)},
        yaxis=yaxis,
    )


def _band_figure(
    result: SimulationResult,
    source_field: str,
    *,
    hoverformat: str,
    lock_percent_axis: bool = False,
) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    series = getattr(result, source_field)
    figure = go.Figure()
    if len(result.percentiles) >= 2:
        figure.add_trace(
            go.Scatter(
                x=x,
                y=series[-1, :].tolist(),
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
                name="band-high",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=x,
                y=series[0, :].tolist(),
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor=BAND_FILLCOLOR,
                showlegend=False,
                hoverinfo="skip",
                name="band-low",
            )
        )
    for row, percentile in enumerate(result.percentiles):
        figure.add_trace(
            go.Scatter(
                x=x,
                y=series[row, :].tolist(),
                mode="lines",
                name=f"{percentile}th",
            )
        )
    yaxis: dict[str, object] = {"hoverformat": hoverformat}
    if lock_percent_axis:
        yaxis["range"] = list(PERCENT_Y_RANGE)
        yaxis["tickformat"] = TICKFORMAT_PERCENT
    _apply_shared_layout(figure, result, yaxis=yaxis)
    return figure


def _wealth_composition_figure(result: SimulationResult, chart_type: str) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    row = wealth_percentile_index(chart_type, len(result.percentiles))
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x,
            y=result.balance_start[row, :].tolist(),
            mode="lines",
            name="Savings",
            stackgroup=_WEALTH_STACKGROUP,
            hoveron="points",
        )
    )
    for label, field in _WEALTH_INCOME_LAYERS:
        figure.add_trace(
            go.Scatter(
                x=x,
                y=getattr(result, field).tolist(),
                mode="lines",
                name=label,
                stackgroup=_WEALTH_STACKGROUP,
                hoveron="points",
            )
        )
    _apply_shared_layout(figure, result, yaxis={"hoverformat": HOVERFORMAT_DOLLAR})
    return figure


def _income_by_source_figure(result: SimulationResult) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    figure = go.Figure()
    for label, field in _INCOME_FLOW_LAYERS:
        figure.add_trace(
            go.Scatter(
                x=x,
                y=getattr(result.diagnostics, field).tolist(),
                mode="lines",
                name=label,
                stackgroup=_INCOME_STACKGROUP,
                hoveron="points",
            )
        )
    # Read the total instead of summing the layers: in a month with no gross
    # income the layers are zero while the total keeps that month's residual
    # tax, so the dotted line can sit off the stack.
    figure.add_trace(
        go.Scatter(
            x=x,
            y=result.diagnostics.net_income_total.tolist(),
            mode="lines",
            name="Total net income",
            line={"dash": "dot"},
        )
    )
    _apply_shared_layout(figure, result, yaxis={"hoverformat": HOVERFORMAT_DOLLAR})
    return figure


def build_figure(result: SimulationResult, chart_type: str) -> dict:
    source_field = _BAND_SOURCE.get(chart_type)
    if source_field is not None:
        is_alloc = chart_type == ASSET_ALLOCATION_SAVINGS
        return _band_figure(
            result,
            source_field,
            hoverformat=HOVERFORMAT_PERCENT if is_alloc else HOVERFORMAT_DOLLAR,
            lock_percent_axis=is_alloc,
        ).to_plotly_json()
    if chart_type in _WEALTH_CHART_TYPES:
        return _wealth_composition_figure(result, chart_type).to_plotly_json()
    if chart_type == INCOME_BY_SOURCE:
        return _income_by_source_figure(result).to_plotly_json()
    raise ValueError(f"unsupported chart type: {chart_type!r}")

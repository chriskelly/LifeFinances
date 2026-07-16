from __future__ import annotations

import plotly.graph_objects as go
from simulation.result import SimulationResult

PORTFOLIO = "portfolio"
SPENDING_TOTAL = "spending-total"
ASSET_ALLOCATION_SAVINGS = "asset-allocation-savings-portfolio"
WEALTH_COMPOSITION_LOW = "wealth-composition-low"
WEALTH_COMPOSITION_MID = "wealth-composition-mid"
WEALTH_COMPOSITION_HIGH = "wealth-composition-high"

DEFAULT_CHART = SPENDING_TOTAL

CHART_TYPES: tuple[str, ...] = (
    PORTFOLIO,
    SPENDING_TOTAL,
    ASSET_ALLOCATION_SAVINGS,
    WEALTH_COMPOSITION_LOW,
    WEALTH_COMPOSITION_MID,
    WEALTH_COMPOSITION_HIGH,
)


def resolve_chart_type(raw: str | None) -> str:
    if raw in CHART_TYPES:
        return raw  # type: ignore[return-value]
    return DEFAULT_CHART


def month_labels(start_month: tuple[int, int], horizon_months: int) -> list[str]:
    year, month = start_month
    labels: list[str] = []
    for _ in range(horizon_months):
        labels.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1
    return labels


_WEALTH_POSITION = {
    WEALTH_COMPOSITION_LOW: "low",
    WEALTH_COMPOSITION_MID: "mid",
    WEALTH_COMPOSITION_HIGH: "high",
}


_STATIC_LABELS = {
    PORTFOLIO: "Portfolio balance",
    SPENDING_TOTAL: "Total spending",
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
    position = _WEALTH_POSITION.get(chart_type)
    if position is None:
        raise ValueError(f"not a wealth-composition chart: {chart_type!r}")
    if position == "low":
        return 0
    if position == "high":
        return num_percentiles - 1
    return num_percentiles // 2


_BAND_SOURCE = {
    PORTFOLIO: "balance_start",
    SPENDING_TOTAL: "withdrawals_total",
    ASSET_ALLOCATION_SAVINGS: "savings_stock_allocation",
}

_WEALTH_INCOME_LAYERS = (
    ("Job", "wealth_job"),
    ("Social Security", "wealth_social_security"),
    ("Pension", "wealth_pension"),
    ("Manual", "wealth_manual"),
)

_WEALTH_STACKGROUP = "wealth"

# Plotly's default hovermode ("closest") only shows a tooltip when the
# cursor is within pixel distance of a line's rendered point, and it flips
# between traces as the cursor's y drifts relative to line-only traces.
# "x unified" instead matches purely on the hovered x and shows every trace
# at that x, so the tooltip stays stable across the whole plot area.
_HOVERMODE = "x unified"


def _band_figure(result: SimulationResult, source_field: str) -> go.Figure:
    x = month_labels(result.start_month, result.horizon_months)
    series = getattr(result, source_field)
    figure = go.Figure()
    for row, percentile in enumerate(result.percentiles):
        figure.add_trace(
            go.Scatter(
                x=x,
                y=series[row, :].tolist(),
                mode="lines",
                name=f"{percentile}th",
            )
        )
    figure.update_layout(hovermode=_HOVERMODE, legend={"traceorder": "reversed"})
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
    figure.update_layout(hovermode=_HOVERMODE)
    return figure


def build_figure(result: SimulationResult, chart_type: str) -> dict:
    source_field = _BAND_SOURCE.get(chart_type)
    if source_field is not None:
        return _band_figure(result, source_field).to_plotly_json()
    if chart_type in _WEALTH_POSITION:
        return _wealth_composition_figure(result, chart_type).to_plotly_json()
    raise ValueError(f"unsupported chart type: {chart_type!r}")

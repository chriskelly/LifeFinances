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
    for chart_type in CHART_TYPES:
        if raw == chart_type:
            return chart_type
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

_WEALTH_INCOME_LAYERS = (
    ("Job", "wealth_job"),
    ("Social Security", "wealth_social_security"),
    ("Pension", "wealth_pension"),
    ("Manual", "wealth_manual"),
)

_WEALTH_STACKGROUP = "wealth"

# "x unified" matches on hovered x and shows every trace, so tooltips stay
# stable across the plot (unlike default "closest", which flips between lines).
_HOVERMODE = "x unified"

# d3-format via yaxis.hoverformat. Allocation is a 0–1 fraction (".1%" → one
# decimal percent). lock_percent_axis also pins range to PERCENT_Y_RANGE.
HOVERFORMAT_DOLLAR = "$,.0f"
HOVERFORMAT_PERCENT = ".1%"
TICKFORMAT_PERCENT = ".0%"
PERCENT_Y_RANGE = (0.0, 1.0)


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
    figure.update_layout(
        hovermode=_HOVERMODE,
        legend={"traceorder": "reversed"},
        yaxis=yaxis,
    )
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
    figure.update_layout(
        hovermode=_HOVERMODE,
        legend={"traceorder": "reversed"},
        yaxis={"hoverformat": HOVERFORMAT_DOLLAR},
    )
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
    raise ValueError(f"unsupported chart type: {chart_type!r}")

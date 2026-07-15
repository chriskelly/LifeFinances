from __future__ import annotations

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


def wealth_percentile_index(chart_type: str, num_percentiles: int) -> int:
    position = _WEALTH_POSITION.get(chart_type)
    if position is None:
        raise ValueError(f"not a wealth-composition chart: {chart_type!r}")
    if position == "low":
        return 0
    if position == "high":
        return num_percentiles - 1
    return num_percentiles // 2

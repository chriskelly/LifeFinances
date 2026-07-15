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

from __future__ import annotations

from core.timeline import add_months


def month_labels(start_month: tuple[int, int], horizon_months: int) -> list[str]:
    """One ``YYYY-MM`` label per simulated month, from ``start_month`` inclusive."""
    year, month = start_month
    labels: list[str] = []
    for index in range(horizon_months):
        label_year, label_month = add_months(year, month, index)
        labels.append(f"{label_year:04d}-{label_month:02d}")
    return labels

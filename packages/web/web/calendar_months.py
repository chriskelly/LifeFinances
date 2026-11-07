from __future__ import annotations

from core.timeline import add_months


def month_label(year: int, month: int) -> str:
    """``YYYY-MM`` label for one calendar month."""
    return f"{year:04d}-{month:02d}"


def month_labels(start_month: tuple[int, int], horizon_months: int) -> list[str]:
    """One ``YYYY-MM`` label per simulated month, from ``start_month`` inclusive."""
    year, month = start_month
    labels: list[str] = []
    for index in range(horizon_months):
        label_year, label_month = add_months(year, month, index)
        labels.append(month_label(label_year, label_month))
    return labels


def padded_month_range(
    start_month: tuple[int, int],
    horizon_months: int,
    *,
    pad_months: int,
) -> list[str]:
    """First-of-month labels bounding an axis padded past the first and last month.

    A non-positive horizon puts the last bound at ``start_month``.
    """
    year, month = start_month
    months = max(horizon_months, 0)
    first = add_months(year, month, -pad_months)
    last = add_months(year, month, months - 1 + pad_months)
    return [f"{month_label(*first)}-01", f"{month_label(*last)}-01"]

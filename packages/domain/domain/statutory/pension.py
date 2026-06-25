from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor

SOURCE_NOTES = {
    "calstrs_2_at_62": (
        "CalSTRS 2% at 62 age factors: https://www.calstrs.com/age-factor"
    ),
}

# CalSTRS 2% at 62 benefit (age) factors, keyed by age in months.
CALSTRS_2_AT_62_AGE_FACTORS: tuple[tuple[int, Decimal], ...] = (
    (55 * 12, Decimal("0.0116")),
    (56 * 12, Decimal("0.0128")),
    (57 * 12, Decimal("0.0140")),
    (58 * 12, Decimal("0.0152")),
    (59 * 12, Decimal("0.0164")),
    (60 * 12, Decimal("0.0176")),
    (61 * 12, Decimal("0.0188")),
    (62 * 12, Decimal("0.0200")),
    (63 * 12, Decimal("0.0213")),
    (64 * 12, Decimal("0.0227")),
    (65 * 12, Decimal("0.0240")),
)


def age_factors_from_statutory(
    rows: tuple[tuple[int, Decimal], ...],
) -> list[AgeFactor]:
    """Convert statutory (age_months, factor) rows to plan config models."""
    return [AgeFactor(age_months=age, factor=factor) for age, factor in rows]

from __future__ import annotations

import math
from decimal import Decimal

# Update procedure: once a year, verify each value below against its source URL,
# refresh any that changed, then set LAST_REVIEWED_YEAR to the current year.
# `is_statutory_data_stale` turns this into a soft CI reminder (see below).
LAST_REVIEWED_YEAR = 2026
STALENESS_GRACE_YEARS = 2

# Append-only historical records: each year's row is permanent. Add a new row
# each year; never edit prior rows.
SOURCE_NOTES = {
    "taxable_max": "SSA maximum taxable earnings (append-only history): https://www.ssa.gov/benefits/retirement/planner/maxtax.html",
    "awi_index": "SSA indexing factors (append-only history): https://www.ssa.gov/cgi-bin/awiFactors.cgi",
    "current_bend_points": "SSA bend points (single current set, replaced yearly): https://www.ssa.gov/oact/cola/bendpoints.html",
    "pia_rates": "SSA PIA formula (single current set): https://www.ssa.gov/oact/cola/piaformula.html",
}

SS_MAX_EARNINGS_BY_YEAR: tuple[tuple[int, Decimal], ...] = (
    (2002, Decimal("84900")),
    (2003, Decimal("87000")),
    (2004, Decimal("87900")),
    (2005, Decimal("90000")),
    (2006, Decimal("94200")),
    (2007, Decimal("97500")),
    (2008, Decimal("102000")),
    (2009, Decimal("106800")),
    (2010, Decimal("106800")),
    (2011, Decimal("106800")),
    (2012, Decimal("110100")),
    (2013, Decimal("113700")),
    (2014, Decimal("117000")),
    (2015, Decimal("118500")),
    (2016, Decimal("118500")),
    (2017, Decimal("127200")),
    (2018, Decimal("128400")),
    (2019, Decimal("132900")),
    (2020, Decimal("137700")),
    (2021, Decimal("142800")),
    (2022, Decimal("147000")),
    (2023, Decimal("160200")),
    (2024, Decimal("168600")),
    (2025, Decimal("176100")),
    (2026, Decimal("184500")),
)

AWI_INDEX_BY_YEAR: tuple[tuple[int, Decimal], ...] = (
    (2003, Decimal("1.9557287")),
    (2004, Decimal("1.8688502")),
    (2005, Decimal("1.8028823")),
    (2006, Decimal("1.7236577")),
    (2007, Decimal("1.6488308")),
    (2008, Decimal("1.6117539")),
    (2009, Decimal("1.6364325")),
    (2010, Decimal("1.5986484")),
    (2011, Decimal("1.5500792")),
    (2012, Decimal("1.5031428")),
    (2013, Decimal("1.4841731")),
    (2014, Decimal("1.4332965")),
    (2015, Decimal("1.3851081")),
    (2016, Decimal("1.3696311")),
    (2017, Decimal("1.3239129")),
    (2018, Decimal("1.2776063")),
    (2019, Decimal("1.2314568")),
    (2020, Decimal("1.1976178")),
    (2021, Decimal("1.0998221")),
    (2022, Decimal("1.0443086")),
    (2023, Decimal("1.0000000")),
    (2024, Decimal("1.0000000")),
)

# Single current sets, not historical records: replace these in place each year.
CURRENT_BEND_POINTS: tuple[Decimal, Decimal] = (Decimal("1286"), Decimal("7749"))
PIA_RATES: tuple[Decimal, Decimal, Decimal] = (
    Decimal("0.90"),
    Decimal("0.32"),
    Decimal("0.15"),
)


def is_statutory_data_stale(current_year: int) -> bool:
    """Whether statutory data is overdue for its annual review.

    Soft reminder: stale only once `current_year` reaches
    `LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS`, so a new calendar year alone
    does not break CI while values are still close enough (real-dollar bend
    points barely move year to year).
    """
    return current_year - LAST_REVIEWED_YEAR >= STALENESS_GRACE_YEARS


def log_linear_extrapolate(
    rows: tuple[tuple[int, Decimal], ...] | list[tuple[int, Decimal]],
    year: int,
) -> Decimal:
    """Estimate `value(year)` from `(year, value)` rows using log-linear fit."""
    if not rows:
        raise ValueError("cannot extrapolate an empty statutory table")
    for source_year, value in rows:
        if source_year == year:
            return value
    x_values = [float(source_year) for source_year, _ in rows]
    y_values = [math.log(float(value)) for _, value in rows]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    )
    denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
    if denominator == 0:
        return rows[0][1]
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return Decimal(str(math.exp(intercept + slope * float(year))))


def statutory_value_for_year(
    rows: tuple[tuple[int, Decimal], ...],
    year: int,
) -> Decimal:
    """Return exact statutory value when available, otherwise extrapolate."""
    return log_linear_extrapolate(rows, year)

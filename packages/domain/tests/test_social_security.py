from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from domain.statutory.social_security import (
    AWI_INDEX_BY_YEAR,
    CURRENT_BEND_POINTS,
    LAST_REVIEWED_YEAR,
    PIA_RATES,
    SS_MAX_EARNINGS_BY_YEAR,
    STALENESS_GRACE_YEARS,
    is_statutory_data_stale,
    log_linear_extrapolate,
    statutory_value_for_year,
)


def test_statutory_tables_sanity_checks() -> None:
    pinned_taxable_max = Decimal("176100")
    # Contract test: 2025 SSA taxable maximum is intentionally pinned as a sanity check.
    assert statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, 2025) == (
        pinned_taxable_max
    )
    assert all(isinstance(value, Decimal) for _, value in AWI_INDEX_BY_YEAR)
    assert CURRENT_BEND_POINTS[0] < CURRENT_BEND_POINTS[1]
    assert PIA_RATES[0] > PIA_RATES[1]
    assert PIA_RATES[1] > PIA_RATES[2]


def test_statutory_data_is_fresh_within_grace_window() -> None:
    last_fresh_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS - 1

    assert is_statutory_data_stale(last_fresh_year) is False


def test_statutory_data_is_stale_past_grace_window() -> None:
    first_stale_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS

    assert is_statutory_data_stale(first_stale_year) is True


def test_statutory_data_is_not_stale_today() -> None:
    # Intentional real-calendar reminder: when this fails, verify the SSA tables
    # against their source URLs, refresh any changed values, and bump
    # LAST_REVIEWED_YEAR.
    assert is_statutory_data_stale(date.today().year) is False, (
        "Social Security statutory data is overdue for review; "
        "verify against source URLs and bump LAST_REVIEWED_YEAR."
    )


def test_log_linear_extrapolate_extends_two_year_growth() -> None:
    first_year = 2000
    second_year = 2001
    first_value = Decimal("100")
    second_value = Decimal("121")
    requested_year = 2002
    source_rows = [(first_year, first_value), (second_year, second_value)]

    result = log_linear_extrapolate(source_rows, requested_year)

    expected = second_value * (second_value / first_value)
    assert float(result) == pytest.approx(float(expected), rel=0.0001)

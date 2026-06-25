from __future__ import annotations

from datetime import date
from decimal import Decimal

from domain.statutory.taxes import (
    FEDERAL_BRACKETS,
    FEDERAL_STANDARD_DEDUCTION,
    LAST_REVIEWED_YEAR,
    STALENESS_GRACE_YEARS,
    is_tax_data_stale,
)


def test_federal_brackets_cover_single_and_mfj() -> None:
    assert set(FEDERAL_BRACKETS) == {"single", "married_filing_jointly"}
    assert set(FEDERAL_STANDARD_DEDUCTION) == {"single", "married_filing_jointly"}
    # MFJ standard deduction is double the single deduction (contract sanity check).
    assert FEDERAL_STANDARD_DEDUCTION["married_filing_jointly"] == (
        FEDERAL_STANDARD_DEDUCTION["single"] * Decimal(2)
    )


def test_tax_data_is_fresh_within_grace_window() -> None:
    last_fresh_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS - 1

    assert is_tax_data_stale(last_fresh_year) is False


def test_tax_data_is_stale_past_grace_window() -> None:
    first_stale_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS

    assert is_tax_data_stale(first_stale_year) is True


def test_tax_data_is_not_stale_today() -> None:
    # Real-calendar reminder: when this fails, verify tax tables against source
    # URLs, refresh changed values, and bump LAST_REVIEWED_YEAR.
    assert is_tax_data_stale(date.today().year) is False, (
        "Tax statutory data is overdue for review; verify against source URLs "
        "and bump LAST_REVIEWED_YEAR."
    )

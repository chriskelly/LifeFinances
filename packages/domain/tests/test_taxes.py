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
from domain.taxes.brackets import annual_income_tax, progressive_tax


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


def test_progressive_tax_is_zero_below_first_bracket() -> None:
    brackets = FEDERAL_BRACKETS["single"]

    assert progressive_tax(brackets, Decimal("0")) == Decimal("0.00")
    assert progressive_tax(brackets, Decimal("-100")) == Decimal("0.00")


def test_progressive_tax_matches_marginal_bracket_formula() -> None:
    brackets = FEDERAL_BRACKETS["single"]
    income = Decimal("50_000")
    previous_cap = Decimal(0)
    expected = None
    for rate, cap, cumulative_prior in brackets:
        if income < cap:
            expected = (cumulative_prior + rate * (income - previous_cap)).quantize(
                Decimal("0.01")
            )
            break
        previous_cap = cap
    assert expected is not None, "income must fall within a defined bracket"

    assert progressive_tax(brackets, income) == expected


def test_annual_income_tax_applies_standard_deduction() -> None:
    filing = "single"
    brackets = FEDERAL_BRACKETS[filing]
    deduction = FEDERAL_STANDARD_DEDUCTION[filing]
    gross = Decimal("200_000")
    taxable = gross - deduction
    expected = progressive_tax(brackets, taxable)

    result = annual_income_tax(
        brackets=brackets, standard_deduction=deduction, annual_income=gross
    )

    assert result == expected

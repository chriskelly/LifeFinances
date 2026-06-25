from __future__ import annotations

from decimal import Decimal

from core.models import FilingStatus

# Update procedure: once a year verify each value below against its source URL,
# refresh any that changed, then set LAST_REVIEWED_YEAR to the current year.
LAST_REVIEWED_YEAR = 2026
STALENESS_GRACE_YEARS = 2

SOURCE_NOTES = {
    "federal": "IRS federal brackets + standard deduction (single current set): https://www.irs.gov/filing/federal-income-tax-rates-and-brackets",
    "california": "CA FTB brackets + standard deduction (single current set): https://www.ftb.ca.gov/file/personal/tax-calculator-tables-rates.asp",
    "new_york": "NY DTF brackets + standard deduction (single current set): https://www.tax.ny.gov/pit/file/tax-tables/",
    "fica": "SSA/IRS FICA rates: https://www.ssa.gov/oact/progdata/taxRates.html",
}

# Bracket = (rate, highest_dollar_at_rate, cumulative_prior_tax_in_dollars).
Bracket = tuple[Decimal, Decimal, Decimal]

_INF = Decimal("Infinity")

FEDERAL_STANDARD_DEDUCTION: dict[FilingStatus, Decimal] = {
    "single": Decimal("16_100"),
    "married_filing_jointly": Decimal("32_200"),
}

FEDERAL_BRACKETS: dict[FilingStatus, tuple[Bracket, ...]] = {
    "single": (
        (Decimal("0.10"), Decimal("11_925"), Decimal("0")),
        (Decimal("0.12"), Decimal("48_475"), Decimal("1_192.50")),
        (Decimal("0.22"), Decimal("103_350"), Decimal("5_578.50")),
        (Decimal("0.24"), Decimal("197_300"), Decimal("17_651")),
        (Decimal("0.32"), Decimal("250_525"), Decimal("40_199")),
        (Decimal("0.35"), Decimal("626_350"), Decimal("57_231")),
        (Decimal("0.37"), _INF, Decimal("188_769.75")),
    ),
    "married_filing_jointly": (
        (Decimal("0.10"), Decimal("23_850"), Decimal("0")),
        (Decimal("0.12"), Decimal("96_950"), Decimal("2_385")),
        (Decimal("0.22"), Decimal("206_700"), Decimal("11_157")),
        (Decimal("0.24"), Decimal("394_600"), Decimal("35_302")),
        (Decimal("0.32"), Decimal("501_050"), Decimal("80_398")),
        (Decimal("0.35"), Decimal("751_600"), Decimal("114_462")),
        (Decimal("0.37"), _INF, Decimal("202_154.50")),
    ),
}

STATE_STANDARD_DEDUCTION: dict[str, dict[FilingStatus, Decimal]] = {
    "California": {
        "single": Decimal("5_706"),
        "married_filing_jointly": Decimal("11_412"),
    },
    "New York": {
        "single": Decimal("8_000"),
        "married_filing_jointly": Decimal("16_050"),
    },
}

STATE_BRACKETS: dict[str, dict[FilingStatus, tuple[Bracket, ...]]] = {
    "California": {
        "single": (
            (Decimal("0.01"), Decimal("11_079"), Decimal("0")),
            (Decimal("0.02"), Decimal("26_264"), Decimal("110.79")),
            (Decimal("0.04"), Decimal("41_452"), Decimal("414.49")),
            (Decimal("0.06"), Decimal("57_542"), Decimal("1_022.01")),
            (Decimal("0.08"), Decimal("72_724"), Decimal("1_987.41")),
            (Decimal("0.093"), Decimal("371_479"), Decimal("3_201.97")),
            (Decimal("0.103"), Decimal("445_771"), Decimal("30_986.19")),
            (Decimal("0.113"), Decimal("742_953"), Decimal("38_638.26")),
            (Decimal("0.123"), _INF, Decimal("72_219.83")),
        ),
        "married_filing_jointly": (
            (Decimal("0.01"), Decimal("22_158"), Decimal("0")),
            (Decimal("0.02"), Decimal("52_528"), Decimal("221.58")),
            (Decimal("0.04"), Decimal("82_904"), Decimal("828.98")),
            (Decimal("0.06"), Decimal("115_084"), Decimal("2_044.02")),
            (Decimal("0.08"), Decimal("145_448"), Decimal("3_974.82")),
            (Decimal("0.093"), Decimal("742_958"), Decimal("6_403.94")),
            (Decimal("0.103"), Decimal("891_542"), Decimal("61_972.37")),
            (Decimal("0.113"), Decimal("1_485_906"), Decimal("77_276.52")),
            (Decimal("0.123"), _INF, Decimal("144_439.65")),
        ),
    },
    "New York": {
        "single": (
            (Decimal("0.04"), Decimal("8_501"), Decimal("0")),
            (Decimal("0.045"), Decimal("11_701"), Decimal("340.04")),
            (Decimal("0.0525"), Decimal("13_901"), Decimal("484.04")),
            (Decimal("0.0585"), Decimal("80_651"), Decimal("599.54")),
            (Decimal("0.0625"), Decimal("215_401"), Decimal("4_504.42")),
            (Decimal("0.0685"), Decimal("1_077_551"), Decimal("12_926.29")),
            (Decimal("0.0965"), Decimal("5_000_001"), Decimal("71_983.57")),
            (Decimal("0.103"), Decimal("25_000_001"), Decimal("450_499.99")),
            (Decimal("0.109"), _INF, Decimal("2_510_499.99")),
        ),
        "married_filing_jointly": (
            (Decimal("0.04"), Decimal("17_151"), Decimal("0")),
            (Decimal("0.045"), Decimal("23_601"), Decimal("686.04")),
            (Decimal("0.0525"), Decimal("27_901"), Decimal("976.29")),
            (Decimal("0.0585"), Decimal("161_551"), Decimal("1_202.04")),
            (Decimal("0.0625"), Decimal("323_201"), Decimal("9_020.57")),
            (Decimal("0.0685"), Decimal("2_155_351"), Decimal("19_123.69")),
            (Decimal("0.0965"), Decimal("5_000_001"), Decimal("144_625.97")),
            (Decimal("0.103"), Decimal("25_000_001"), Decimal("419_134.69")),
            (Decimal("0.109"), _INF, Decimal("2_479_134.69")),
        ),
    },
}

MEDICARE_TAX_RATE = Decimal("0.0145")
SOCIAL_SECURITY_TAX_RATE = Decimal("0.062")


def is_tax_data_stale(current_year: int) -> bool:
    """Soft annual-review reminder for the tax statutory tables."""
    return current_year - LAST_REVIEWED_YEAR >= STALENESS_GRACE_YEARS

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.social_security import AnnualEarnings
from domain.social_security.earnings import parse_social_security_statement_xml
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


def test_parse_social_security_statement_xml_extracts_fica_earnings() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0">
  <osss:EarningsRecord>
    <osss:Earnings startYear="2023" endYear="2023">
      <osss:FicaEarnings>160200</osss:FicaEarnings>
      <osss:MedicareEarnings>219491</osss:MedicareEarnings>
    </osss:Earnings>
    <osss:Earnings startYear="2025" endYear="2025">
      <osss:FicaEarnings>-1</osss:FicaEarnings>
      <osss:MedicareEarnings>-1</osss:MedicareEarnings>
    </osss:Earnings>
  </osss:EarningsRecord>
</osss:OnlineSocialSecurityStatementData>
"""
    expected = [AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))]
    earnings = parse_social_security_statement_xml(xml_text)
    assert earnings == expected


def test_parse_social_security_statement_xml_rejects_multi_year_rows() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0">
  <osss:EarningsRecord>
    <osss:Earnings startYear="2020" endYear="2021">
      <osss:FicaEarnings>1000</osss:FicaEarnings>
    </osss:Earnings>
  </osss:EarningsRecord>
</osss:OnlineSocialSecurityStatementData>
"""
    with pytest.raises(ValueError, match="multi-year"):
        parse_social_security_statement_xml(xml_text)


def test_parse_social_security_statement_xml_rejects_missing_record() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0" />
"""
    with pytest.raises(ValueError, match="EarningsRecord"):
        parse_social_security_statement_xml(xml_text)

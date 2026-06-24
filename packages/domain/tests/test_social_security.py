from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.social_security import FULL_RETIREMENT_AGE_MONTHS, AnnualEarnings
from core.timeline import Timeline
from domain.social_security.benefits import (
    calculate_aime,
    calculate_pia,
    claim_age_multiplier,
)
from domain.social_security.earnings import (
    group_monthly_earnings_by_year,
    indexed_annual_earnings,
    parse_social_security_statement_xml,
)
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


def test_calculate_aime_uses_highest_35_years_with_implicit_zeroes() -> None:
    earning_years = 10
    annual_earnings = [Decimal("42000")] * earning_years
    aime = calculate_aime(annual_earnings)
    expected = sum(annual_earnings) / Decimal(35 * 12)
    assert aime == expected


def test_calculate_pia_uses_standard_bend_point_formula() -> None:
    aime = Decimal("9000")
    pia = calculate_pia(aime)
    first_bend, second_bend = CURRENT_BEND_POINTS
    rate1, rate2, rate3 = PIA_RATES
    expected = (
        first_bend * rate1
        + (second_bend - first_bend) * rate2
        + (aime - second_bend) * rate3
    ).quantize(Decimal("0.01"))
    assert pia == expected


def test_claim_age_multiplier_uses_monthly_early_and_delayed_rules() -> None:
    fra_multiplier = Decimal("1")
    earliest_claim_age = 62 * 12
    delayed_claim_age = 70 * 12
    early = claim_age_multiplier(earliest_claim_age)
    fra = claim_age_multiplier(FULL_RETIREMENT_AGE_MONTHS)
    delayed = claim_age_multiplier(delayed_claim_age)
    first_36_months = Decimal(36) * Decimal(5) / Decimal(900)
    remaining_24_months = Decimal(24) * Decimal(5) / Decimal(1200)
    expected_early = Decimal("1") - first_36_months - remaining_24_months
    expected_delayed = Decimal("1") + Decimal(36) * Decimal(2) / Decimal(300)
    assert early == expected_early
    assert fra == fra_multiplier
    assert delayed == expected_delayed


def test_group_monthly_earnings_by_year_uses_timeline_calendar_months() -> None:
    plan = default_plan()
    timeline = Timeline(plan, today=date(2026, 11, 1))
    year1_month11 = Decimal("100")
    year1_month12 = Decimal("200")
    year2_month1 = Decimal("300")
    monthly = [year1_month11, year1_month12, year2_month1]
    grouped = group_monthly_earnings_by_year(monthly, timeline)
    assert grouped == {2026: year1_month11 + year1_month12, 2027: year2_month1}


def test_indexed_annual_earnings_indexes_history_but_not_future_real_income() -> None:
    historical_year = 2023
    historical_earning = Decimal("1000")
    future_year = 2026
    historical = [
        AnnualEarnings(year=historical_year, fica_earnings=historical_earning)
    ]
    future = {future_year: Decimal("2000")}
    earnings = indexed_annual_earnings(
        historical_earnings=historical,
        future_real_earnings_by_year=future,
        today_year=2026,
    )
    historical_index = statutory_value_for_year(AWI_INDEX_BY_YEAR, historical_year)
    expected_history = historical_earning * historical_index
    assert expected_history in earnings
    assert future[future_year] in earnings

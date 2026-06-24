from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.social_security import (
    FULL_RETIREMENT_AGE_MONTHS,
    AnnualEarnings,
    PersonSocialSecurityConfig,
)
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, PersonId
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection, PersonJobIncome, project_job_income
from domain.social_security import project_social_security
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


def _zero_job_income(horizon: int) -> JobIncomeProjection:
    zeroes = [Decimal("0.00")] * horizon
    person = PersonJobIncome(gross=zeroes, ss_covered_gross=zeroes, tax_deferred=zeroes)
    return JobIncomeProjection(
        person1=person,
        person2=person,
        total_gross=zeroes,
        total_ss_covered_gross=zeroes,
        total_tax_deferred=zeroes,
    )


def _ss_plan(
    *,
    person1_claim_age_months: int = FULL_RETIREMENT_AGE_MONTHS,
    person2_claim_age_months: int = FULL_RETIREMENT_AGE_MONTHS,
    trust_factor: Decimal = Decimal("1"),
) -> Plan:
    return Plan(
        name="SS Test Plan",
        household=Household(
            person1=PersonHousehold(
                birth_month=1,
                birth_year=1960,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=person1_claim_age_months,
                    earnings_record=[
                        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
                    ],
                ),
            ),
            person2=PersonHousehold(
                birth_month=1,
                birth_year=1962,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=person2_claim_age_months,
                ),
            ),
            social_security_trust_factor=trust_factor,
        ),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_project_social_security_returns_horizon_length_series() -> None:
    plan = _ss_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)

    projection = project_social_security(plan, timeline, job_income)

    assert len(projection.person1.max_benefit) == timeline.horizon_months
    assert len(projection.person2.max_benefit) == timeline.horizon_months
    assert len(projection.total) == timeline.horizon_months


def test_project_social_security_starts_own_benefit_at_claim_month() -> None:
    claim_age = 67 * 12
    plan = _ss_plan(person1_claim_age_months=claim_age)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)
    person_id: PersonId = "person1"
    claim_index = timeline.index_of(
        PersonAgeBoundary(person=person_id, age_months=claim_age)
    )

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person1.own_benefit[claim_index - 1] == Decimal("0.00")
    assert projection.person1.own_benefit[claim_index] > Decimal("0.00")


def test_spousal_alternative_starts_after_both_people_claim() -> None:
    person1_claim = 67 * 12
    person2_claim = 70 * 12
    plan = _ss_plan(
        person1_claim_age_months=person1_claim,
        person2_claim_age_months=person2_claim,
    )
    plan.household.person2.social_security.earnings_record = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)
    person1_claim_index = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=person1_claim)
    )
    person2_claim_index = timeline.index_of(
        PersonAgeBoundary(person="person2", age_months=person2_claim)
    )

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person1.spousal_alternative[person1_claim_index] == (
        Decimal("0.00")
    )
    assert projection.person1.spousal_alternative[person2_claim_index] > (
        Decimal("0.00")
    )


def test_spousal_top_up_is_max_benefit_minus_own_benefit() -> None:
    plan = _ss_plan()
    plan.household.person2.social_security.earnings_record = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)

    projection = project_social_security(plan, timeline, job_income)

    for own, max_benefit, top_up in zip(
        projection.person1.own_benefit,
        projection.person1.max_benefit,
        projection.person1.spousal_top_up,
        strict=True,
    ):
        assert top_up == max_benefit - own


def test_sabbatical_reduced_ss_covered_income_flows_into_projection() -> None:
    annual_income = Decimal("120000")
    claim_age_months = 67 * 12
    break_start = CalendarMonthBoundary(year=2026, month=1)
    break_end = CalendarMonthBoundary(year=2026, month=12)
    person_with_break = PersonHousehold(
        birth_month=1,
        birth_year=1990,
        social_security=PersonSocialSecurityConfig(claim_age_months=claim_age_months),
        jobs=[
            Job(
                annual_income=annual_income,
                social_security_eligible=True,
                sabbaticals=[
                    SabbaticalWindow(
                        start=break_start,
                        end=break_end,
                        remaining_fraction=Decimal("0"),
                    )
                ],
            )
        ],
    )
    person_without_break = PersonHousehold(
        birth_month=1,
        birth_year=1990,
        social_security=PersonSocialSecurityConfig(claim_age_months=claim_age_months),
        jobs=[Job(annual_income=annual_income, social_security_eligible=True)],
    )
    base = default_plan()
    plan_with_break = Plan(
        name="SS Sabbatical",
        household=Household(person1=person_with_break, person2=base.household.person2),
        portfolio=base.portfolio,
    )
    plan_without_break = Plan(
        name="SS No Sabbatical",
        household=Household(
            person1=person_without_break, person2=base.household.person2
        ),
        portfolio=base.portfolio,
    )
    timeline_with_break = Timeline(plan_with_break, today=date(2026, 1, 1))
    timeline_without_break = Timeline(plan_without_break, today=date(2026, 1, 1))

    projection_with_break = project_social_security(
        plan_with_break,
        timeline_with_break,
        project_job_income(plan_with_break, timeline_with_break),
    )
    projection_without_break = project_social_security(
        plan_without_break,
        timeline_without_break,
        project_job_income(plan_without_break, timeline_without_break),
    )

    claim_index = timeline_with_break.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age_months)
    )
    assert (
        projection_with_break.person1.own_benefit[claim_index]
        < (projection_without_break.person1.own_benefit[claim_index])
    )


def test_household_trust_factor_scales_projected_benefits() -> None:
    full_trust = Decimal("1")
    reduced_trust = Decimal("0.75")
    full_plan = _ss_plan(trust_factor=full_trust)
    reduced_plan = _ss_plan(trust_factor=reduced_trust)
    full_timeline = Timeline(full_plan, today=date(2026, 1, 1))
    reduced_timeline = Timeline(reduced_plan, today=date(2026, 1, 1))
    full_projection = project_social_security(
        full_plan, full_timeline, _zero_job_income(full_timeline.horizon_months)
    )
    reduced_projection = project_social_security(
        reduced_plan,
        reduced_timeline,
        _zero_job_income(reduced_timeline.horizon_months),
    )
    claim_index = full_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=67 * 12)
    )

    assert reduced_projection.person1.max_benefit[claim_index] == (
        full_projection.person1.max_benefit[claim_index] * reduced_trust
    ).quantize(Decimal("0.01"))

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.models import FilingStatus, Household, Plan
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection, PersonJobIncome
from domain.pension import PensionProjection
from domain.social_security import PersonSocialSecurity, SocialSecurityProjection
from domain.statutory.social_security import (
    SS_MAX_EARNINGS_BY_YEAR,
    statutory_value_for_year,
)
from domain.statutory.taxes import (
    FEDERAL_BRACKETS,
    FEDERAL_STANDARD_DEDUCTION,
    LAST_REVIEWED_YEAR,
    MEDICARE_TAX_RATE,
    SOCIAL_SECURITY_TAX_RATE,
    STALENESS_GRACE_YEARS,
    is_tax_data_stale,
)
from domain.taxes import TaxBreakdown, compute_taxes
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


def _zeros(n: int) -> list[Decimal]:
    return [Decimal("0.00")] * n


def _job_income(
    *,
    horizon: int,
    person1_gross: list[Decimal],
    person1_deferred: list[Decimal] | None = None,
    person1_ss_covered: list[Decimal] | None = None,
) -> JobIncomeProjection:
    deferred = person1_deferred if person1_deferred is not None else _zeros(horizon)
    # SS-covered wages default to zero; pass person1_ss_covered only for FICA SS tests.
    ss_covered = (
        person1_ss_covered if person1_ss_covered is not None else _zeros(horizon)
    )
    person1 = PersonJobIncome(
        gross=person1_gross, ss_covered_gross=ss_covered, tax_deferred=deferred
    )
    person2 = PersonJobIncome(
        gross=_zeros(horizon),
        ss_covered_gross=_zeros(horizon),
        tax_deferred=_zeros(horizon),
    )
    return JobIncomeProjection(
        person1=person1,
        person2=person2,
        total_gross=person1_gross,
        total_ss_covered_gross=ss_covered,
        total_tax_deferred=deferred,
    )


def _zero_ss(horizon: int) -> SocialSecurityProjection:
    person = PersonSocialSecurity(
        own_benefit=_zeros(horizon),
        spousal_alternative=_zeros(horizon),
        max_benefit=_zeros(horizon),
    )
    return SocialSecurityProjection(
        person1=person, person2=person, total=_zeros(horizon)
    )


def _zero_pension(horizon: int) -> PensionProjection:
    zeroes = _zeros(horizon)
    return PensionProjection(formula=zeroes, manual=zeroes, stored_total=zeroes)


def _plan(
    *,
    filing_status: FilingStatus = "married_filing_jointly",
    residence_state: str | None = None,
) -> Plan:
    base = default_plan()
    return Plan(
        name="Tax Test",
        household=Household(
            person1=base.household.person1,
            person2=base.household.person2,
            filing_status=filing_status,
            residence_state=residence_state,
        ),
        portfolio=base.portfolio,
    )


def test_taxes_are_negative_outflows() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    monthly_gross = Decimal("10_000.00")
    job_income = _job_income(horizon=horizon, person1_gross=[monthly_gross] * horizon)

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    assert isinstance(breakdown, TaxBreakdown)
    assert breakdown.federal_income[0] < Decimal("0")
    assert breakdown.fica_medicare[0] < Decimal("0")
    assert all(t <= Decimal("0") for t in breakdown.stored_total)


def test_annual_federal_tax_uses_year_total_not_per_month_annualized() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    # All of year 1's income lands in the first 3 months (e.g. a job ending in March).
    gross = _zeros(horizon)
    monthly = Decimal("40_000.00")
    for month in range(3):
        gross[month] = monthly
    job_income = _job_income(horizon=horizon, person1_gross=gross)
    year_total = monthly * Decimal(3)
    fed_brackets = FEDERAL_BRACKETS["married_filing_jointly"]
    fed_deduction = FEDERAL_STANDARD_DEDUCTION["married_filing_jointly"]
    expected_year_fed = annual_income_tax(
        brackets=fed_brackets,
        standard_deduction=fed_deduction,
        annual_income=year_total,
    )

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    year1_fed = -sum(breakdown.federal_income[0:12], Decimal("0"))
    # Allow sub-cent distribution rounding across the 3 funded months.
    assert abs(year1_fed - expected_year_fed) <= Decimal("0.03")


def test_federal_tax_distributed_proportional_to_monthly_taxable() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    gross = _zeros(horizon)
    gross[0] = Decimal("30_000.00")
    gross[1] = Decimal("10_000.00")
    job_income = _job_income(horizon=horizon, person1_gross=gross)

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    # Month 0 has 3x the taxable income of month 1, so it carries ~3x the tax.
    assert breakdown.federal_income[0] == (
        breakdown.federal_income[1] * Decimal(3)
    ).quantize(Decimal("0.01"))


def test_filing_status_changes_federal_tax() -> None:
    timeline_today = date(2026, 1, 1)
    monthly_gross = Decimal("12_000.00")
    single_plan = _plan(filing_status="single")
    mfj_plan = _plan(filing_status="married_filing_jointly")
    single_timeline = Timeline(single_plan, today=timeline_today)
    mfj_timeline = Timeline(mfj_plan, today=timeline_today)
    horizon = single_timeline.horizon_months
    job_income = _job_income(horizon=horizon, person1_gross=[monthly_gross] * horizon)

    single = compute_taxes(
        plan=single_plan,
        timeline=single_timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )
    mfj = compute_taxes(
        plan=mfj_plan,
        timeline=mfj_timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    # MFJ brackets are wider, so the same income owes less federal tax.
    assert mfj.federal_income[0] > single.federal_income[0]


def test_ss_pension_taxable_fraction_scales_taxable_benefits() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    monthly_pension = Decimal("5_000.00")
    pension = PensionProjection(
        formula=[monthly_pension] * horizon,
        manual=_zeros(horizon),
        stored_total=[monthly_pension] * horizon,
    )
    job_income = _job_income(horizon=horizon, person1_gross=_zeros(horizon))

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=pension,
    )

    # Pension income is partially included, so it produces some federal tax.
    assert breakdown.federal_income[0] < Decimal("0")


def test_fica_medicare_is_flat_rate_on_gross() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    monthly_gross = Decimal("10_000.00")
    job_income = _job_income(horizon=horizon, person1_gross=[monthly_gross] * horizon)
    expected = -(MEDICARE_TAX_RATE * monthly_gross).quantize(Decimal("0.01"))

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    assert breakdown.fica_medicare[0] == expected


def test_fica_social_security_caps_at_annual_wage_base() -> None:
    plan = _plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    monthly_gross = Decimal("300_000.00")  # 3.6M/yr exceeds the wage base
    job_income = _job_income(
        horizon=horizon,
        person1_gross=[monthly_gross] * horizon,
        person1_ss_covered=[monthly_gross] * horizon,
    )
    wage_base = statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, timeline.today.year)
    expected_year_one = -(SOCIAL_SECURITY_TAX_RATE * wage_base).quantize(
        Decimal("0.01")
    )

    breakdown = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    year_one_ss = sum(breakdown.fica_social_security[0:12], Decimal("0"))
    assert abs(year_one_ss - expected_year_one) <= Decimal("0.01")


def test_no_state_when_residence_state_unknown_or_none() -> None:
    plan = _plan(residence_state=None)
    ca_plan = _plan(residence_state="California")
    timeline = Timeline(plan, today=date(2026, 1, 1))
    ca_timeline = Timeline(ca_plan, today=date(2026, 1, 1))
    horizon = timeline.horizon_months
    monthly_gross = Decimal("10_000.00")
    job_income = _job_income(horizon=horizon, person1_gross=[monthly_gross] * horizon)

    no_state = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )
    california = compute_taxes(
        plan=ca_plan,
        timeline=ca_timeline,
        job_income=job_income,
        social_security=_zero_ss(horizon),
        pension=_zero_pension(horizon),
    )

    assert all(s == Decimal("0.00") for s in no_state.state_income)
    assert california.state_income[0] < Decimal("0")

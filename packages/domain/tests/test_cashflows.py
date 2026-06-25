from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline

from domain import MonthlyCashflows, build_monthly_cashflows


def _working_plan() -> Plan:
    base = default_plan()
    job = Job(
        annual_income=Decimal("120_000"),
        end=CalendarMonthBoundary(year=2045, month=12),
    )
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1983,
        jobs=[job],
        social_security=base.household.person1.social_security,
    )
    return Plan(
        name="Cashflow Test",
        household=Household(person1=person1, person2=base.household.person2),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_all_series_have_horizon_length() -> None:
    plan = _working_plan()
    today = date(2026, 1, 1)
    horizon = Timeline(plan, today=today).horizon_months

    cashflows = build_monthly_cashflows(plan, today=today)

    assert isinstance(cashflows, MonthlyCashflows)
    assert len(cashflows.gross_job) == horizon
    assert len(cashflows.gross_social_security) == horizon
    assert len(cashflows.gross_pension) == horizon
    assert len(cashflows.gross_manual) == horizon
    assert len(cashflows.total_gross) == horizon
    assert len(cashflows.net_cashflow) == horizon
    assert len(cashflows.taxes.stored_total) == horizon


def test_net_cashflow_is_total_gross_plus_negative_taxes() -> None:
    plan = _working_plan()
    today = date(2026, 1, 1)

    cashflows = build_monthly_cashflows(plan, today=today)

    for month in range(len(cashflows.net_cashflow)):
        expected = cashflows.total_gross[month] + cashflows.taxes.stored_total[month]
        assert cashflows.net_cashflow[month] == expected


def test_total_gross_sums_all_income_components() -> None:
    plan = _working_plan()
    today = date(2026, 1, 1)

    cashflows = build_monthly_cashflows(plan, today=today)

    for month in range(len(cashflows.total_gross)):
        expected = (
            cashflows.gross_job[month]
            + cashflows.gross_social_security[month]
            + cashflows.gross_pension[month]
            + cashflows.gross_manual[month]
        )
        assert cashflows.total_gross[month] == expected


def test_manual_income_stream_appears_in_gross_manual() -> None:
    plan = _working_plan()
    monthly_amount = Decimal("2_000.00")
    plan.manual_income_streams = [
        TimedStream(label="rental", monthly_amount=monthly_amount)
    ]
    today = date(2026, 1, 1)

    cashflows = build_monthly_cashflows(plan, today=today)

    assert cashflows.gross_manual[0] == monthly_amount


def test_sabbatical_reduced_income_lowers_taxes() -> None:
    today = date(2026, 1, 1)
    career_end = CalendarMonthBoundary(year=2045, month=12)
    break_start = CalendarMonthBoundary(year=2027, month=1)
    break_end = CalendarMonthBoundary(year=2027, month=12)
    base = default_plan()

    def plan_with(job: Job) -> Plan:
        person1 = PersonHousehold(birth_month=1, birth_year=1983, jobs=[job])
        return Plan(
            name="Sabbatical Cashflow",
            household=Household(person1=person1, person2=base.household.person2),
            portfolio=Portfolio(current_savings_balance=Decimal("0")),
        )

    no_break = plan_with(Job(annual_income=Decimal("120_000"), end=career_end))
    with_break = plan_with(
        Job(
            annual_income=Decimal("120_000"),
            end=career_end,
            sabbaticals=[
                SabbaticalWindow(
                    start=break_start,
                    end=break_end,
                    remaining_fraction=Decimal("0"),
                )
            ],
        )
    )

    no_break_cashflows = build_monthly_cashflows(no_break, today=today)
    with_break_cashflows = build_monthly_cashflows(with_break, today=today)

    # During the sabbatical year the lower taxable income means lower (less negative) tax.
    sabbatical_month = Timeline(with_break, today=today).index_of(break_start)
    assert (
        with_break_cashflows.taxes.stored_total[sabbatical_month]
        > (no_break_cashflows.taxes.stored_total[sabbatical_month])
    )

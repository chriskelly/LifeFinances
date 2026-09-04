"""Helpers for tools/disability_insurance.py (plain Python, not a Marimo notebook)."""

from __future__ import annotations

import tomllib
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from core.models import PersonHousehold, Plan
from core.streams import PersonAgeBoundary, PersonId
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection, PersonJobIncome

from domain import MonthlyCashflows, build_monthly_cashflows

LOCAL_CONFIG_PATH = Path("tools/disability_insurance.local.toml")


def optional_int(table: object, key: str) -> int | None:
    if not isinstance(table, dict) or key not in table:
        return None
    value = table[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def person_from_table(raw: object) -> tuple[Decimal, int | None, int | None]:
    if raw is None:
        return Decimal(0), None, None
    if not isinstance(raw, dict):
        raise ValueError("person1/person2 must be TOML tables")
    percentage_raw = raw.get("percentage", 0)
    if isinstance(percentage_raw, bool) or not isinstance(percentage_raw, (int, float)):
        raise ValueError("percentage must be a number")
    return (
        Decimal(str(percentage_raw)),
        optional_int(raw, "duration_years"),
        optional_int(raw, "age_limit"),
    )


def validate_coverage(
    *,
    percentage: Decimal,
    duration_years: int | None,
    age_limit: int | None,
    label: str,
) -> None:
    if percentage < 0:
        raise ValueError(f"{label}: percentage must be >= 0")
    has_duration = duration_years is not None
    has_age = age_limit is not None
    if has_duration and has_age:
        raise ValueError(f"{label}: set only one of duration_years or age_limit")
    if percentage > 0:
        if not has_duration and not has_age:
            raise ValueError(
                f"{label}: when percentage > 0, set duration_years or age_limit"
            )
        if has_duration and duration_years is not None and duration_years <= 0:
            raise ValueError(f"{label}: duration_years must be positive")
        if has_age and age_limit is not None and age_limit <= 0:
            raise ValueError(f"{label}: age_limit must be positive")
    elif has_duration or has_age:
        raise ValueError(
            f"{label}: when percentage is 0, omit duration_years and age_limit"
        )


def load_local_config() -> tuple[
    str,
    int | None,
    Decimal,
    int | None,
    int | None,
    Decimal,
    int | None,
    int | None,
]:
    """Return source, plan_id, and person1/person2 coverage fields.

    Validates person1 only. Validate person2 after the plan loads when a partner exists.
    """
    data: dict = {}
    config_source = "defaults (file not found)"
    if LOCAL_CONFIG_PATH.exists():
        text = LOCAL_CONFIG_PATH.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        if not isinstance(data, dict):
            raise ValueError(f"`{LOCAL_CONFIG_PATH}` must be a TOML table.")
        config_source = str(LOCAL_CONFIG_PATH)

    plan_id = optional_int(data, "plan_id")
    p1_pct, p1_dur, p1_age = person_from_table(data.get("person1"))
    p2_pct, p2_dur, p2_age = person_from_table(data.get("person2"))
    validate_coverage(
        percentage=p1_pct,
        duration_years=p1_dur,
        age_limit=p1_age,
        label="person1",
    )
    return (
        config_source,
        plan_id,
        p1_pct,
        p1_dur,
        p1_age,
        p2_pct,
        p2_dur,
        p2_age,
    )


def fmt_money(amount: Decimal) -> str:
    return f"${float(amount):,.0f}"


def person_job(jobs: JobIncomeProjection, person_id: PersonId) -> PersonJobIncome:
    if person_id == "person1":
        return jobs.person1
    if jobs.person2 is None:
        raise ValueError("person2 is not on this plan")
    return jobs.person2


def series_all_zero(values: list[Decimal]) -> bool:
    return all(value == 0 for value in values)


def first_positive_annual_income(gross: list[Decimal]) -> Decimal | None:
    for monthly in gross:
        if monthly > 0:
            return monthly * Decimal(12)
    return None


def covered_month_count(
    *,
    timeline: Timeline,
    person_id: PersonId,
    duration_years: int | None,
    age_limit: int | None,
) -> int:
    horizon = timeline.horizon_months
    if duration_years is not None:
        raw = duration_years * 12
        return max(0, min(raw, horizon))
    if age_limit is None:
        return 0
    end_exclusive = timeline.index_of(
        PersonAgeBoundary(person=person_id, age_months=age_limit * 12)
    )
    return max(0, min(end_exclusive, horizon))


def average_tax_rate(baseline: MonthlyCashflows) -> Decimal:
    job = baseline.gross_job
    taxes = baseline.taxes
    job_sum = Decimal(0)
    tax_sum = Decimal(0)
    for month, job_amount in enumerate(job):
        if job_amount > 0:
            job_sum += job_amount
            tax_sum += (
                taxes.federal_income[month]
                + taxes.state_income[month]
                + taxes.fica_medicare[month]
            )
    if job_sum == 0:
        return Decimal(0)
    return -tax_sum / job_sum


def employer_replacement(
    *,
    percentage: Decimal,
    current_annual_income: Decimal,
    covered_months: int,
    avg_tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    if percentage == 0 or current_annual_income <= 0 or covered_months == 0:
        zero = Decimal(0)
        return zero, zero, zero
    capped = min(percentage, Decimal(100))
    pct = capped / Decimal(100)
    monthly = current_annual_income / Decimal(12)
    gross_benefits = monthly * pct * Decimal(covered_months)
    tax_on_benefits = gross_benefits * avg_tax_rate
    net_replacement = gross_benefits - tax_on_benefits
    return gross_benefits, tax_on_benefits, net_replacement


def sum_series(values: list[Decimal]) -> Decimal:
    total = Decimal(0)
    for value in values:
        total += value
    return total


def disable_person(plan: Plan, person_id: PersonId) -> Plan:
    clone = plan.model_copy(deep=True)
    if person_id == "person1":
        clone.household.person1.jobs = []
        return clone
    if clone.household.person2 is None:
        raise ValueError("person2 is not on this plan")
    clone.household.person2.jobs = []
    return clone


def report_person(
    *,
    label: str,
    person_id: PersonId,
    person: PersonHousehold,
    plan: Plan,
    baseline: MonthlyCashflows,
    jobs: JobIncomeProjection,
    timeline: Timeline,
    percentage: Decimal,
    duration_years: int | None,
    age_limit: int | None,
) -> str:
    _ = person
    person_gross = person_job(jobs, person_id).gross
    if series_all_zero(person_gross):
        return f"## {label}\n\nNo future job income — disability insurance is not needed.\n"
    disabled_plan = disable_person(plan, person_id)
    disability = build_monthly_cashflows(disabled_plan)
    need = sum_series(baseline.net_cashflow) - sum_series(disability.net_cashflow)
    job_delta = sum_series(baseline.gross_job) - sum_series(disability.gross_job)
    ss_delta = sum_series(baseline.gross_social_security) - sum_series(
        disability.gross_social_security
    )
    pension_delta = (
        sum_series(baseline.gross_pension)
        + sum_series(baseline.gross_manual)
        - sum_series(disability.gross_pension)
        - sum_series(disability.gross_manual)
    )
    current_annual = first_positive_annual_income(person_gross)
    assert current_annual is not None
    covered = covered_month_count(
        timeline=timeline,
        person_id=person_id,
        duration_years=duration_years,
        age_limit=age_limit,
    )
    years = Decimal(covered) / Decimal(12)
    avg_rate = average_tax_rate(baseline)
    gross_b, tax_b, net_b = employer_replacement(
        percentage=percentage,
        current_annual_income=current_annual,
        covered_months=covered,
        avg_tax_rate=avg_rate,
    )
    gap = max(Decimal(0), need - net_b)
    lines = [
        f"## {label}",
        "",
        f"1. **Total income replacement needed:** {fmt_money(need)}",
        f"   - Baseline post-tax lifetime: {fmt_money(sum_series(baseline.net_cashflow))}",
        f"   - Disability post-tax lifetime: {fmt_money(sum_series(disability.net_cashflow))}",
        f"   - Job (gross) delta: {fmt_money(job_delta)}",
        f"   - Social Security (gross) delta: {fmt_money(ss_delta)}",
        f"   - Pension + manual (gross) delta: {fmt_money(pension_delta)}",
        "   - Includes SS/pension changes after the employer policy window.",
        "",
        f"2. **Existing coverage replacement (after taxes):** {fmt_money(net_b)}",
        "   - Workplace disability benefits treated as taxable ordinary income.",
        f"   - Gross benefits: {fmt_money(gross_b)}; tax on benefits: {fmt_money(tax_b)}",
    ]
    if percentage > 100:
        lines.append(
            "   - Entered percentage exceeds 100%; replacement capped at 100%."
        )
    lines.extend(["", f"3. **Remaining coverage gap:** {fmt_money(gap)}"])
    if covered == 0 and percentage > 0:
        lines.append("   - Coverage window is empty; no % of income recommendation.")
    elif gap == 0:
        lines.append("   - No additional coverage is needed.")
    elif years > 0 and current_annual > 0:
        benefit_percent = (gap / years) / current_annual * Decimal(100)
        rounded = benefit_percent.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        lines.append(
            f"   - Recommended: **{rounded}% of income for {float(years):g} years** "
            "(same window as employer benefits)."
        )
    return "\n".join(lines)

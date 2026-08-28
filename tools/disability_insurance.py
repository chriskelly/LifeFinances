import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    from decimal import ROUND_HALF_UP, Decimal

    import marimo as mo
    from core.models import PersonHousehold, Plan
    from core.repository import PlanRepository
    from core.settings_repository import SettingsRepository
    from core.streams import PersonAgeBoundary, PersonId
    from core.timeline import Timeline
    from domain.job_income import (
        JobIncomeProjection,
        PersonJobIncome,
        project_job_income,
    )

    from domain import MonthlyCashflows, build_monthly_cashflows

    plan_repo = PlanRepository()
    settings_repo = SettingsRepository()
    return (
        Decimal,
        JobIncomeProjection,
        MonthlyCashflows,
        PersonAgeBoundary,
        PersonHousehold,
        PersonId,
        PersonJobIncome,
        Plan,
        PlanRepository,
        ROUND_HALF_UP,
        SettingsRepository,
        Timeline,
        build_monthly_cashflows,
        mo,
        plan_repo,
        project_job_income,
        settings_repo,
    )


@app.cell
def _(mo, plan_repo):
    db_path = plan_repo.db_path
    missing_db = not db_path.exists()
    mo.stop(
        missing_db,
        mo.md(
            f"Database not found at `{db_path}`. "
            "Run `uv run python scripts/init_db.py` and/or open the web app."
        ),
    )
    summaries = plan_repo.list()
    mo.stop(
        len(summaries) == 0,
        mo.md(
            "No plans in the database. "
            "Run `uv run python scripts/init_db.py` and/or open the web app."
        ),
    )
    lines = "\n".join(f"- `{row.id}`: {row.name}" for row in summaries)
    mo.md(f"**Plans**\n\n{lines}")
    return (summaries,)


@app.cell
def _(mo, plan_repo, settings_repo, summaries):
    # Edit this. None → AppSettings.default_plan_id (same as GET /).
    PLAN_ID: int | None = None

    valid_ids = {row.id for row in summaries}
    chosen_id = PLAN_ID if PLAN_ID is not None else settings_repo.get().default_plan_id
    mo.stop(
        chosen_id is None or chosen_id not in valid_ids,
        mo.md(
            "Set `PLAN_ID` to an id from the list above "
            "(default plan is missing or invalid)."
        ),
    )
    plan = plan_repo.get_by_id(chosen_id)
    mo.stop(
        plan is None,
        mo.md(
            f"Plan `{chosen_id}` could not be loaded. Pick another id from the list."
        ),
    )
    mo.md(f"Using plan **{plan.name}** (`id={chosen_id}`).")
    return PLAN_ID, chosen_id, plan


@app.cell
def _(Decimal, mo):
    def validate_coverage(
        *,
        percentage: Decimal,
        duration_years: int | None,
        age_limit: int | None,
        label: str,
    ) -> None:
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
        elif has_duration or has_age:
            raise ValueError(
                f"{label}: when percentage is 0, omit duration_years and age_limit"
            )

    # 60 means 60%. Partner block is ignored when the plan has no person2.
    PERSON1_PERCENTAGE = Decimal("0")
    PERSON1_DURATION_YEARS: int | None = None
    PERSON1_AGE_LIMIT: int | None = None
    PERSON2_PERCENTAGE = Decimal("0")
    PERSON2_DURATION_YEARS: int | None = None
    PERSON2_AGE_LIMIT: int | None = None

    validate_coverage(
        percentage=PERSON1_PERCENTAGE,
        duration_years=PERSON1_DURATION_YEARS,
        age_limit=PERSON1_AGE_LIMIT,
        label="person1",
    )
    validate_coverage(
        percentage=PERSON2_PERCENTAGE,
        duration_years=PERSON2_DURATION_YEARS,
        age_limit=PERSON2_AGE_LIMIT,
        label="person2",
    )
    mo.md("Coverage literals validated (not saved to the plan).")
    return (
        PERSON1_AGE_LIMIT,
        PERSON1_DURATION_YEARS,
        PERSON1_PERCENTAGE,
        PERSON2_AGE_LIMIT,
        PERSON2_DURATION_YEARS,
        PERSON2_PERCENTAGE,
    )


@app.cell
def _(  # noqa: C901
    Decimal,
    JobIncomeProjection,
    MonthlyCashflows,
    PersonAgeBoundary,
    PersonHousehold,
    PersonId,
    PersonJobIncome,
    Plan,
    ROUND_HALF_UP,
    Timeline,
    build_monthly_cashflows,
    project_job_income,
):
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
            lines.append(
                "   - Coverage window is empty; no % of income recommendation."
            )
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

    return (
        disable_person,
        report_person,
        series_all_zero,
        sum_series,
    )


@app.cell
def _(
    build_monthly_cashflows,
    mo,
    plan,
    project_job_income,
    series_all_zero,
    Timeline,
):
    timeline = Timeline(plan)
    baseline = build_monthly_cashflows(plan)
    jobs = project_job_income(plan, timeline)
    household_no_jobs = series_all_zero(jobs.person1.gross) and (
        jobs.person2 is None or series_all_zero(jobs.person2.gross)
    )
    mo.stop(
        household_no_jobs,
        mo.md(
            "Neither person has future job income — disability insurance is not needed."
        ),
    )
    return baseline, jobs, timeline


@app.cell
def _(
    PERSON1_AGE_LIMIT,
    PERSON1_DURATION_YEARS,
    PERSON1_PERCENTAGE,
    baseline,
    jobs,
    mo,
    plan,
    report_person,
    timeline,
):
    person1_md = report_person(
        label="Person 1",
        person_id="person1",
        person=plan.household.person1,
        plan=plan,
        baseline=baseline,
        jobs=jobs,
        timeline=timeline,
        percentage=PERSON1_PERCENTAGE,
        duration_years=PERSON1_DURATION_YEARS,
        age_limit=PERSON1_AGE_LIMIT,
    )
    mo.md(person1_md)
    return


@app.cell
def _(
    PERSON2_AGE_LIMIT,
    PERSON2_DURATION_YEARS,
    PERSON2_PERCENTAGE,
    baseline,
    jobs,
    mo,
    plan,
    report_person,
    timeline,
):
    partner = plan.household.person2
    if partner is not None:
        person2_md = report_person(
            label="Person 2",
            person_id="person2",
            person=partner,
            plan=plan,
            baseline=baseline,
            jobs=jobs,
            timeline=timeline,
            percentage=PERSON2_PERCENTAGE,
            duration_years=PERSON2_DURATION_YEARS,
            age_limit=PERSON2_AGE_LIMIT,
        )
        person2_out = mo.md(person2_md)
    else:
        person2_out = None
    return person2_out


if __name__ == "__main__":
    app.run()

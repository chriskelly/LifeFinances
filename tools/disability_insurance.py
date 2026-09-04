import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import tomllib
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    import marimo as mo
    from core.repository import PlanRepository
    from core.settings_repository import SettingsRepository
    from core.timeline import Timeline
    from domain.job_income import project_job_income

    from domain import build_monthly_cashflows

    helpers_path = Path("tools/disability_insurance_helpers.py")
    helpers_spec = spec_from_file_location(
        "disability_insurance_helpers",
        helpers_path,
    )
    assert helpers_spec is not None and helpers_spec.loader is not None
    helpers = module_from_spec(helpers_spec)
    helpers_spec.loader.exec_module(helpers)

    plan_repo = PlanRepository()
    settings_repo = SettingsRepository()
    return (
        Timeline,
        build_monthly_cashflows,
        helpers,
        mo,
        plan_repo,
        project_job_income,
        settings_repo,
        tomllib,
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
def _(helpers, mo, tomllib):
    try:
        (
            config_source,
            PLAN_ID,
            PERSON1_PERCENTAGE,
            PERSON1_DURATION_YEARS,
            PERSON1_AGE_LIMIT,
            PERSON2_PERCENTAGE,
            PERSON2_DURATION_YEARS,
            PERSON2_AGE_LIMIT,
        ) = helpers.load_local_config()
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError, ValueError) as exc:
        mo.stop(
            True,
            mo.md(f"Config error (`{helpers.LOCAL_CONFIG_PATH}`): {exc}"),
        )

    mo.md(
        f"Config: `{config_source}`. "
        f"plan_id={PLAN_ID!s}. "
        f"person1 {PERSON1_PERCENTAGE}% "
        f"(duration_years={PERSON1_DURATION_YEARS!s}, age_limit={PERSON1_AGE_LIMIT!s}); "
        f"person2 {PERSON2_PERCENTAGE}% "
        f"(duration_years={PERSON2_DURATION_YEARS!s}, age_limit={PERSON2_AGE_LIMIT!s}). "
        "Not saved to the plan."
    )
    return (
        PLAN_ID,
        PERSON1_AGE_LIMIT,
        PERSON1_DURATION_YEARS,
        PERSON1_PERCENTAGE,
        PERSON2_AGE_LIMIT,
        PERSON2_DURATION_YEARS,
        PERSON2_PERCENTAGE,
    )


@app.cell
def _(
    PERSON2_AGE_LIMIT,
    PERSON2_DURATION_YEARS,
    PERSON2_PERCENTAGE,
    PLAN_ID,
    helpers,
    mo,
    plan_repo,
    settings_repo,
    summaries,
):
    valid_ids = {row.id for row in summaries}
    chosen_id = PLAN_ID if PLAN_ID is not None else settings_repo.get().default_plan_id
    mo.stop(
        chosen_id is None or chosen_id not in valid_ids,
        mo.md(
            "Set `plan_id` in `tools/disability_insurance.local.toml` "
            "to an id from the list above (default plan is missing or invalid)."
        ),
    )
    plan = plan_repo.get_by_id(chosen_id)
    mo.stop(
        plan is None,
        mo.md(
            f"Plan `{chosen_id}` could not be loaded. Pick another id from the list."
        ),
    )
    if plan.household.person2 is not None:
        try:
            helpers.validate_coverage(
                percentage=PERSON2_PERCENTAGE,
                duration_years=PERSON2_DURATION_YEARS,
                age_limit=PERSON2_AGE_LIMIT,
                label="person2",
            )
        except ValueError as exc:
            mo.stop(True, mo.md(str(exc)))
    mo.md(f"Using plan **{plan.name}** (`id={chosen_id}`).")
    return (plan,)


@app.cell
def _(
    Timeline,
    build_monthly_cashflows,
    helpers,
    mo,
    plan,
    project_job_income,
):
    timeline = Timeline(plan)
    baseline = build_monthly_cashflows(plan)
    jobs = project_job_income(plan, timeline)
    household_no_jobs = helpers.series_all_zero(jobs.person1.gross) and (
        jobs.person2 is None or helpers.series_all_zero(jobs.person2.gross)
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
    PERSON1_AGE_LIMIT: int | None,
    PERSON1_DURATION_YEARS: int | None,
    PERSON1_PERCENTAGE,
    baseline,
    helpers,
    jobs,
    mo,
    plan,
    timeline,
):
    person1_md = helpers.report_person(
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
    PERSON2_AGE_LIMIT: int | None,
    PERSON2_DURATION_YEARS: int | None,
    PERSON2_PERCENTAGE,
    baseline,
    helpers,
    jobs,
    mo,
    plan,
    timeline,
):
    partner = plan.household.person2
    person2_md = ""
    if partner is not None:
        person2_md = helpers.report_person(
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
    mo.md(person2_md)
    return


if __name__ == "__main__":
    app.run()

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Disability Insurance Calculator

    This notebook calculates disability insurance coverage needs by comparing
    baseline income projections (with job income) against disability scenarios
    (without job income). It accounts for:

    - Lost job income until the employer policy window ends
      (`age_limit` or `duration_years` from local config)
    - Reduced Social Security benefits (including after the policy window)
    - Reduced pension benefits (including after the policy window)
    - Existing employer-provided disability coverage (after taxes)
    - Remaining coverage gap in standard disability insurance format
      (% of income for x years)

    **Usage**: Copy `tools/disability_insurance.local.toml.example` to
    `tools/disability_insurance.local.toml`, set `plan_id` and coverage knobs,
    and keep a SQLite plan database at `data/data.db` (or `LIFE_FINANCES_DB_PATH`).
    """)
    return


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
    mo.md(
        f"""
    ## Plans

    Plans available in the SQLite database.

    {lines}
    """
    )
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
        f"""
    ## Local configuration

    Load `plan_id` and coverage knobs from gitignored
    `{helpers.LOCAL_CONFIG_PATH}` (zeros / default plan if the file is missing).

    Config: `{config_source}`.
    plan_id={PLAN_ID!s}.
    person1 {PERSON1_PERCENTAGE}%
    (duration_years={PERSON1_DURATION_YEARS!s}, age_limit={PERSON1_AGE_LIMIT!s});
    person2 {PERSON2_PERCENTAGE}%
    (duration_years={PERSON2_DURATION_YEARS!s}, age_limit={PERSON2_AGE_LIMIT!s}).
    Not saved to the plan.
    """
    )
    return (
        PERSON1_AGE_LIMIT,
        PERSON1_DURATION_YEARS,
        PERSON1_PERCENTAGE,
        PERSON2_AGE_LIMIT,
        PERSON2_DURATION_YEARS,
        PERSON2_PERCENTAGE,
        PLAN_ID,
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
    mo.md(
        f"""
    ## Plan selection

    Resolve `plan_id` (or the app default) and validate person2 coverage when
    the plan has a partner.

    Using plan **{plan.name}** (`id={chosen_id}`).
    """
    )
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
    mo.md(
        """
    ## Baseline cashflows

    Build the timeline, baseline monthly cashflows, and job-income projection.
    Stops if neither person has future job income.
    """
    )
    return baseline, jobs, timeline


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Your disability calculation

    Calculate disability insurance needs for you.
    """)
    return


@app.cell
def _(
    PERSON1_AGE_LIMIT,
    PERSON1_DURATION_YEARS,
    PERSON1_PERCENTAGE,
    baseline,
    helpers,
    jobs,
    mo,
    plan,
    timeline,
):
    person1_md = helpers.report_person(
        label="Your results",
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
def _(mo, plan):
    person2_heading = ""
    if plan.household.person2 is not None:
        person2_heading = """
    ## Your partner's disability calculation

    Calculate disability insurance needs for your partner.
    """
    mo.md(person2_heading)
    return


@app.cell
def _(
    PERSON2_AGE_LIMIT,
    PERSON2_DURATION_YEARS,
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
            label="Your partner's results",
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

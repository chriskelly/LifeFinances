# Phase 5 — Tools: Disability Insurance Calculator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A linear Marimo app that loads a SQLite plan and prints a full-parity disability-insurance coverage-gap report using `core` + `domain` only.

**Architecture:** `tools/disability_insurance.py` is a read-only consumer. It resolves a plan id (explicit or `AppSettings.default_plan_id`), clones the plan with `Plan.model_copy(deep=True)`, clears one person’s `jobs`, compares two `build_monthly_cashflows` results, and prints replacement need, after-tax employer coverage, and remaining gap as `% of income for X years`. Coverage literals stay in the notebook; nothing is written to SQLite.

**Tech Stack:** Python 3.14+, uv workspace, Marimo (root `dev` group), Pydantic `Plan`, `PlanRepository`, `SettingsRepository`, `domain.build_monthly_cashflows`, `domain.project_job_income`, `core.timeline.Timeline`.

**Design spec:** `docs/superpowers/specs/2026-08-28-phase-5-tools-disability-insurance-design.md`

**Branch:** continue `feat/phase-5-disability-insurance-design` (or rename to `feat/phase-5-disability-insurance` when implementation starts).

## Global Constraints

- Run all commands from the **repository root**.
- `uv add --dev marimo` only — never hand-edit `uv.lock` or `pyproject.toml` dependency lists.
- Notebook imports: `marimo` (host), `core`, `domain`. Never `web`. Never `simulation`.
- Do not call `PlanRepository.save`, `create`, `ensure_bootstrap`, or `get_or_create_default`.
- Coverage `percentage` is on a 0–100+ scale (`60` means 60%, not `0.60`).
- No pytest for gap formulas (spec §10). Do not add a Marimo execute step to `make test`.
- `make` (pytest + ruff + pyright) must still pass. If Marimo syntax fails ruff/pyright, exclude **`tools/` only** — do not weaken rules for `packages/`.
- Do not persist `DisabilityCoverage` on `Plan`. Do not add a web editor.

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| Modify: `pyproject.toml` / `uv.lock` | Via `uv add --dev marimo` only |
| Modify: `tools/AGENTS.md` | Run command, import rule, read-only DB, test exemption, how to add a tool |
| Create: `tools/disability_insurance.py` | Entire Marimo app (load, coverage, cashflows, report) |
| Modify: `README.md` | One-line pointer to the calculator |
| Modify: `AGENTS.md` | One-line pointer under Tools |
| Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` | Phase 5 plan + design links; exit criteria `core` + `domain` |
| Modify: `docs/superpowers/specs/2026-08-28-phase-5-tools-disability-insurance-design.md` | Point **Phase plan** at this file |
| Modify: `pyproject.toml` ruff `extend-exclude` | **Only if** `ruff check tools/disability_insurance.py` cannot parse Marimo |

---

## Testing policy

Application packages stay TDD. **This phase does not add tests** that re-encode the gap formulas (spec §10).

Each task’s verification is:

1. `make` still passes, and
2. For the notebook task: `uv run python -c "import ast; ast.parse(open('tools/disability_insurance.py').read())"` succeeds **or**, if Marimo’s `@app.cell` form is not plain Python that `ast` accepts, `uv run marimo check tools/disability_insurance.py` (or `uv run python tools/disability_insurance.py --help` / `marimo edit --headless` as available). Prefer `uv run marimo check` if that subcommand exists after install; otherwise parse/import the file in a way that does not open a browser.

Do **not** add `tests/test_disability_insurance.py`.

---

### Task 1: Marimo dev dependency and tools agent guide

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (via `uv add` only)
- Modify: `tools/AGENTS.md`

**Interfaces:**
- Consumes: existing `tools/AGENTS.md` placeholder
- Produces: `marimo` on the root `dev` dependency group; documented run command `uv run marimo edit tools/disability_insurance.py`

- [ ] **Step 1: Add Marimo**

Run from repo root:

```bash
uv add --dev marimo
```

Expected: `pyproject.toml` `[dependency-groups] dev` lists `marimo`; `uv.lock` updates. Do not add a `tools` workspace package.

- [ ] **Step 2: Confirm Marimo runs**

```bash
uv run marimo --help
```

Expected: help text, exit 0.

- [ ] **Step 3: Replace `tools/AGENTS.md`**

Write exactly:

```markdown
# Tools — Agent Guide

Marimo standalone apps live here. They consume shared packages; they are not the web UI.

## Run

From the repository root:

```bash
uv run marimo edit tools/disability_insurance.py
```

Optional: `uv run marimo run tools/disability_insurance.py` for view-only.

Working directory must be the repo root so `core.paths.default_db_path()` resolves `data/data.db`. Override with `LIFE_FINANCES_DB_PATH`.

## Rules

- Import `core` and `domain` only (plus `marimo` as the host). **Never** import `web` or `simulation`.
- Load plans with `PlanRepository.list` / `get_by_id` and `SettingsRepository.get`. **Never** `save`, `create`, `ensure_bootstrap`, or `get_or_create_default`.
- Coverage and other tool inputs stay in the notebook. Do not add fields to `Plan` for a tool unless a later spec says so.

## Tests

Standalone Marimo apps are **not** imported by `packages/` and are exempt from pytest. `make test` must not execute notebooks. Keep `make` green for the rest of the repo.

## Adding a tool

1. Create `tools/<name>.py` as a Marimo app (`import marimo` + `app = marimo.App()` + `@app.cell`).
2. Follow the import and read-only DB rules above.
3. Document the run command in this file’s Run section.
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock tools/AGENTS.md
git commit -m "$(cat <<'EOF'
chore(tools): add Marimo and document standalone app rules

Phase 5 needs a host runtime for the disability calculator without a tools uv package.
EOF
)"
```

---

### Task 2: Disability insurance Marimo notebook

**Files:**
- Create: `tools/disability_insurance.py`

**Interfaces:**
- Consumes: `PlanRepository.list`, `PlanRepository.get_by_id`, `SettingsRepository.get`, `default_db_path`, `Plan.model_copy(deep=True)`, `build_monthly_cashflows(plan, *, today=None) -> MonthlyCashflows`, `project_job_income(plan, timeline) -> JobIncomeProjection`, `Timeline(plan)`, `PersonAgeBoundary(person=..., age_months=...)`, `timeline.index_of`, `timeline.horizon_months`
- Produces: notebook cells that print the three-part report per person; `PLAN_ID: int | None = None` defaults via `settings.default_plan_id`

**Cell order (spec §4, household guard before per-person reports; helpers before baseline so `series_all_zero` exists):**

1. Imports + repositories  
2. List plans  
3. Resolve `PLAN_ID` / default; `mo.stop` on failure  
4. Coverage literals + `validate_coverage`  
5. Helper functions (same file, not a package)  
6. Baseline cashflows + job projection + household zero-job guard  
7. Person 1 report  
8. Person 2 report if `person2` is not `None`

- [ ] **Step 1: Create `tools/disability_insurance.py`**

Use this file (Marimo may rewrite `__generated_with` / cell ids on first `marimo edit`; that is fine). Helpers live in a cell so person 1 and person 2 share one implementation without a `domain` extract.

```python
import marimo

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
    from domain import MonthlyCashflows, build_monthly_cashflows
    from domain.job_income import JobIncomeProjection, PersonJobIncome, project_job_income

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
            f"Plan `{chosen_id}` could not be loaded. "
            "Pick another id from the list."
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
def _(
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
            return (
                f"## {label}\n\nNo future job income — disability insurance is not needed.\n"
            )
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
            "1. **Total income replacement needed:** "
            f"{fmt_money(need)}",
            f"   - Baseline post-tax lifetime: {fmt_money(sum_series(baseline.net_cashflow))}",
            f"   - Disability post-tax lifetime: {fmt_money(sum_series(disability.net_cashflow))}",
            f"   - Job (gross) delta: {fmt_money(job_delta)}",
            f"   - Social Security (gross) delta: {fmt_money(ss_delta)}",
            f"   - Pension + manual (gross) delta: {fmt_money(pension_delta)}",
            "   - Includes SS/pension changes after the employer policy window.",
            "",
            "2. **Existing coverage replacement (after taxes):** "
            f"{fmt_money(net_b)}",
            "   - Workplace disability benefits treated as taxable ordinary income.",
            f"   - Gross benefits: {fmt_money(gross_b)}; tax on benefits: {fmt_money(tax_b)}",
        ]
        if percentage > 100:
            lines.append("   - Entered percentage exceeds 100%; replacement capped at 100%.")
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
            "Neither person has future job income — "
            "disability insurance is not needed."
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
    if partner is None:
        return
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
    mo.md(person2_md)
    return


if __name__ == "__main__":
    app.run()
```

Fix Marimo’s returned-name list if the editor complains: every name a later cell uses must be returned from the cell that binds it. After first `marimo edit`, let Marimo rewrite returns; keep behavior identical.

**Do not import** `JobIncomeProjection` in `person_job`’s runtime if the helper cell’s annotation needs a quote or a late import — the first cell already imports it. If ruff flags `F821` on `JobIncomeProjection` in the helper cell, add it to that cell’s return/import list (copy the import into the helper cell; do not import `web` or `simulation`).

- [ ] **Step 2: Verify the file is a Marimo app**

```bash
uv run marimo check tools/disability_insurance.py
```

If `check` is not a subcommand, run:

```bash
uv run python -c "import importlib.util; spec = importlib.util.spec_from_file_location('di', 'tools/disability_insurance.py'); spec.loader.exec_module(importlib.util.module_from_spec(spec))"
```

Expected: exit 0. Then:

```bash
rg -n "from web|import web|from simulation|import simulation" tools/disability_insurance.py
```

Expected: no matches.

- [ ] **Step 3: Lint the notebook**

```bash
uv run ruff check tools/disability_insurance.py && uv run ruff format tools/disability_insurance.py
```

Expected: clean, or only Marimo-generated issues. If ruff cannot parse the file, add `"tools"` to `[tool.ruff] extend-exclude` in `pyproject.toml` (keep `archive` there too) and re-run `uv run ruff check .`.

Do **not** add `tools` to `pyrightconfig.json` `include` unless pyright is already scanning it and failing; default config includes only `packages`, `scripts`, `tests`.

- [ ] **Step 4: Manual run (required for this task)**

```bash
uv run python scripts/init_db.py
uv run marimo edit tools/disability_insurance.py
```

With `PLAN_ID = None` and a valid `default_plan_id`, the notebook must show that plan’s name. Set person 1 coverage to `percentage = Decimal("60")`, `duration_years = 5`, `age_limit = None` and confirm the three numbered sections print. If the default plan has no jobs, the “not needed” message is correct — use a plan that has job income to see the gap math.

- [ ] **Step 5: Commit**

```bash
git add tools/disability_insurance.py pyproject.toml
git commit -m "$(cat <<'EOF'
feat(tools): add Marimo disability insurance calculator

Load a SQLite plan and report coverage gap from domain cashflows without touching Plan or web.
EOF
)"
```

Only include `pyproject.toml` if you added the ruff exclude.

---

### Task 3: Docs, rebuild index, and `make`

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Modify: `docs/superpowers/specs/2026-08-28-phase-5-tools-disability-insurance-design.md`

**Interfaces:**
- Consumes: Task 2 run command and import rules
- Produces: index Phase 5 linked to this plan + design spec; exit criteria say `core` + `domain`

- [ ] **Step 1: README**

After the setup block (after the `LIFE_FINANCES_DB_PATH` line), add:

```markdown
Disability insurance calculator (Marimo): `uv run marimo edit tools/disability_insurance.py` — see `tools/AGENTS.md`.
```

- [ ] **Step 2: Root `AGENTS.md`**

In the **Tech stack** table, Tools row already says Marimo. Add a short **Standalone tools** subsection after **Bootstrap**:

```markdown
## Standalone tools

Disability insurance calculator: `uv run marimo edit tools/disability_insurance.py`. Rules: `tools/AGENTS.md` (`core`/`domain` only; never `web`).
```

- [ ] **Step 3: Rebuild index — Phase 5 section**

Replace the Phase 5 block (plan file through exit criteria) with:

```markdown
### Phase 5 — Tools

**Plan file:** [`2026-06-12-phase-5-tools-disability-insurance.md`](2026-06-12-phase-5-tools-disability-insurance.md)

**Design spec:** [`2026-08-28-phase-5-tools-disability-insurance-design.md`](../specs/2026-08-28-phase-5-tools-disability-insurance-design.md)

**Delivers:** Marimo disability insurance calculator using shared packages.

**References:** Legacy `standalone_tools/disability_insurance_calculator.ipynb`; design spec §5.

**Entry criteria:** Phase 4 minimum bar met (4a + 4c + 4d + thin 4b); full 4e/4f not required.

**Exit criteria:**

- [ ] `tools/disability_insurance.py` runs via `uv run marimo edit tools/disability_insurance.py`
- [ ] Uses `core` + `domain`; no `web` import; no `simulation` import
- [ ] `tools/AGENTS.md` documents adding new tools
```

Do **not** change the **Active phase** table from 4e to 5 unless this phase is the one being executed as current work. Leave 4e as current if that table still points at extended charts; this plan can run in parallel (index: 4e/4f do not block Phase 5).

- [ ] **Step 4: Spec header**

In `docs/superpowers/specs/2026-08-28-phase-5-tools-disability-insurance-design.md`, replace:

`**Phase plan:** \`2026-06-12-phase-5-tools-disability-insurance.md\` *(to write)*`

with:

`**Phase plan:** [\`2026-06-12-phase-5-tools-disability-insurance.md\`](../plans/2026-06-12-phase-5-tools-disability-insurance.md)`

- [ ] **Step 5: Run `make`**

```bash
make
```

Expected: pytest, ruff check, ruff format check, and pyright all pass.

- [ ] **Step 6: Commit**

```bash
git add README.md AGENTS.md docs/superpowers/plans/2026-06-12-rebuild-index.md docs/superpowers/specs/2026-08-28-phase-5-tools-disability-insurance-design.md
git commit -m "$(cat <<'EOF'
docs(phase-5): link disability calculator plan and run command

Index and agent docs should describe core+domain tools, not a simulation import.
EOF
)"
```

---

## Spec coverage (self-review)

| Spec | Task |
| ---- | ---- |
| Marimo file + `uv run marimo edit` | 2, 3 |
| Default plan when `PLAN_ID is None` | 2 |
| Tool-only coverage XOR rules | 2 |
| `build_monthly_cashflows` + clone/zero jobs | 2 |
| Person 2 when present | 2 |
| Need, after-tax employer, gap % for X years | 2 |
| Empty jobs / missing DB / bad id | 2 |
| No `web` / `simulation`; no `save` | 1, 2 |
| `tools/AGENTS.md` | 1 |
| README / root AGENTS / index `core`+`domain` | 3 |
| No pytest of gap math | global + testing policy |
| Marimo in root `dev` group | 1 |

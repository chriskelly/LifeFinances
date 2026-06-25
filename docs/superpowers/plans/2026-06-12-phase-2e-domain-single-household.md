# Phase 2e — Domain: Single-Person Household Implementation Plan

> **Status:** complete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the second household member optional so a plan can model a single person, auto-deriving `filing_status` from household size while honoring an explicit override.

**Architecture:** `Household.person2` becomes optional; a `people` helper and a `resolved_filing_status` property centralize "present members" and filing-status logic. Domain projections (`job_income`, `social_security`) gain optional `person2` fields and sum only present members; pension/taxes iterate present people; the aggregator is unchanged. A minimal `has_partner` toggle is added to the household editor.

**Tech Stack:** Python 3.14, Pydantic v2, FastAPI + Jinja2 + HTMX, pytest, ruff, pyright, uv workspace.

**Spec:** `docs/superpowers/specs/2026-06-25-phase-2e-domain-single-household-design.md`

---

## Conventions for every task

- Run all commands from the **repository root** (`/Users/chris/Projects/life-finances-workspace/LifeFInances`).
- Run a single test with: `uv run pytest <path>::<test> -v`
- Run a package's tests with: `uv run pytest packages/<pkg>/tests -v`
- Final gate before claiming done: `make` (build + test + lint) must pass.
- TDD: write the failing test, run it, confirm the failure is **logical** (`AssertionError` / `NotImplementedError`) not **structural** (`ImportError` / `AttributeError`). Add minimal scaffolding first if the failure is structural, then implement.
- Commit after each task with the message shown in its final step.

---

## File Structure

| File | Responsibility | Action |
| ---- | -------------- | ------ |
| `packages/core/core/models.py` | `Household.person2` optional; `people`, `resolved_filing_status`; `filing_status` default `None`; validator loops present people | Modify |
| `packages/core/core/timeline.py` | `horizon_months` over present people | Modify |
| `packages/core/tests/test_single_household.py` | `people`, resolver, single-person horizon, validator | Create |
| `packages/core/tests/test_household_tax_config.py` | default test asserts `resolved_filing_status` | Modify |
| `packages/domain/domain/job_income/__init__.py` | `JobIncomeProjection.person2` optional; totals over present | Modify |
| `packages/domain/domain/social_security/__init__.py` | `SocialSecurityProjection.person2` optional; skip spousal when absent | Modify |
| `packages/domain/domain/pension/__init__.py` | iterate `household.people` | Modify |
| `packages/domain/domain/taxes/__init__.py` | `resolved_filing_status`; FICA over present people | Modify |
| `packages/domain/tests/test_single_household.py` | single-person job income, SS, pension, FICA, cashflows | Create |
| `packages/web/web/forms.py` | `HouseholdForm`: `has_partner` + optional person2 | Modify |
| `packages/web/web/app.py` | `patch_household` route: optional person2 + `has_partner` Form params | Modify |
| `packages/web/web/templates/editor_household.html` | `has_partner` checkbox + disable-toggle for person2 fields | Modify |
| `packages/web/tests/test_app.py` | single vs two-person POST + round-trip | Modify |
| `packages/domain/OVERVIEW.md` | document single-household support | Modify |

---

## Task 1: Core — optional `person2`, `people`, and `resolved_filing_status`

**Files:**
- Modify: `packages/core/core/models.py`
- Create: `packages/core/tests/test_single_household.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_single_household.py`:

```python
from __future__ import annotations

from core.defaults import default_plan
from core.models import FilingStatus, Household, PersonHousehold


def _person(birth_year: int) -> PersonHousehold:
    return PersonHousehold(birth_month=1, birth_year=birth_year)


def test_household_people_excludes_absent_partner() -> None:
    person1 = _person(1980)
    household = Household(person1=person1, person2=None)

    assert household.people == (person1,)


def test_household_people_includes_present_partner() -> None:
    person1 = _person(1980)
    person2 = _person(1982)
    household = Household(person1=person1, person2=person2)

    assert household.people == (person1, person2)


def test_resolved_filing_status_is_single_for_one_person() -> None:
    expected: FilingStatus = "single"
    household = Household(person1=_person(1980), person2=None)

    assert household.resolved_filing_status == expected


def test_resolved_filing_status_is_mfj_for_two_people() -> None:
    expected: FilingStatus = "married_filing_jointly"
    household = Household(person1=_person(1980), person2=_person(1982))

    assert household.resolved_filing_status == expected


def test_explicit_filing_status_overrides_household_size() -> None:
    overridden: FilingStatus = "married_filing_jointly"
    household = Household(
        person1=_person(1980),
        person2=None,
        filing_status=overridden,
    )

    assert household.resolved_filing_status == overridden


def test_person2_defaults_to_none() -> None:
    household = Household(person1=_person(1980))

    assert household.person2 is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest packages/core/tests/test_single_household.py -v`
Expected: FAIL — `person2` is currently required (logical/validation failure on the `person2=None` and single-arg constructions) and `people` / `resolved_filing_status` raise `AttributeError`. Add the attributes (Step 3) so the failure becomes logical, then confirm pass.

- [ ] **Step 3: Implement in `packages/core/core/models.py`**

Change the `Household` class. Replace the current `person2`, `filing_status`, and `_validate_sabbatical_windows` definitions:

```python
class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold | None = None
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus | None = None
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)

    @property
    def people(self) -> tuple[PersonHousehold, ...]:
        if self.person2 is None:
            return (self.person1,)
        return (self.person1, self.person2)

    @property
    def resolved_filing_status(self) -> FilingStatus:
        if self.filing_status is not None:
            return self.filing_status
        return "single" if self.person2 is None else "married_filing_jointly"

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> Household:
        for person in self.people:
            for job in person.jobs:
                _validate_job_windows(job, self)
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_single_household.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_single_household.py
git commit -m "feat(core): make Household.person2 optional with filing-status resolver"
```

---

## Task 2: Core — update the default-plan filing-status test

`Task 1` flipped `filing_status`'s default from `"married_filing_jointly"` to `None`. The existing default test asserts the raw field and will now fail; it must assert the resolved value instead (the default plan is two-person, so it still resolves to MFJ).

**Files:**
- Modify: `packages/core/tests/test_household_tax_config.py:12-20`

- [ ] **Step 1: Run the existing test to observe the failure**

Run: `uv run pytest packages/core/tests/test_household_tax_config.py::test_household_defaults_to_married_filing_jointly -v`
Expected: FAIL — `assert None == 'married_filing_jointly'` (logical failure caused by the new default).

- [ ] **Step 2: Update the test to assert the resolved status**

Replace the body of `test_household_defaults_to_married_filing_jointly`:

```python
def test_household_defaults_to_married_filing_jointly() -> None:
    expected_status: FilingStatus = "married_filing_jointly"
    expected_fraction = Decimal("0.80")

    household = default_plan().household

    assert household.filing_status is None
    assert household.resolved_filing_status == expected_status
    assert household.residence_state is None
    assert household.ss_pension_taxable_fraction == expected_fraction
```

- [ ] **Step 3: Run the full core tax-config test file to verify it passes**

Run: `uv run pytest packages/core/tests/test_household_tax_config.py -v`
Expected: PASS (the round-trip and unknown-value tests are unaffected).

- [ ] **Step 4: Commit**

```bash
git add packages/core/tests/test_household_tax_config.py
git commit -m "test(core): assert resolved filing status for default plan"
```

---

## Task 3: Core — `horizon_months` over present people

**Files:**
- Modify: `packages/core/core/timeline.py:37-41`
- Modify: `packages/core/tests/test_single_household.py` (append)

- [ ] **Step 1: Write the failing test (append to `test_single_household.py`)**

```python
from datetime import date

from core.models import Plan, Portfolio
from core.timeline import horizon_months


def test_horizon_uses_only_present_people() -> None:
    birth_year=1980
    max_age_years=90
    today = date(2026, 1, 1)
    person1 = PersonHousehold(birth_month=1, birth_year=birth_year, max_age_years=max_age_years)
    plan = Plan(
        name="Single",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )
    expected = (birth_year + max_age_years - today.year) * 12 + (1 - today.month)

    assert horizon_months(plan, today=today) == expected
```

Add the needed imports at the top of the file if not already present (`from decimal import Decimal`).

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest packages/core/tests/test_single_household.py::test_horizon_uses_only_present_people -v`
Expected: FAIL — current `horizon_months` calls `person_end_date(household.person2)` with `person2=None`, raising `AttributeError` (structural). The fix in Step 3 converts this to a passing logical result.

- [ ] **Step 3: Implement in `packages/core/core/timeline.py`**

Replace `horizon_months`:

```python
def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    household = plan.household
    end = max(person_end_date(person) for person in household.people)
    return (end.year - today.year) * 12 + (end.month - today.month)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest packages/core/tests/test_single_household.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_single_household.py
git commit -m "feat(core): compute horizon over present household members"
```

---

## Task 4: Domain — optional `person2` in job income

**Files:**
- Modify: `packages/domain/domain/job_income/__init__.py`
- Create: `packages/domain/tests/test_single_household.py`

- [ ] **Step 1: Write the failing test**

Create `packages/domain/tests/test_single_household.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.job import Job
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary
from core.timeline import Timeline

from domain.job_income import project_job_income


def _single_person_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1983,
        jobs=[
            Job(
                annual_income=Decimal("120_000"),
                end=CalendarMonthBoundary(year=2045, month=12),
            )
        ],
    )
    return Plan(
        name="Single Person",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_job_income_omits_absent_partner_and_totals_equal_person1() -> None:
    plan = _single_person_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))

    projection = project_job_income(plan, timeline)

    assert projection.person2 is None
    assert projection.total_gross == projection.person1.gross
    assert projection.total_ss_covered_gross == projection.person1.ss_covered_gross
    assert projection.total_tax_deferred == projection.person1.tax_deferred
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest packages/domain/tests/test_single_household.py::test_job_income_omits_absent_partner_and_totals_equal_person1 -v`
Expected: FAIL — `project_job_income` calls `_project_person(plan.household.person2, ...)` with `None`, raising `AttributeError` (structural). Step 3 converts to a logical pass.

- [ ] **Step 3: Implement in `packages/domain/domain/job_income/__init__.py`**

Make `person2` optional on the model and project only when present. Replace the `JobIncomeProjection` class and `project_job_income`:

```python
class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome | None = None
    total_gross: list[Decimal]
    total_ss_covered_gross: list[Decimal]
    total_tax_deferred: list[Decimal]


def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection:
    person1 = _project_person(plan.household.person1, timeline)
    partner = plan.household.person2
    person2 = _project_person(partner, timeline) if partner is not None else None

    total_gross = person1.gross
    total_ss_covered_gross = person1.ss_covered_gross
    total_tax_deferred = person1.tax_deferred
    if person2 is not None:
        total_gross = _add(total_gross, person2.gross)
        total_ss_covered_gross = _add(
            total_ss_covered_gross, person2.ss_covered_gross
        )
        total_tax_deferred = _add(total_tax_deferred, person2.tax_deferred)

    return JobIncomeProjection(
        person1=person1,
        person2=person2,
        total_gross=total_gross,
        total_ss_covered_gross=total_ss_covered_gross,
        total_tax_deferred=total_tax_deferred,
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_single_household.py -v`
Expected: PASS

- [ ] **Step 5: Run the existing job-income tests to confirm no regression**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/job_income/__init__.py packages/domain/tests/test_single_household.py
git commit -m "feat(domain): project job income for single-person households"
```

---

## Task 5: Domain — optional `person2` in Social Security, skip spousal

**Files:**
- Modify: `packages/domain/domain/social_security/__init__.py`
- Modify: `packages/domain/tests/test_single_household.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
from core.social_security import (
    FULL_RETIREMENT_AGE_MONTHS,
    AnnualEarnings,
    PersonSocialSecurityConfig,
)
from domain.social_security import project_social_security


def _single_ss_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1960,
        social_security=PersonSocialSecurityConfig(
            claim_age_months=FULL_RETIREMENT_AGE_MONTHS,
            earnings_record=[
                AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
            ],
        ),
    )
    return Plan(
        name="Single SS",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_single_person_ss_has_no_spousal_and_total_equals_own() -> None:
    plan = _single_ss_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person2 is None
    assert projection.person1.spousal_alternative == (
        [Decimal("0.00")] * timeline.horizon_months
    )
    assert projection.person1.max_benefit == projection.person1.own_benefit
    assert projection.total == projection.person1.max_benefit
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest packages/domain/tests/test_single_household.py::test_single_person_ss_has_no_spousal_and_total_equals_own -v`
Expected: FAIL — `project_social_security` builds `person2_inputs` from `plan.household.person2` (`None`) and reads `job_income.person2.ss_covered_gross`, raising `AttributeError` (structural). Step 3 converts to a logical pass.

- [ ] **Step 3: Implement in `packages/domain/domain/social_security/__init__.py`**

Make `person2` optional on the projection, compute person2 inputs only when present, and pass an optional spouse to the spousal series. Replace `SocialSecurityProjection`, `_spousal_series`, and `project_social_security`:

```python
class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity | None = None
    total: list[Decimal]
```

```python
def _spousal_series(
    *,
    receiver_inputs: _PersonInputs,
    spouse_inputs: _PersonInputs | None,
    horizon: int,
) -> list[Decimal]:
    SPOUSAL_RATIO = Decimal("0.5")
    series = _zeroes(horizon)
    if spouse_inputs is None:
        return series
    start_index = max(
        receiver_inputs.claim_start_index, spouse_inputs.claim_start_index
    )
    monthly = (
        spouse_inputs.effective_pia * SPOUSAL_RATIO * receiver_inputs.claim_multiplier
    ).quantize(_CENTS)
    low = max(start_index, 0)
    for month_index in range(low, horizon):
        series[month_index] = monthly
    return series
```

```python
def project_social_security(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> SocialSecurityProjection:
    horizon = timeline.horizon_months
    trust_factor = plan.household.social_security_trust_factor
    person1_inputs = _person_inputs(
        person=plan.household.person1,
        person_id="person1",
        timeline=timeline,
        future_ss_covered=job_income.person1.ss_covered_gross,
        trust_factor=trust_factor,
    )
    partner = plan.household.person2
    person2_inputs = (
        _person_inputs(
            person=partner,
            person_id="person2",
            timeline=timeline,
            future_ss_covered=job_income.person2.ss_covered_gross,
            trust_factor=trust_factor,
        )
        if partner is not None and job_income.person2 is not None
        else None
    )

    person1_own = _own_series(person1_inputs, horizon)
    person1_spousal = _spousal_series(
        receiver_inputs=person1_inputs,
        spouse_inputs=person2_inputs,
        horizon=horizon,
    )
    person1 = _person_projection(person1_own, person1_spousal)

    if person2_inputs is None:
        return SocialSecurityProjection(
            person1=person1,
            person2=None,
            total=list(person1.max_benefit),
        )

    person2_own = _own_series(person2_inputs, horizon)
    person2_spousal = _spousal_series(
        receiver_inputs=person2_inputs,
        spouse_inputs=person1_inputs,
        horizon=horizon,
    )
    person2 = _person_projection(person2_own, person2_spousal)
    return SocialSecurityProjection(
        person1=person1,
        person2=person2,
        total=[
            a + b for a, b in zip(person1.max_benefit, person2.max_benefit, strict=True)
        ],
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_single_household.py::test_single_person_ss_has_no_spousal_and_total_equals_own -v`
Expected: PASS

- [ ] **Step 5: Run the existing SS tests to confirm no regression**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/social_security/__init__.py packages/domain/tests/test_single_household.py
git commit -m "feat(domain): skip spousal Social Security when partner absent"
```

---

## Task 6: Domain — pension iterates present people

**Files:**
- Modify: `packages/domain/domain/pension/__init__.py:56-64`
- Modify: `packages/domain/tests/test_single_household.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
from core.job import FormulaPension
from core.streams import PersonAgeBoundary
from domain.pension import project_pension
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def _single_pension_plan() -> Plan:
    person1 = PersonHousehold(
        birth_month=1,
        birth_year=1970,
        jobs=[
            Job(
                annual_income=Decimal("120_000"),
                end=PersonAgeBoundary(person="person1", age_months=62 * 12),
                pension=FormulaPension(
                    service_start=CalendarMonthBoundary(year=2010, month=1),
                    claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
                    age_factor_table=age_factors_from_statutory(
                        CALSTRS_2_AT_62_AGE_FACTORS
                    ),
                ),
            )
        ],
    )
    return Plan(
        name="Single Pension",
        household=Household(person1=person1, person2=None),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_single_person_pension_projects_without_partner() -> None:
    plan = _single_pension_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert len(projection.formula) == timeline.horizon_months
    assert any(value > Decimal("0.00") for value in projection.formula)
```

Note: `age_factor_table` is a required field on `FormulaPension` (`packages/core/core/job.py`), so it must be supplied; the statutory helper builds the CalSTRS default. `project_job_income` is already imported at the top of this test file from Task 4.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest packages/domain/tests/test_single_household.py::test_single_person_pension_projects_without_partner -v`
Expected: FAIL — `project_pension` loops `(household.person1, household.person2)` and accesses `None.jobs`, raising `AttributeError` (structural). Step 3 converts to a logical pass.

- [ ] **Step 3: Implement in `packages/domain/domain/pension/__init__.py`**

Replace the person loop in `project_pension`:

```python
    for person in household.people:
        for job in person.jobs:
            if job.pension is None:
                continue
            series = _formula_benefit_series(
                job=job, person=person, household=household, timeline=timeline
            )
            formula = [a + b for a, b in zip(formula, series, strict=True)]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_single_household.py::test_single_person_pension_projects_without_partner -v`
Expected: PASS

- [ ] **Step 5: Run the existing pension tests to confirm no regression**

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/pension/__init__.py packages/domain/tests/test_single_household.py
git commit -m "feat(domain): iterate present people in pension projection"
```

---

## Task 7: Domain — taxes use resolved filing status and present-people FICA

**Files:**
- Modify: `packages/domain/domain/taxes/__init__.py:45-67` (FICA helper) and `:89` (filing read)
- Modify: `packages/domain/tests/test_single_household.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
from domain import build_monthly_cashflows
from domain.taxes import compute_taxes


def test_single_person_taxes_use_single_brackets_and_no_partner_fica() -> None:
    plan = _single_person_plan()  # job income, no partner (defined in Task 4)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)
    social_security = project_social_security(plan, timeline, job_income)
    pension = project_pension(plan, timeline, job_income)

    taxes = compute_taxes(
        plan=plan,
        timeline=timeline,
        job_income=job_income,
        social_security=social_security,
        pension=pension,
    )

    # No AttributeError on absent person2; FICA SS present for the one worker.
    assert len(taxes.fica_social_security) == timeline.horizon_months
    assert any(value < Decimal("0.00") for value in taxes.fica_social_security)


def test_single_person_cashflows_run_end_to_end() -> None:
    plan = _single_person_plan()
    today = date(2026, 1, 1)

    cashflows = build_monthly_cashflows(plan, today=today)

    horizon = Timeline(plan, today=today).horizon_months
    assert len(cashflows.net_cashflow) == horizon
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest "packages/domain/tests/test_single_household.py::test_single_person_taxes_use_single_brackets_and_no_partner_fica" "packages/domain/tests/test_single_household.py::test_single_person_cashflows_run_end_to_end" -v`
Expected: FAIL — `_fica_social_security` reads `job_income.person2.ss_covered_gross` (`None`), raising `AttributeError` (structural). Step 3 converts to a logical pass.

- [ ] **Step 3: Implement in `packages/domain/domain/taxes/__init__.py`**

Build the FICA per-person series from present projections only. Replace the `person_series` assignment in `_fica_social_security`:

```python
    person_series = tuple(
        person.ss_covered_gross
        for person in (job_income.person1, job_income.person2)
        if person is not None
    )
```

And switch the filing-status read in `compute_taxes` from the raw field to the resolver:

```python
    filing = household.resolved_filing_status
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_single_household.py -v`
Expected: PASS

- [ ] **Step 5: Run the existing tax and cashflow tests to confirm no regression**

Run: `uv run pytest packages/domain/tests/test_taxes.py packages/domain/tests/test_cashflows.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/taxes/__init__.py packages/domain/tests/test_single_household.py
git commit -m "feat(domain): single-person taxes via resolved filing status"
```

---

## Task 8: Web — `has_partner` toggle in the household editor

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/app.py:122-145`
- Modify: `packages/web/web/templates/editor_household.html`
- Modify: `packages/web/tests/test_app.py`

- [ ] **Step 1: Write the failing tests**

In `packages/web/tests/test_app.py`, add the `has_partner` constant to the existing `from web.forms import (...)` block, then append:

```python
from web.forms import HAS_PARTNER  # add to the existing forms import block


def test_patch_household_without_partner_saves_single_person(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    form_data = _household_form_data()
    del form_data[PERSON2_BIRTH_MONTH]
    del form_data[PERSON2_BIRTH_YEAR]
    del form_data[PERSON2_MAX_AGE_YEARS]
    # has_partner omitted entirely, mirroring an unchecked HTML checkbox.

    response: httpx.Response = client.patch(PLAN_HOUSEHOLD, data=form_data)

    assert response.status_code == 200
    loaded = repo.get_by_id(1)
    assert loaded is not None
    assert loaded.household.person2 is None
    assert loaded.household.resolved_filing_status == "single"


def test_patch_household_with_partner_saves_two_people(
    client: TestClient, repo: PlanRepository
) -> None:
    home_response: httpx.Response = client.get(HOME)
    assert home_response.status_code == 200
    form_data = _household_form_data()
    form_data[HAS_PARTNER] = "on"

    response: httpx.Response = client.patch(PLAN_HOUSEHOLD, data=form_data)

    assert response.status_code == 200
    loaded = repo.get_by_id(1)
    assert loaded is not None
    assert loaded.household.person2 is not None
    assert loaded.household.resolved_filing_status == "married_filing_jointly"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest packages/web/tests/test_app.py::test_patch_household_without_partner_saves_single_person packages/web/tests/test_app.py::test_patch_household_with_partner_saves_two_people -v`
Expected: FAIL — `HAS_PARTNER` is undefined (`ImportError`) and the route requires person2 form fields. Add the constant and DTO fields (Steps 3–4) so the failure becomes logical, then pass.

- [ ] **Step 3: Implement the form in `packages/web/web/forms.py`**

Add the constant alongside the others and replace `HouseholdForm`:

```python
HAS_PARTNER = "has_partner"


class HouseholdForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    has_partner: bool = False
    person2_birth_month: int | None = None
    person2_birth_year: int | None = None
    person2_max_age_years: int | None = None

    def apply_to(self, plan: Plan) -> Plan:
        person2 = None
        if self.has_partner:
            person2 = PersonHousehold(
                birth_month=self.person2_birth_month,
                birth_year=self.person2_birth_year,
                max_age_years=self.person2_max_age_years,
            )
        household = Household(
            person1=PersonHousehold(
                birth_month=self.person1_birth_month,
                birth_year=self.person1_birth_year,
                max_age_years=self.person1_max_age_years,
            ),
            person2=person2,
        )
        return plan.model_copy(update={"household": household})
```

- [ ] **Step 4: Implement the route in `packages/web/web/app.py`**

Replace the `patch_household` signature and body so person2 fields and `has_partner` are optional Form params:

```python
    @app.patch(PLAN_HOUSEHOLD)
    def patch_household(
        person1_birth_month: Annotated[int, Form()],
        person1_birth_year: Annotated[int, Form()],
        person1_max_age_years: Annotated[int, Form()],
        repo: RepoDep,
        has_partner: Annotated[bool, Form()] = False,
        person2_birth_month: Annotated[int | None, Form()] = None,
        person2_birth_year: Annotated[int | None, Form()] = None,
        person2_max_age_years: Annotated[int | None, Form()] = None,
    ) -> Response:
        plan_id, plan = repo.get_or_create_default()
        try:
            updated = HouseholdForm(
                person1_birth_month=person1_birth_month,
                person1_birth_year=person1_birth_year,
                person1_max_age_years=person1_max_age_years,
                has_partner=has_partner,
                person2_birth_month=person2_birth_month,
                person2_birth_year=person2_birth_year,
                person2_max_age_years=person2_max_age_years,
            ).apply_to(plan)
        except ValidationError as exc:
            return HTMLResponse(_validation_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)
```

- [ ] **Step 5: Update the template `packages/web/web/templates/editor_household.html`**

Add a checkbox and guard the person2 fields for a `None` partner. Replace the partner `<fieldset>` (lines 35-61) with:

```html
    <label class="partner-toggle">
      <input
        type="checkbox"
        name="{{ forms.HAS_PARTNER }}"
        {% if plan.household.person2 %}checked{% endif %}
        onchange="this.closest('form').querySelectorAll('.partner-fields input, .partner-fields select').forEach(el => el.disabled = !this.checked)"
      >
      Include a partner
    </label>
    <fieldset class="person-fields partner-fields">
      <legend>Partner</legend>
      <label>
        Birth month
        <select name="{{ forms.PERSON2_BIRTH_MONTH }}"{% if not plan.household.person2 %} disabled{% endif %}>
          {% for month in range(1, 13) %}
          <option value="{{ month }}"{% if plan.household.person2 and plan.household.person2.birth_month == month %} selected{% endif %}>{{ month }}</option>
          {% endfor %}
        </select>
      </label>
      <label>
        Birth year
        <input
          type="number"
          name="{{ forms.PERSON2_BIRTH_YEAR }}"
          value="{{ plan.household.person2.birth_year if plan.household.person2 else '' }}"
          {% if not plan.household.person2 %}disabled{% endif %}
        >
      </label>
      <label>
        Max age
        <input
          type="number"
          name="{{ forms.PERSON2_MAX_AGE_YEARS }}"
          value="{{ plan.household.person2.max_age_years if plan.household.person2 else '' }}"
          {% if not plan.household.person2 %}disabled{% endif %}
        >
      </label>
    </fieldset>
```

Rationale: disabled inputs are not submitted, so an unchecked partner sends no person2 fields and `has_partner` defaults to `False` server-side. The `onchange` handler enables/disables the fields live.

- [ ] **Step 6: Run the web tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`
Expected: PASS (including the existing two-person tests, which still send all person2 fields).

- [ ] **Step 7: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/app.py packages/web/web/templates/editor_household.html packages/web/tests/test_app.py
git commit -m "feat(web): add has-partner toggle for single-person households"
```

---

## Task 9: Document single-household support in `OVERVIEW.md`

**Files:**
- Modify: `packages/domain/OVERVIEW.md`

- [ ] **Step 1: Add a single-household note**

Append a section after the "Legacy port map" table:

```markdown
## Single-person households (Phase 2e)

`Household.person2` is optional (`None` = single-person plan). `Household.people`
yields present members; `Household.resolved_filing_status` derives `single` vs
`married_filing_jointly` from household size unless `filing_status` is set
explicitly. Job income, Social Security (spousal skipped when absent), pension,
taxes, and `build_monthly_cashflows` all operate over present members only.
```

- [ ] **Step 2: Commit**

```bash
git add packages/domain/OVERVIEW.md
git commit -m "docs(domain): document single-person household support"
```

---

## Task 10: Full verification and index update

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (active-phase table, completed-plans table, Phase 2e exit checkboxes)

- [ ] **Step 1: Run the full gate**

Run: `make`
Expected: build + test + lint all pass.

- [ ] **Step 2: Mark this plan complete and advance the index**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`:
- Check the Phase 2e exit-criteria boxes (all five) and the `OVERVIEW.md` item.
- Update the **Active phase** table to Phase 3a (`2026-06-12-phase-3a-simulation-market-data.md` *(to write)*), next action "Write Phase 3a plan before coding".
- Add a row to the **Completed plans** table: `Phase 2e | 2026-06-12-phase-2e-domain-single-household.md | complete`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "docs(plan): mark Phase 2e complete and advance index to 3a"
```

---

## Self-Review

**Spec coverage:**
- Optional `person2` → Tasks 1, 4, 5, 8. ✓
- `filing_status` resolver + override honored → Tasks 1, 2, 7. ✓
- Job income / SS / pension / `build_monthly_cashflows` single-person → Tasks 4, 5, 6, 7. ✓
- Spousal SS skipped when absent → Task 5. ✓
- Web toggle → Task 8. ✓
- `OVERVIEW.md` → Task 9. ✓
- `make` passes → Task 10. ✓

**Type consistency:** `Household.people`, `Household.resolved_filing_status`, `JobIncomeProjection.person2: PersonJobIncome | None`, `SocialSecurityProjection.person2: PersonSocialSecurity | None`, `_spousal_series(spouse_inputs: _PersonInputs | None)`, and `HouseholdForm.has_partner: bool` are defined once and used consistently across tasks.

**Placeholder scan:** No TBD/TODO; every code step shows complete code. Task 6's note to verify `FormulaPension` required fields is a read-before-write reminder, not a placeholder.

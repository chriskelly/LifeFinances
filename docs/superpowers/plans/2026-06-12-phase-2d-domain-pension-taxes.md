# Phase 2d — Domain: Pension and Taxes Implementation Plan

**Status:** Complete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port legacy pension and income-side tax logic onto the Phase 2a–2c monthly domain foundation and deliver `domain.build_monthly_cashflows(plan)` — the aggregator that assembles all income sources, applies income-side taxes, and returns month-indexed net cashflows.

**Architecture:** Pension and tax *config* live in `core` (persisted on `Plan`): `FormulaPension`/`AgeFactor` attach to a `Job`; `filing_status`, `residence_state`, and `ss_pension_taxable_fraction` attach to `Household`. Statutory source data (CalSTRS age factors, federal/CA/NY brackets, FICA rates) live in `domain/statutory`. Calculation lives in `domain/pension`, `domain/taxes`, and the `domain/__init__.py` aggregator. All series are month-indexed, real today's-dollars; taxes are negative outflows.

**Tech Stack:** Python 3.14, Pydantic v2, `Decimal` money math, pytest, uv workspace. Spec: `docs/superpowers/specs/2026-06-25-phase-2d-domain-pension-taxes-design.md`.

**Conventions for every task:**

- Follow TDD: write the behavior test, scaffold to a *logical* red (`NotImplementedError`, wrong return, or missing validation), confirm the failure is logical (not `ImportError`/`AttributeError`), implement, confirm green.
- Run commands from the repository root: `/Users/chris/Projects/life-finances-workspace/LifeFInances`.
- Single test command: `uv run pytest <path>::<test_name> -v`.
- Package-level test command: `uv run pytest packages/core/tests packages/domain/tests -v`.
- Full verification command: `make`.
- Bind expected values to variables and reference them in both arrange and assert when a value appears in both places.
- Import constants from production modules in tests instead of copying literals, except where a test intentionally pins a public statutory contract and says so in a comment.
- Use underscore grouping in `Decimal` integer literals for readability (e.g. `Decimal("1_000_000")`, `Decimal("48_475")`).
- Sum series stored on projection models as `stored_total` at compute time (not `@computed_field`) so consumers never re-derive O(n) totals on each access.
- Commit after each task. The pre-commit hook runs `make`; do not skip it.

**Resolved layering note (read before Task 2):** The spec sketches `FormulaPension.age_factor_table` defaulting to the statutory CalSTRS table via `default_factory`. The strict dependency rule (`core → stdlib + pydantic + sqlite` only; `core` must never import `domain`) forbids `core` reaching `domain/statutory`. Therefore `age_factor_table` is a **required** field on `FormulaPension`, and `domain/statutory/pension.py` ships `age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)` as the resolved default that callers (and the Phase 4 UI) use to populate the persisted table. This keeps a single source of truth in `domain/statutory` without a layering violation.

---

## File Structure

`packages/core/`

- `core/job.py` *(modify)* — add `AgeFactor`, `FormulaPension`; add `Job.pension`.
- `core/models.py` *(modify)* — add `FilingStatus`; add `Household.filing_status`, `Household.residence_state`, `Household.ss_pension_taxable_fraction`.
- `tests/test_pension_config.py` *(new)* — pension config validation + repository round-trip.
- `tests/test_household_tax_config.py` *(new)* — household tax-field validation + repository round-trip.

`packages/domain/`

- `domain/statutory/pension.py` *(new)* — `CALSTRS_2_AT_62_AGE_FACTORS`, `SOURCE_NOTES`, `age_factors_from_statutory`.
- `domain/statutory/taxes.py` *(new)* — federal/CA/NY brackets, standard deductions, FICA rates, staleness check.
- `domain/pension/__init__.py` *(new)* — `PensionProjection`, `project_pension`.
- `domain/pension/formula.py` *(new)* — service credit, final compensation, age-factor interpolation, claim age.
- `domain/taxes/__init__.py` *(new)* — `TaxBreakdown`, `compute_taxes`.
- `domain/taxes/brackets.py` *(new)* — progressive bracket math and annual income-tax helper.
- `domain/__init__.py` *(modify)* — `MonthlyCashflows`, `build_monthly_cashflows`.
- `tests/test_pension.py` *(new)* — formula helpers + projection + single-source-of-truth + manual path.
- `tests/test_taxes.py` *(new)* — statutory tables, bracket math, filing status, aggregation/distribution, FICA, state, sign.
- `tests/test_cashflows.py` *(new)* — aggregator series length, net cashflow, integration.
- `OVERVIEW.md` *(modify)* — pension + taxes + aggregator status.

`docs/superpowers/plans/`

- `2026-06-12-rebuild-index.md` *(modify at phase completion)* — mark Phase 2d complete, point active phase to Phase 2e.

---

## Task 1: Household tax config (`core`)

**Files:**

- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_household_tax_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/core/tests/test_household_tax_config.py
from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.models import FilingStatus, Household, Plan
from core.repository import PlanRepository
from pydantic import ValidationError


def test_household_defaults_to_married_filing_jointly() -> None:
    expected_status: FilingStatus = "married_filing_jointly"
    expected_fraction = Decimal("0.80")

    household = default_plan().household

    assert household.filing_status == expected_status
    assert household.residence_state is None
    assert household.ss_pension_taxable_fraction == expected_fraction


def test_ss_pension_taxable_fraction_must_be_between_zero_and_one() -> None:
    base = default_plan().household
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        Household(
            person1=base.person1,
            person2=base.person2,
            ss_pension_taxable_fraction=too_high,
        )


def test_filing_status_rejects_unknown_value() -> None:
    base = default_plan().household

    with pytest.raises(ValidationError):
        Household(person1=base.person1, person2=base.person2, filing_status="unknown")


def test_household_tax_config_round_trips_through_repository(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_status: FilingStatus = "single"
    expected_state = "California"
    expected_fraction = Decimal("0.65")

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=plan.household.person1,
            person2=plan.household.person2,
            filing_status=expected_status,
            residence_state=expected_state,
            ss_pension_taxable_fraction=expected_fraction,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.filing_status == expected_status
    assert loaded.household.residence_state == expected_state
    assert loaded.household.ss_pension_taxable_fraction == expected_fraction
```

- [ ] **Step 2: Run tests to verify they fail logically**

Run: `uv run pytest packages/core/tests/test_household_tax_config.py -v`
Expected: FAIL with `ImportError` on `FilingStatus` first. Add the minimal scaffolding in Step 3 until the failure becomes a logical `AssertionError`/`ValidationError` mismatch, then implement fully. Confirm the failure is logical before moving on.

- [ ] **Step 3: Implement the household tax fields**

In `packages/core/core/models.py`, add the `Literal` import and `FilingStatus` alias near the top, then extend `Household`:

```python
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from core.job import Job
from core.social_security import PersonSocialSecurityConfig
from core.streams import TimedStream
from core.timeline import boundary_to_year_month

FilingStatus = Literal["married_filing_jointly", "single"]
```

```python
class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus = "married_filing_jointly"
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Field(default=Decimal("0.80"), ge=0, le=1)

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> Household:
        for person in (self.person1, self.person2):
            for job in person.jobs:
                _validate_job_windows(job, self)
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_household_tax_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_household_tax_config.py
git commit -m "feat(core): add household filing status and tax config"
```

---

## Task 2: Pension config models (`core`)

**Files:**

- Modify: `packages/core/core/job.py`
- Test: `packages/core/tests/test_pension_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/core/tests/test_pension_config.py
from __future__ import annotations

from decimal import Decimal

import pytest
from core.defaults import default_plan
from core.job import AgeFactor, FormulaPension, Job
from core.models import Household, PersonHousehold, Plan
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from pydantic import ValidationError


def _formula_pension() -> FormulaPension:
    return FormulaPension(
        service_start=CalendarMonthBoundary(year=2016, month=1),
        claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
        age_factor_table=[
            AgeFactor(age_months=62 * 12, factor=Decimal("0.0200")),
            AgeFactor(age_months=65 * 12, factor=Decimal("0.0240")),
        ],
    )


def test_formula_pension_defaults() -> None:
    expected_averaging_months = 36
    expected_trust = Decimal(1)

    pension = _formula_pension()

    assert pension.final_comp_averaging_months == expected_averaging_months
    assert pension.trust_factor == expected_trust
    assert pension.benefit_real_growth_rate == Decimal(0)


def test_trust_factor_must_be_between_zero_and_one() -> None:
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
            trust_factor=too_high,
        )


def test_job_pension_defaults_to_none() -> None:
    assert Job(annual_income=Decimal("100_000")).pension is None


def test_pension_config_round_trips_through_repository(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_pension = _formula_pension()
    job_with_pension = Job(
        annual_income=Decimal("109_500"),
        end=CalendarMonthBoundary(year=2045, month=12),
        pension=expected_pension,
    )

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=plan.household.person1.birth_month,
                birth_year=plan.household.person1.birth_year,
                max_age_years=plan.household.person1.max_age_years,
                jobs=[job_with_pension],
                social_security=plan.household.person1.social_security,
            ),
            person2=plan.household.person2,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.person1.jobs[0].pension == expected_pension
```

- [ ] **Step 2: Run tests to verify they fail logically**

Run: `uv run pytest packages/core/tests/test_pension_config.py -v`
Expected: FAIL with `ImportError` on `AgeFactor`/`FormulaPension`. Add the models (Step 3), re-run, and confirm the failure becomes logical before claiming green.

- [ ] **Step 3: Implement the pension config models**

In `packages/core/core/job.py`, add `AgeFactor` and `FormulaPension` and the optional `Job.pension` field:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from core.streams import Boundary


class AgeFactor(BaseModel):
    """Defined-benefit age factor at a given age."""

    age_months: int = Field(ge=0)
    factor: Decimal = Field(ge=0)


class FormulaPension(BaseModel):
    """Defined-benefit pension formula attached to a job.

    Benefit = service_credit_years x age_factor x final_compensation.
    All dollar amounts are real today's dollars; inflation is applied by the
    simulation layer on the projected benefit stream.
    """

    service_start: Boundary
    claim: Boundary
    age_factor_table: list[AgeFactor]
    final_comp_averaging_months: int = Field(default=36, ge=1)
    trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    benefit_real_growth_rate: Decimal = Decimal(0)
```

Add `pension` to `Job` (place the field with the other optional fields, before the validator):

```python
class Job(BaseModel):
    label: str | None = None
    annual_income: Decimal = Field(ge=0)
    annual_tax_deferred: Decimal = Field(default=Decimal(0), ge=0)
    annual_raise: Decimal = Decimal(0)
    start: Boundary | None = None
    end: Boundary | None = None
    social_security_eligible: bool = True
    sabbaticals: list[SabbaticalWindow] = Field(default_factory=list)
    pension: FormulaPension | None = None

    @model_validator(mode="after")
    def _tax_deferred_within_income(self) -> Job:
        if self.annual_tax_deferred > self.annual_income:
            raise ValueError("annual_tax_deferred must not exceed annual_income")
        return self
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_pension_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/job.py packages/core/tests/test_pension_config.py
git commit -m "feat(core): add job-attached formula pension config"
```

---

## Task 3: Statutory pension age factors (`domain/statutory`)

**Files:**

- Create: `packages/domain/domain/statutory/pension.py`
- Test: `packages/domain/tests/test_pension.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/domain/tests/test_pension.py
from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def test_calstrs_table_spans_55_to_65_and_is_monotonic() -> None:
    youngest_age_months = 55 * 12
    oldest_age_months = 65 * 12

    ages = [age for age, _ in CALSTRS_2_AT_62_AGE_FACTORS]
    factors = [factor for _, factor in CALSTRS_2_AT_62_AGE_FACTORS]

    assert ages[0] == youngest_age_months
    assert ages[-1] == oldest_age_months
    assert factors == sorted(factors)


def test_age_factors_from_statutory_builds_config_models() -> None:
    rows = ((62 * 12, Decimal("0.0200")), (65 * 12, Decimal("0.0240")))

    result = age_factors_from_statutory(rows)

    assert result == [
        AgeFactor(age_months=62 * 12, factor=Decimal("0.0200")),
        AgeFactor(age_months=65 * 12, factor=Decimal("0.0240")),
    ]
```

- [ ] **Step 2: Run test to verify it fails logically**

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: FAIL with `ModuleNotFoundError` for `domain.statutory.pension`. After Step 3 the failure must become a logical assertion pass/fail.

- [ ] **Step 3: Implement the statutory pension module**

```python
# packages/domain/domain/statutory/pension.py
from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor

SOURCE_NOTES = {
    "calstrs_2_at_62": (
        "CalSTRS 2% at 62 age factors: "
        "https://www.calstrs.com/age-factor"
    ),
}

# CalSTRS 2% at 62 benefit (age) factors, keyed by age in months.
CALSTRS_2_AT_62_AGE_FACTORS: tuple[tuple[int, Decimal], ...] = (
    (55 * 12, Decimal("0.0116")),
    (56 * 12, Decimal("0.0128")),
    (57 * 12, Decimal("0.0140")),
    (58 * 12, Decimal("0.0152")),
    (59 * 12, Decimal("0.0164")),
    (60 * 12, Decimal("0.0176")),
    (61 * 12, Decimal("0.0188")),
    (62 * 12, Decimal("0.0200")),
    (63 * 12, Decimal("0.0213")),
    (64 * 12, Decimal("0.0227")),
    (65 * 12, Decimal("0.0240")),
)


def age_factors_from_statutory(
    rows: tuple[tuple[int, Decimal], ...],
) -> list[AgeFactor]:
    """Convert statutory (age_months, factor) rows to plan config models."""
    return [AgeFactor(age_months=age, factor=factor) for age, factor in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/statutory/pension.py packages/domain/tests/test_pension.py
git commit -m "feat(domain): add CalSTRS statutory age-factor table"
```

---

## Task 4: Pension formula helpers (`domain/pension/formula.py`)

**Files:**

- Create: `packages/domain/domain/pension/formula.py`
- Test: `packages/domain/tests/test_pension.py` (append)

- [ ] **Step 1: Write the failing tests (append to `test_pension.py`)**

```python
from datetime import date

import pytest
from core.job import FormulaPension, Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from core.timeline import Timeline
from domain.pension.formula import (
    claim_age_months,
    final_compensation,
    interpolate_age_factor,
    service_credit_years,
)


def _person_with_job(job: Job, *, birth_year: int = 1983) -> PersonHousehold:
    return PersonHousehold(birth_month=1, birth_year=birth_year, jobs=[job])


def _plan_with_person1_job(job: Job) -> Plan:
    return Plan(
        name="Pension Test",
        household=Household(
            person1=_person_with_job(job),
            person2=PersonHousehold(birth_month=1, birth_year=1985),
        ),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_service_credit_counts_inclusive_months_as_years() -> None:
    service_start = CalendarMonthBoundary(year=2016, month=1)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    expected_years = Decimal(30)
    job = Job(annual_income=Decimal("120_000"), end=job_end, pension=FormulaPension(
        service_start=service_start,
        claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
        age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
    ))
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    assert service_credit_years(job=job, timeline=timeline) == expected_years


def test_service_credit_reduced_by_sabbatical_loss() -> None:
    service_start = CalendarMonthBoundary(year=2016, month=1)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    remaining = Decimal("0.5")
    break_start = CalendarMonthBoundary(year=2030, month=1)
    break_end = CalendarMonthBoundary(year=2030, month=12)
    window_years = Decimal(12) / Decimal(12)
    expected_years = Decimal(30) - (Decimal(1) - remaining) * window_years
    job = Job(
        annual_income=Decimal("120_000"),
        end=job_end,
        sabbaticals=[
            SabbaticalWindow(start=break_start, end=break_end, remaining_fraction=remaining)
        ],
        pension=FormulaPension(
            service_start=service_start,
            claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
            age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
        ),
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    assert service_credit_years(job=job, timeline=timeline) == expected_years


def test_service_credit_requires_job_end() -> None:
    job = Job(annual_income=Decimal("120_000"), pension=FormulaPension(
        service_start=CalendarMonthBoundary(year=2016, month=1),
        claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
        age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
    ))
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    with pytest.raises(ValueError, match="job end"):
        service_credit_years(job=job, timeline=timeline)


def test_final_compensation_averages_trailing_months_annualized() -> None:
    monthly_income = Decimal("10_000")
    annual_income = monthly_income * Decimal(12)
    job_end = CalendarMonthBoundary(year=2045, month=12)
    job = Job(annual_income=annual_income, end=job_end, pension=FormulaPension(
        service_start=CalendarMonthBoundary(year=2016, month=1),
        claim=PersonAgeBoundary(person="person1", age_months=62 * 12),
        age_factor_table=[AgeFactor(age_months=62 * 12, factor=Decimal("0.02"))],
        final_comp_averaging_months=12,
    ))
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))

    # No raise, no sabbatical => final comp equals the annual income.
    assert final_compensation(job=job, timeline=timeline) == annual_income


def test_interpolate_age_factor_is_linear_between_rows() -> None:
    factor_at_62 = Decimal("0.0200")
    factor_at_63 = Decimal("0.0213")
    table = [
        AgeFactor(age_months=62 * 12, factor=factor_at_62),
        AgeFactor(age_months=63 * 12, factor=factor_at_63),
    ]
    midpoint_age = 62 * 12 + 6
    expected = factor_at_62 + (factor_at_63 - factor_at_62) * (
        Decimal(6) / Decimal(12)
    )

    assert interpolate_age_factor(table, midpoint_age) == expected


def test_interpolate_age_factor_clamps_outside_table_range() -> None:
    factor_at_62 = Decimal("0.0200")
    factor_at_65 = Decimal("0.0240")
    table = [
        AgeFactor(age_months=62 * 12, factor=factor_at_62),
        AgeFactor(age_months=65 * 12, factor=factor_at_65),
    ]

    assert interpolate_age_factor(table, 55 * 12) == factor_at_62
    assert interpolate_age_factor(table, 70 * 12) == factor_at_65


def test_interpolate_age_factor_rejects_empty_table() -> None:
    with pytest.raises(ValueError, match="empty"):
        interpolate_age_factor([], 62 * 12)


def test_claim_age_months_uses_owning_person_birth() -> None:
    birth_year = 1983
    claim_age = 62 * 12
    person = PersonHousehold(birth_month=1, birth_year=birth_year)
    household = Household(
        person1=person, person2=PersonHousehold(birth_month=1, birth_year=1985)
    )
    claim = PersonAgeBoundary(person="person1", age_months=claim_age)

    assert claim_age_months(person=person, claim=claim, household=household) == claim_age
```

- [ ] **Step 2: Scaffold and run to a logical red**

Create `packages/domain/domain/pension/formula.py` with stubs that raise `NotImplementedError`:

```python
# packages/domain/domain/pension/formula.py
from __future__ import annotations

from decimal import Decimal

from core.job import AgeFactor, Job
from core.models import Household, PersonHousehold
from core.streams import Boundary
from core.timeline import Timeline, boundary_to_year_month

from domain.job_income.compile import project_job_gross

_MONTHS_PER_YEAR = Decimal(12)


def service_credit_years(*, job: Job, timeline: Timeline) -> Decimal:
    raise NotImplementedError


def final_compensation(*, job: Job, timeline: Timeline) -> Decimal:
    raise NotImplementedError


def interpolate_age_factor(table: list[AgeFactor], age_months: int) -> Decimal:
    raise NotImplementedError


def claim_age_months(
    *, person: PersonHousehold, claim: Boundary, household: Household
) -> int:
    raise NotImplementedError
```

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: FAIL with `NotImplementedError` (logical red), not import errors. Confirm before implementing.

- [ ] **Step 3: Implement the helpers**

```python
def _absolute_month(boundary: Boundary, household: Household) -> int:
    year, month = boundary_to_year_month(boundary, household)
    return year * 12 + month


def service_credit_years(*, job: Job, timeline: Timeline) -> Decimal:
    if job.pension is None:
        raise ValueError("service_credit_years requires a job with a formula pension")
    if job.end is None:
        raise ValueError("formula pension requires a job end boundary")
    household = timeline.plan.household
    start_abs = _absolute_month(job.pension.service_start, household)
    end_abs = _absolute_month(job.end, household)
    gross_months = end_abs - start_abs + 1
    loss_years = Decimal(0)
    for window in job.sabbaticals:
        window_months = (
            _absolute_month(window.end, household)
            - _absolute_month(window.start, household)
            + 1
        )
        loss_years += (Decimal(1) - window.remaining_fraction) * (
            Decimal(window_months) / _MONTHS_PER_YEAR
        )
    return Decimal(gross_months) / _MONTHS_PER_YEAR - loss_years


def final_compensation(*, job: Job, timeline: Timeline) -> Decimal:
    if job.pension is None:
        raise ValueError("final_compensation requires a job with a formula pension")
    if job.end is None:
        raise ValueError("formula pension requires a job end boundary")
    horizon = timeline.horizon_months
    if horizon <= 0:
        return Decimal("0.00")
    gross = project_job_gross(job, timeline)
    end_index = min(max(timeline.index_of(job.end), 0), horizon - 1)
    averaging_months = job.pension.final_comp_averaging_months
    start_index = max(end_index - averaging_months + 1, 0)
    window = gross[start_index : end_index + 1]
    average_monthly = sum(window, Decimal(0)) / Decimal(len(window))
    return average_monthly * _MONTHS_PER_YEAR


def interpolate_age_factor(table: list[AgeFactor], age_months: int) -> Decimal:
    if not table:
        raise ValueError("empty age_factor_table")
    rows = sorted(table, key=lambda row: row.age_months)
    if age_months <= rows[0].age_months:
        return rows[0].factor
    if age_months >= rows[-1].age_months:
        return rows[-1].factor
    for lower, upper in zip(rows, rows[1:], strict=False):
        if lower.age_months <= age_months <= upper.age_months:
            span = upper.age_months - lower.age_months
            if span == 0:
                return lower.factor
            ratio = Decimal(age_months - lower.age_months) / Decimal(span)
            return lower.factor + (upper.factor - lower.factor) * ratio
    return rows[-1].factor


def claim_age_months(
    *, person: PersonHousehold, claim: Boundary, household: Household
) -> int:
    claim_year, claim_month = boundary_to_year_month(claim, household)
    return (claim_year - person.birth_year) * 12 + (claim_month - person.birth_month)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/pension/formula.py packages/domain/tests/test_pension.py
git commit -m "feat(domain): add pension formula helpers"
```

---

## Task 5: Pension projection (`domain/pension/__init__.py`)

**Files:**

- Create: `packages/domain/domain/pension/__init__.py`
- Test: `packages/domain/tests/test_pension.py` (append)

- [ ] **Step 1: Write the failing tests (append to `test_pension.py`)**

```python
from core.streams import TimedStream
from domain.job_income import project_job_income
from domain.pension import PensionProjection, project_pension
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def _job_with_pension(*, annual_income: Decimal, claim_age_months_value: int, end_year: int) -> Job:
    return Job(
        annual_income=annual_income,
        end=CalendarMonthBoundary(year=end_year, month=12),
        pension=FormulaPension(
            service_start=CalendarMonthBoundary(year=2016, month=1),
            claim=PersonAgeBoundary(person="person1", age_months=claim_age_months_value),
            age_factor_table=age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS),
        ),
    )


def test_project_pension_returns_horizon_length_series() -> None:
    job = _job_with_pension(
        annual_income=Decimal("109_500"), claim_age_months_value=62 * 12, end_year=2045
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert len(projection.formula) == timeline.horizon_months
    assert len(projection.manual) == timeline.horizon_months
    assert len(projection.stored_total) == timeline.horizon_months


def test_formula_benefit_starts_at_claim_month_and_is_zero_before() -> None:
    claim_age = 62 * 12
    job = _job_with_pension(
        annual_income=Decimal("120_000"), claim_age_months_value=claim_age, end_year=2045
    )
    plan = _plan_with_person1_job(job)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)
    claim_index = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    projection = project_pension(plan, timeline, job_income)

    assert projection.formula[claim_index - 1] == Decimal("0.00")
    assert projection.formula[claim_index] > Decimal("0.00")


def test_trust_factor_scales_formula_benefit() -> None:
    claim_age = 62 * 12
    reduced_trust = Decimal("0.5")
    full_job = _job_with_pension(
        annual_income=Decimal("120_000"), claim_age_months_value=claim_age, end_year=2045
    )
    reduced_job = _job_with_pension(
        annual_income=Decimal("120_000"), claim_age_months_value=claim_age, end_year=2045
    )
    assert reduced_job.pension is not None
    reduced_job.pension.trust_factor = reduced_trust
    full_plan = _plan_with_person1_job(full_job)
    reduced_plan = _plan_with_person1_job(reduced_job)
    full_timeline = Timeline(full_plan, today=date(2026, 1, 1))
    reduced_timeline = Timeline(reduced_plan, today=date(2026, 1, 1))
    claim_index = full_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    full = project_pension(full_plan, full_timeline, project_job_income(full_plan, full_timeline))
    reduced = project_pension(
        reduced_plan, reduced_timeline, project_job_income(reduced_plan, reduced_timeline)
    )

    assert reduced.formula[claim_index] == (
        full.formula[claim_index] * reduced_trust
    ).quantize(Decimal("0.01"))


def test_changing_job_end_changes_service_credit_without_separate_pension_edit() -> None:
    claim_age = 62 * 12
    early_end_job = _job_with_pension(
        annual_income=Decimal("120_000"), claim_age_months_value=claim_age, end_year=2040
    )
    late_end_job = _job_with_pension(
        annual_income=Decimal("120_000"), claim_age_months_value=claim_age, end_year=2045
    )
    early_plan = _plan_with_person1_job(early_end_job)
    late_plan = _plan_with_person1_job(late_end_job)
    early_timeline = Timeline(early_plan, today=date(2026, 1, 1))
    late_timeline = Timeline(late_plan, today=date(2026, 1, 1))
    claim_index = early_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    early = project_pension(early_plan, early_timeline, project_job_income(early_plan, early_timeline))
    late = project_pension(late_plan, late_timeline, project_job_income(late_plan, late_timeline))

    # A longer career => more service credit => higher benefit, with no pension edit.
    assert late.formula[claim_index] > early.formula[claim_index]


def test_manual_income_streams_flow_into_pension_manual() -> None:
    monthly_amount = Decimal("1_500.00")
    plan = _plan_with_person1_job(
        _job_with_pension(annual_income=Decimal("120_000"), claim_age_months_value=62 * 12, end_year=2045)
    )
    plan.manual_income_streams = [
        TimedStream(label="inherited pension", monthly_amount=monthly_amount)
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = project_job_income(plan, timeline)

    projection = project_pension(plan, timeline, job_income)

    assert projection.manual[0] == monthly_amount
    assert projection.stored_total[0] == projection.formula[0] + monthly_amount
```

- [ ] **Step 2: Scaffold and run to a logical red**

Create `packages/domain/domain/pension/__init__.py` with a stub:

```python
# packages/domain/domain/pension/__init__.py
from __future__ import annotations

from decimal import Decimal

from core.models import Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income import JobIncomeProjection


class PensionProjection(BaseModel):
    formula: list[Decimal]
    manual: list[Decimal]
    stored_total: list[Decimal]  # formula + manual; snapshot at projection time


def project_pension(
    plan: Plan, timeline: Timeline, job_income: JobIncomeProjection
) -> PensionProjection:
    raise NotImplementedError
```

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: FAIL with `NotImplementedError`. Confirm logical red.

- [ ] **Step 3: Implement `project_pension`**

```python
from decimal import ROUND_HALF_UP, Decimal

from core.job import Job
from core.models import Household, PersonHousehold, Plan
from core.streams import TimedStream
from core.timeline import Timeline, project_stream

from domain.pension.formula import (
    claim_age_months,
    final_compensation,
    interpolate_age_factor,
    service_credit_years,
)

_CENTS = Decimal("0.01")
_MONTHS_PER_YEAR = Decimal(12)


def _formula_benefit_series(
    *, job: Job, person: PersonHousehold, household: Household, timeline: Timeline
) -> list[Decimal]:
    pension = job.pension
    assert pension is not None
    if not pension.age_factor_table:
        raise ValueError("empty age_factor_table")
    credit = service_credit_years(job=job, timeline=timeline)
    final_comp = final_compensation(job=job, timeline=timeline)
    age = claim_age_months(person=person, claim=pension.claim, household=household)
    factor = interpolate_age_factor(pension.age_factor_table, age)
    annual_benefit = credit * factor * final_comp
    monthly = annual_benefit / _MONTHS_PER_YEAR * pension.trust_factor
    if monthly < 0:
        monthly = Decimal(0)
    stream = TimedStream(
        monthly_amount=monthly,
        start=pension.claim,
        annual_growth_rate=pension.benefit_real_growth_rate,
    )
    return project_stream(stream, timeline)


def project_pension(
    plan: Plan, timeline: Timeline, job_income: JobIncomeProjection
) -> PensionProjection:
    horizon = timeline.horizon_months
    formula = [Decimal("0.00")] * horizon
    household = plan.household
    for person in (household.person1, household.person2):
        for job in person.jobs:
            if job.pension is None:
                continue
            series = _formula_benefit_series(
                job=job, person=person, household=household, timeline=timeline
            )
            formula = [a + b for a, b in zip(formula, series, strict=True)]
    manual = [Decimal("0.00")] * horizon
    for stream in plan.manual_income_streams:
        projected = project_stream(stream, timeline)
        manual = [a + b for a, b in zip(manual, projected, strict=True)]
    stored_total = [f + m for f, m in zip(formula, manual, strict=True)]
    return PensionProjection(formula=formula, manual=manual, stored_total=stored_total)
```

Note: `job_income` is accepted for API symmetry with the other projection functions and forward compatibility; per-job gross is recomputed via `project_job_gross` inside `final_compensation` because `JobIncomeProjection` only carries per-person aggregates. The unused `ROUND_HALF_UP`/`_CENTS` imports are not needed here — remove them if Step 4 flags `F401`.

- [ ] **Step 4: Run tests and lint**

Run: `uv run pytest packages/domain/tests/test_pension.py -v`
Expected: PASS.
Run: `uv run ruff check packages/domain/domain/pension`
Expected: clean (remove any unused imports it reports).

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/pension/__init__.py packages/domain/tests/test_pension.py
git commit -m "feat(domain): project formula and manual pension income"
```

---

## Task 6: Statutory tax tables (`domain/statutory/taxes.py`)

**Files:**

- Create: `packages/domain/domain/statutory/taxes.py`
- Test: `packages/domain/tests/test_taxes.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/domain/tests/test_taxes.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from domain.statutory.taxes import (
    FEDERAL_BRACKETS,
    FEDERAL_STANDARD_DEDUCTION,
    LAST_REVIEWED_YEAR,
    MEDICARE_TAX_RATE,
    SOCIAL_SECURITY_TAX_RATE,
    STALENESS_GRACE_YEARS,
    STATE_BRACKETS,
    is_tax_data_stale,
)


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
```

- [ ] **Step 2: Run tests to verify they fail logically**

Run: `uv run pytest packages/domain/tests/test_taxes.py -v`
Expected: FAIL with `ModuleNotFoundError` for `domain.statutory.taxes`. After Step 3 the failures become logical assertions.

- [ ] **Step 3: Implement the statutory tax module**

Port federal and New York bracket data from legacy
`backend/app/data/taxes.py`, converting legacy thousands values to dollars
(multiply caps, cumulative prior tax, and standard deductions by 1000). Legacy
index `0` = single, `1` = married. California brackets use the current FTB
single/MFJ schedule in the table below (not the legacy port). Top brackets use
`Decimal("Infinity")`.

```python
# packages/domain/domain/statutory/taxes.py
from __future__ import annotations

from decimal import Decimal

from core.models import FilingStatus

# Update procedure: once a year verify each value below against its source URL,
# refresh any that changed, then set LAST_REVIEWED_YEAR to the current year.
LAST_REVIEWED_YEAR = 2026
STALENESS_GRACE_YEARS = 2

SOURCE_NOTES = {
    "federal": "IRS federal brackets + standard deduction (single current set): https://www.irs.gov/filing/federal-income-tax-rates-and-brackets",
    "california": "CA FTB brackets + standard deduction (single current set): https://www.ftb.ca.gov/file/personal/tax-calculator-tables-rates.asp",
    "new_york": "NY DTF brackets + standard deduction (single current set): https://www.tax.ny.gov/pit/file/tax-tables/",
    "fica": "SSA/IRS FICA rates: https://www.ssa.gov/oact/progdata/taxRates.html",
}

# Bracket = (rate, highest_dollar_at_rate, cumulative_prior_tax_in_dollars).
Bracket = tuple[Decimal, Decimal, Decimal]

_INF = Decimal("Infinity")

FEDERAL_STANDARD_DEDUCTION: dict[FilingStatus, Decimal] = {
    "single": Decimal("16_100"),
    "married_filing_jointly": Decimal("32_200"),
}

FEDERAL_BRACKETS: dict[FilingStatus, tuple[Bracket, ...]] = {
    "single": (
        (Decimal("0.10"), Decimal("11_925"), Decimal("0")),
        (Decimal("0.12"), Decimal("48_475"), Decimal("1_193")),
        (Decimal("0.22"), Decimal("103_350"), Decimal("5_579")),
        (Decimal("0.24"), Decimal("197_300"), Decimal("17_651")),
        (Decimal("0.32"), Decimal("250_525"), Decimal("40_199")),
        (Decimal("0.35"), Decimal("626_350"), Decimal("57_231")),
        (Decimal("0.37"), _INF, Decimal("188_770")),
    ),
    "married_filing_jointly": (
        (Decimal("0.10"), Decimal("23_850"), Decimal("0")),
        (Decimal("0.12"), Decimal("96_950"), Decimal("2_385")),
        (Decimal("0.22"), Decimal("206_700"), Decimal("11_157")),
        (Decimal("0.24"), Decimal("394_600"), Decimal("35_302")),
        (Decimal("0.32"), Decimal("501_050"), Decimal("80_398")),
        (Decimal("0.35"), Decimal("751_600"), Decimal("114_462")),
        (Decimal("0.37"), _INF, Decimal("202_154")),
    ),
}

STATE_STANDARD_DEDUCTION: dict[str, dict[FilingStatus, Decimal]] = {
    "California": {"single": Decimal("5_706"), "married_filing_jointly": Decimal("11_412")},
    "New York": {"single": Decimal("8_000"), "married_filing_jointly": Decimal("16_050")},
}

STATE_BRACKETS: dict[str, dict[FilingStatus, tuple[Bracket, ...]]] = {
    "California": {
        "single": (
            (Decimal("0.01"), Decimal("11_079"), Decimal("0")),
            (Decimal("0.02"), Decimal("26_264"), Decimal("110.79")),
            (Decimal("0.04"), Decimal("41_452"), Decimal("414.49")),
            (Decimal("0.06"), Decimal("57_542"), Decimal("1_022.01")),
            (Decimal("0.08"), Decimal("72_724"), Decimal("1_987.41")),
            (Decimal("0.093"), Decimal("371_479"), Decimal("3_201.97")),
            (Decimal("0.103"), Decimal("445_771"), Decimal("30_986.19")),
            (Decimal("0.113"), Decimal("742_953"), Decimal("38_638.26")),
            (Decimal("0.123"), _INF, Decimal("72_219.83")),
        ),
        "married_filing_jointly": (
            (Decimal("0.01"), Decimal("22_158"), Decimal("0")),
            (Decimal("0.02"), Decimal("52_528"), Decimal("221.58")),
            (Decimal("0.04"), Decimal("82_904"), Decimal("828.98")),
            (Decimal("0.06"), Decimal("115_084"), Decimal("2_044.02")),
            (Decimal("0.08"), Decimal("145_448"), Decimal("3_974.82")),
            (Decimal("0.093"), Decimal("742_958"), Decimal("6_403.94")),
            (Decimal("0.103"), Decimal("891_542"), Decimal("61_972.37")),
            (Decimal("0.113"), Decimal("1_485_906"), Decimal("77_276.52")),
            (Decimal("0.123"), _INF, Decimal("144_439.65")),
        ),
    },
    "New York": {
        "single": (
            (Decimal("0.04"), Decimal("8_501"), Decimal("0")),
            (Decimal("0.045"), Decimal("11_701"), Decimal("340")),
            (Decimal("0.0525"), Decimal("13_901"), Decimal("484")),
            (Decimal("0.0585"), Decimal("80_651"), Decimal("599")),
            (Decimal("0.0625"), Decimal("215_401"), Decimal("4_504")),
            (Decimal("0.0685"), Decimal("1_077_551"), Decimal("12_926")),
            (Decimal("0.0965"), Decimal("5_000_001"), Decimal("71_983")),
            (Decimal("0.103"), Decimal("25_000_001"), Decimal("450_499")),
            (Decimal("0.109"), _INF, Decimal("2_510_499")),
        ),
        "married_filing_jointly": (
            (Decimal("0.04"), Decimal("17_151"), Decimal("0")),
            (Decimal("0.045"), Decimal("23_601"), Decimal("686")),
            (Decimal("0.0525"), Decimal("27_901"), Decimal("976")),
            (Decimal("0.0585"), Decimal("161_551"), Decimal("1_202")),
            (Decimal("0.0625"), Decimal("323_201"), Decimal("9_021")),
            (Decimal("0.0685"), Decimal("2_155_351"), Decimal("19_124")),
            (Decimal("0.0965"), Decimal("5_000_001"), Decimal("144_626")),
            (Decimal("0.103"), Decimal("25_000_001"), Decimal("419_135")),
            (Decimal("0.109"), _INF, Decimal("2_479_135")),
        ),
    },
}

MEDICARE_TAX_RATE = Decimal("0.0145")
SOCIAL_SECURITY_TAX_RATE = Decimal("0.062")


def is_tax_data_stale(current_year: int) -> bool:
    """Soft annual-review reminder for the tax statutory tables."""
    return current_year - LAST_REVIEWED_YEAR >= STALENESS_GRACE_YEARS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_taxes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/statutory/taxes.py packages/domain/tests/test_taxes.py
git commit -m "feat(domain): add federal, CA, NY tax statutory tables"
```

---

## Task 7: Bracket math (`domain/taxes/brackets.py`)

**Files:**

- Create: `packages/domain/domain/taxes/brackets.py`
- Test: `packages/domain/tests/test_taxes.py` (append)

- [ ] **Step 1: Write the failing tests (append to `test_taxes.py`)**

```python
from domain.statutory.taxes import FEDERAL_BRACKETS, FEDERAL_STANDARD_DEDUCTION
from domain.taxes.brackets import annual_income_tax, progressive_tax


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
```

- [ ] **Step 2: Scaffold and run to a logical red**

```python
# packages/domain/domain/taxes/brackets.py
from __future__ import annotations

from decimal import Decimal

from domain.statutory.taxes import Bracket


def progressive_tax(brackets: tuple[Bracket, ...], taxable_income: Decimal) -> Decimal:
    raise NotImplementedError


def annual_income_tax(
    *,
    brackets: tuple[Bracket, ...],
    standard_deduction: Decimal,
    annual_income: Decimal,
) -> Decimal:
    raise NotImplementedError
```

Run: `uv run pytest packages/domain/tests/test_taxes.py -k "progressive or annual_income_tax" -v`
Expected: FAIL with `NotImplementedError`. Confirm logical red.

- [ ] **Step 3: Implement the bracket math**

```python
from decimal import ROUND_HALF_UP, Decimal

_CENTS = Decimal("0.01")


def progressive_tax(brackets: tuple[Bracket, ...], taxable_income: Decimal) -> Decimal:
    """Tax owed (positive) on `taxable_income` in dollars."""
    if taxable_income <= 0:
        return Decimal("0.00")
    previous_cap = Decimal(0)
    for rate, cap, cumulative_prior in brackets:
        if taxable_income < cap:
            return (cumulative_prior + rate * (taxable_income - previous_cap)).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )
        previous_cap = cap
    raise ValueError("annual taxable income exceeds the highest tax bracket")


def annual_income_tax(
    *,
    brackets: tuple[Bracket, ...],
    standard_deduction: Decimal,
    annual_income: Decimal,
) -> Decimal:
    taxable = annual_income - standard_deduction
    if taxable <= 0:
        return Decimal("0.00")
    return progressive_tax(brackets, taxable)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_taxes.py -k "progressive or annual_income_tax" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/taxes/brackets.py packages/domain/tests/test_taxes.py
git commit -m "feat(domain): add progressive bracket tax math"
```

---

## Task 8: Tax computation (`domain/taxes/__init__.py`)

**Files:**

- Create: `packages/domain/domain/taxes/__init__.py`
- Test: `packages/domain/tests/test_taxes.py` (append)

- [ ] **Step 1: Write the failing tests (append to `test_taxes.py`)**

```python
from core.defaults import default_plan
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection, PersonJobIncome
from domain.pension import PensionProjection
from domain.social_security import PersonSocialSecurity, SocialSecurityProjection
from domain.statutory.social_security import (
    SS_MAX_EARNINGS_BY_YEAR,
    statutory_value_for_year,
)
from domain.taxes import TaxBreakdown, compute_taxes


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
        gross=_zeros(horizon), ss_covered_gross=_zeros(horizon), tax_deferred=_zeros(horizon)
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
    return SocialSecurityProjection(person1=person, person2=person, total=_zeros(horizon))


def _zero_pension(horizon: int) -> PensionProjection:
    zeroes = _zeros(horizon)
    return PensionProjection(formula=zeroes, manual=zeroes, stored_total=zeroes)


def _plan(*, filing_status: str = "married_filing_jointly", residence_state: str | None = None) -> Plan:
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
        brackets=fed_brackets, standard_deduction=fed_deduction, annual_income=year_total
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
    assert breakdown.federal_income[0] == (breakdown.federal_income[1] * Decimal(3)).quantize(
        Decimal("0.01")
    )


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
        plan=single_plan, timeline=single_timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
    )
    mfj = compute_taxes(
        plan=mfj_plan, timeline=mfj_timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
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
        plan=plan, timeline=timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
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
    expected_year_one = -(SOCIAL_SECURITY_TAX_RATE * wage_base).quantize(Decimal("0.01"))

    breakdown = compute_taxes(
        plan=plan, timeline=timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
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
        plan=plan, timeline=timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
    )
    california = compute_taxes(
        plan=ca_plan, timeline=ca_timeline, job_income=job_income,
        social_security=_zero_ss(horizon), pension=_zero_pension(horizon),
    )

    assert all(s == Decimal("0.00") for s in no_state.state_income)
    assert california.state_income[0] < Decimal("0")
```

- [ ] **Step 2: Scaffold and run to a logical red**

```python
# packages/domain/domain/taxes/__init__.py
from __future__ import annotations

from decimal import Decimal

from core.models import Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income import JobIncomeProjection
from domain.pension import PensionProjection
from domain.social_security import SocialSecurityProjection


class TaxBreakdown(BaseModel):
    federal_income: list[Decimal]
    state_income: list[Decimal]
    fica_medicare: list[Decimal]
    fica_social_security: list[Decimal]
    stored_total: list[Decimal]  # sum of components; snapshot at compute time


def compute_taxes(
    *,
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
    social_security: SocialSecurityProjection,
    pension: PensionProjection,
) -> TaxBreakdown:
    raise NotImplementedError
```

Run: `uv run pytest packages/domain/tests/test_taxes.py -k "fica or federal or filing or taxable_fraction or state or negative" -v`
Expected: FAIL with `NotImplementedError`. Confirm logical red.

- [ ] **Step 3: Implement `compute_taxes`**

```python
from decimal import ROUND_HALF_UP, Decimal

from domain.statutory.social_security import (
    SS_MAX_EARNINGS_BY_YEAR,
    statutory_value_for_year,
)
from domain.statutory.taxes import (
    FEDERAL_BRACKETS,
    FEDERAL_STANDARD_DEDUCTION,
    MEDICARE_TAX_RATE,
    SOCIAL_SECURITY_TAX_RATE,
    STATE_BRACKETS,
    STATE_STANDARD_DEDUCTION,
)
from domain.taxes.brackets import annual_income_tax

_CENTS = Decimal("0.01")


def _indices_by_year(timeline: Timeline) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for month_index in range(timeline.horizon_months):
        year = timeline.month_boundary(month_index).year
        grouped.setdefault(year, []).append(month_index)
    return grouped


def _fica_social_security(
    job_income: JobIncomeProjection, timeline: Timeline
) -> list[Decimal]:
    horizon = timeline.horizon_months
    wage_base = statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, timeline.today.year)
    person_series = (
        job_income.person1.ss_covered_gross,
        job_income.person2.ss_covered_gross,
    )
    series = [Decimal("0.00")] * horizon
    cumulative: dict[tuple[int, int], Decimal] = {}
    for month_index in range(horizon):
        year = timeline.month_boundary(month_index).year
        month_tax = Decimal(0)
        for person_idx, covered in enumerate(person_series):
            key = (person_idx, year)
            accrued = cumulative.get(key, Decimal(0))
            remaining = max(wage_base - accrued, Decimal(0))
            taxable = min(covered[month_index], remaining)
            month_tax += SOCIAL_SECURITY_TAX_RATE * taxable
            cumulative[key] = accrued + covered[month_index]
        series[month_index] = -month_tax.quantize(_CENTS, rounding=ROUND_HALF_UP)
    return series


def compute_taxes(
    *,
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
    social_security: SocialSecurityProjection,
    pension: PensionProjection,
) -> TaxBreakdown:
    horizon = timeline.horizon_months
    if horizon <= 0:
        return TaxBreakdown(
            federal_income=[],
            state_income=[],
            fica_medicare=[],
            fica_social_security=[],
            stored_total=[],
        )

    household = plan.household
    filing = household.filing_status
    ss_pension_fraction = household.ss_pension_taxable_fraction
    state = household.residence_state

    job_taxable = [
        gross - deferred
        for gross, deferred in zip(
            job_income.total_gross, job_income.total_tax_deferred, strict=True
        )
    ]
    total_taxable = [
        job_taxable[m]
        + (social_security.total[m] + pension.stored_total[m]) * ss_pension_fraction
        for m in range(horizon)
    ]

    fed_brackets = FEDERAL_BRACKETS[filing]
    fed_deduction = FEDERAL_STANDARD_DEDUCTION[filing]
    state_brackets = STATE_BRACKETS.get(state, {}).get(filing) if state else None
    state_deduction = (
        STATE_STANDARD_DEDUCTION.get(state, {}).get(filing, Decimal(0))
        if state
        else Decimal(0)
    )

    federal = [Decimal("0.00")] * horizon
    state_income = [Decimal("0.00")] * horizon
    for indices in _indices_by_year(timeline).values():
        year_taxable = sum((total_taxable[m] for m in indices), Decimal(0))
        if year_taxable <= 0:
            continue
        year_federal = annual_income_tax(
            brackets=fed_brackets,
            standard_deduction=fed_deduction,
            annual_income=year_taxable,
        )
        year_state = (
            annual_income_tax(
                brackets=state_brackets,
                standard_deduction=state_deduction,
                annual_income=year_taxable,
            )
            if state_brackets is not None
            else Decimal("0.00")
        )
        for month_index in indices:
            share = total_taxable[month_index] / year_taxable
            federal[month_index] = -(year_federal * share).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )
            state_income[month_index] = -(year_state * share).quantize(
                _CENTS, rounding=ROUND_HALF_UP
            )

    medicare = [
        -(MEDICARE_TAX_RATE * gross).quantize(_CENTS, rounding=ROUND_HALF_UP)
        for gross in job_income.total_gross
    ]
    fica_social_security = _fica_social_security(job_income, timeline)
    stored_total = [
        f + s + m + ss
        for f, s, m, ss in zip(
            federal, state_income, medicare, fica_social_security, strict=True
        )
    ]

    return TaxBreakdown(
        federal_income=federal,
        state_income=state_income,
        fica_medicare=medicare,
        fica_social_security=fica_social_security,
        stored_total=stored_total,
    )
```

Note: SS payroll tax applies to SS-*covered* wages, so `_fica_social_security` uses each person's `ss_covered_gross`. The wage-base cap is the current real (today's-year) statutory maximum applied to every projected calendar year, consistent with the real today's-dollars convention.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_taxes.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/taxes/__init__.py packages/domain/tests/test_taxes.py
git commit -m "feat(domain): compute income-side taxes with annual aggregation"
```

---

## Task 9: Cashflow aggregator (`domain/__init__.py`)

**Files:**

- Modify: `packages/domain/domain/__init__.py`
- Test: `packages/domain/tests/test_cashflows.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/domain/tests/test_cashflows.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import FormulaPension, Job, SabbaticalWindow
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, TimedStream
from core.timeline import Timeline
from domain import MonthlyCashflows, build_monthly_cashflows
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)


def _working_plan() -> Plan:
    base = default_plan()
    job = Job(
        annual_income=Decimal("120_000"),
        end=CalendarMonthBoundary(year=2045, month=12),
    )
    person1 = PersonHousehold(
        birth_month=1, birth_year=1983, jobs=[job],
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
                SabbaticalWindow(start=break_start, end=break_end, remaining_fraction=Decimal("0"))
            ],
        )
    )

    no_break_cashflows = build_monthly_cashflows(no_break, today=today)
    with_break_cashflows = build_monthly_cashflows(with_break, today=today)

    # During the sabbatical year the lower taxable income means lower (less negative) tax.
    sabbatical_month = Timeline(with_break, today=today).index_of(break_start)
    assert with_break_cashflows.taxes.stored_total[sabbatical_month] > (
        no_break_cashflows.taxes.stored_total[sabbatical_month]
    )
```

- [ ] **Step 2: Scaffold and run to a logical red**

Replace the contents of `packages/domain/domain/__init__.py`:

```python
"""Income, pension, Social Security, and tax domain logic."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.models import Plan
from core.timeline import Timeline
from pydantic import BaseModel

from domain.job_income import project_job_income
from domain.pension import project_pension
from domain.social_security import project_social_security
from domain.taxes import TaxBreakdown, compute_taxes


class MonthlyCashflows(BaseModel):
    gross_job: list[Decimal]
    gross_social_security: list[Decimal]
    gross_pension: list[Decimal]
    gross_manual: list[Decimal]
    total_gross: list[Decimal]
    taxes: TaxBreakdown
    net_cashflow: list[Decimal]


def build_monthly_cashflows(
    plan: Plan, *, today: date | None = None
) -> MonthlyCashflows:
    raise NotImplementedError
```

Run: `uv run pytest packages/domain/tests/test_cashflows.py -v`
Expected: FAIL with `NotImplementedError`. Confirm logical red.

- [ ] **Step 3: Implement `build_monthly_cashflows`**

```python
def build_monthly_cashflows(
    plan: Plan, *, today: date | None = None
) -> MonthlyCashflows:
    timeline = Timeline(plan, today=today)
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

    gross_job = job_income.total_gross
    gross_social_security = social_security.total
    gross_pension = pension.formula
    gross_manual = pension.manual
    total_gross = [
        gross_job[m]
        + gross_social_security[m]
        + gross_pension[m]
        + gross_manual[m]
        for m in range(timeline.horizon_months)
    ]
    net_cashflow = [
        total + tax for total, tax in zip(total_gross, taxes.stored_total, strict=True)
    ]

    return MonthlyCashflows(
        gross_job=gross_job,
        gross_social_security=gross_social_security,
        gross_pension=gross_pension,
        gross_manual=gross_manual,
        total_gross=total_gross,
        taxes=taxes,
        net_cashflow=net_cashflow,
    )
```

Note: `gross_pension` maps to `pension.formula` and `gross_manual` to `pension.manual` so manual income is counted exactly once in `total_gross`, while `compute_taxes` still uses `pension.stored_total` (formula + manual) for the SS/pension taxable base.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest packages/domain/tests/test_cashflows.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/__init__.py packages/domain/tests/test_cashflows.py
git commit -m "feat(domain): add build_monthly_cashflows aggregator"
```

---

## Task 10: Documentation, index, and final verification

**Files:**

- Modify: `packages/domain/OVERVIEW.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Modify: `docs/superpowers/specs/2026-06-25-phase-2d-domain-pension-taxes-design.md`
- Modify: `docs/superpowers/plans/2026-06-12-phase-2d-domain-pension-taxes.md` (this file)

- [ ] **Step 1: Update the domain overview**

In `packages/domain/OVERVIEW.md`, change the three Phase 2d rows to `done`:

```markdown
| `pension.py` | `domain/pension/` | 2d | done |
| `taxes.py` (income-side) | `domain/taxes/` | 2d | done |
| `build_monthly_cashflows(plan)` aggregator | `domain/__init__.py` | 2d | done |
```

- [ ] **Step 2: Update the rebuild index**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, update the active phase table to point to Phase 2e:

```markdown
| **Current phase** | Phase 2e — plan |
| **Active plan** | *(to write)* `2026-06-12-phase-2e-domain-single-household.md` |
| **Next action** | Write Phase 2e plan before coding |
```

Set each Phase 2d exit-criteria checkbox to `[x]`, and add Phase 2d to the completed plans table:

```markdown
| Phase 2d | `2026-06-12-phase-2d-domain-pension-taxes.md` | complete |
```

- [ ] **Step 3: Mark the spec and this plan complete**

In `docs/superpowers/specs/2026-06-25-phase-2d-domain-pension-taxes-design.md`, set each exit-criteria checkbox in §9 to `[x]`.

At the top of this plan file, add the status line under the title:

```markdown
**Status:** Complete
```

- [ ] **Step 4: Run full verification**

Run: `make`
Expected: PASS for ruff lint, ruff format check, pyright, and pytest.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/OVERVIEW.md docs/superpowers/plans/2026-06-12-rebuild-index.md docs/superpowers/specs/2026-06-25-phase-2d-domain-pension-taxes-design.md docs/superpowers/plans/2026-06-12-phase-2d-domain-pension-taxes.md
git commit -m "docs(domain): complete Phase 2d pension and taxes"
```

---

## Self-Review Checklist

**Spec coverage (spec §-by-§):**

- §3 `FormulaPension`/`AgeFactor` on `Job`: Task 2.
- §3 statutory CalSTRS age-factor table in `domain/statutory/pension.py`: Task 3.
- §3 service credit / final compensation / age-factor interpolation: Task 4.
- §3 `project_pension` formula benefit stream + manual path + single source of truth: Task 5.
- §4 `Household.filing_status`, `residence_state`, `ss_pension_taxable_fraction`: Task 1.
- §4 statutory tax tables + staleness: Task 6.
- §4 progressive bracket math: Task 7.
- §4 `compute_taxes` annual aggregation + monthly distribution + FICA + state + sign: Task 8.
- §5 `MonthlyCashflows` + `build_monthly_cashflows`: Task 9.
- §6 file layout: Tasks 1–9 create the listed files.
- §7 error handling: job-without-end `ValueError` (Task 4), empty age-factor table `ValueError` (Tasks 4–5), bracket-overflow `ValueError` (Task 7), clamped age extrapolation (Task 4), validation errors (Tasks 1–2), empty horizon → empty lists (Tasks 8–9).
- §8 testing highlights: covered across Tasks 1–9.
- §9 exit criteria + OVERVIEW + index: Task 10.

**Type / name consistency:**

- Config: `AgeFactor`, `FormulaPension`, `Job.pension`, `FilingStatus`, `Household.filing_status`, `Household.residence_state`, `Household.ss_pension_taxable_fraction`.
- Statutory: `CALSTRS_2_AT_62_AGE_FACTORS`, `age_factors_from_statutory`, `FEDERAL_BRACKETS`, `FEDERAL_STANDARD_DEDUCTION`, `STATE_BRACKETS`, `STATE_STANDARD_DEDUCTION`, `MEDICARE_TAX_RATE`, `SOCIAL_SECURITY_TAX_RATE`, `is_tax_data_stale`, `Bracket`.
- Pension: `service_credit_years`, `final_compensation`, `interpolate_age_factor`, `claim_age_months`, `PensionProjection(formula, manual, stored_total)`, `project_pension(plan, timeline, job_income)`.
- Taxes: `progressive_tax`, `annual_income_tax`, `TaxBreakdown(federal_income, state_income, fica_medicare, fica_social_security, stored_total)`, `compute_taxes(*, plan, timeline, job_income, social_security, pension)`.
- Aggregator: `MonthlyCashflows`, `build_monthly_cashflows(plan, *, today=None)`.

**Decimal / sign conventions:**

- All money is `Decimal`; benefit and tax series quantize to cents with `ROUND_HALF_UP`.
- Tax components and `TaxBreakdown.stored_total` are negative; `net_cashflow = total_gross + taxes.stored_total`.

**Layering:**

- `core` never imports `domain` (age-factor default resolved by `domain/statutory`, not `core`).
- `domain/statutory/taxes.py` imports `FilingStatus` from `core.models` (domain → core, allowed).

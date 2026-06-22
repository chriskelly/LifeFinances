# Phase 2b — Domain: Job Income Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port legacy job income onto the Phase 2a `TimedStream` foundation: per-person multiple jobs with raises and per-job sabbatical windows, compiled into month-indexed `JobIncomeProjection` series for downstream phases.

**Architecture:** Config models (`Job`, `SabbaticalWindow`) live in `core` and persist on `PersonHousehold.jobs` via the existing JSON-blob repository. Sabbatical-window structure is validated by a `Household` Pydantic validator using a birth-date-only boundary resolver (no `today`). The `domain.job_income` package compiles each job into re-anchored `TimedStream` segments, reuses `core.timeline.project_stream` for growth, and aggregates per-person `gross` / `ss_covered_gross` / `tax_deferred` plus household totals.

**Tech Stack:** Python 3.14, Pydantic v2, `Decimal` money math, pytest, uv workspace. Spec: `docs/superpowers/specs/2026-06-12-phase-2b-domain-job-income-design.md`.

**Conventions for every task:**

- Follow TDD: write the behavior test, scaffold to a *logical* red (`NotImplementedError`/stub), confirm the failure is logical (not `ImportError`/`AttributeError`), implement, confirm green.
- Inject `today: date`; never read wall-clock time in logic or assertions.
- Bind shared values to a variable referenced in both arrange and assert; import constants/defaults from source instead of copying literals.
- Run developer commands from the **repository root** (`LifeFInances/`).
- Single test: `uv run pytest <path>::<test_name> -v`. Each task's final commit triggers the pre-commit hook which runs `make` (full build + lint + test).

---

## File Structure

`**packages/core/`**

- `core/job.py` *(new)* — `Job`, `SabbaticalWindow` models + `Job` model-level validator (`annual_tax_deferred <= annual_income`).
- `core/models.py` *(modify)* — add `PersonHousehold.jobs`; add `Household` sabbatical-window validator.
- `core/timeline.py` *(modify)* — add `boundary_to_year_month()`; refactor `Timeline.index_of` to reuse it; add `Timeline.month_boundary()`; move the `core.models` import under `TYPE_CHECKING` to break the new `models → timeline` cycle.
- `tests/test_job.py` *(new)* — `Job` validation, `Household` window validation, repository round-trip.
- `tests/test_timeline.py` *(modify)* — `boundary_to_year_month` + `month_boundary` behavior.

`**packages/domain/*`*

- `domain/job_income/__init__.py` *(new)* — `PersonJobIncome`, `JobIncomeProjection`, `project_job_income()`.
- `domain/job_income/compile.py` *(new)* — `project_job_gross()` (segment split + re-anchoring + projection).
- `tests/test_job_income.py` *(new)* — compilation and projection behaviors.
- `OVERVIEW.md` *(modify)* — job-income port status.

`**docs/superpowers/plans/2026-06-12-rebuild-index.md*`* *(modify)* — active-phase pointer at the end.

---

## Task 1: `Job` and `SabbaticalWindow` config models

**Files:**

- Create: `packages/core/core/job.py`
- Test: `packages/core/tests/test_job.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/core/tests/test_job.py
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from core.job import Job


def test_job_rejects_tax_deferred_above_income() -> None:
    income = Decimal("100000")
    too_much_deferred = income + Decimal("1")

    with pytest.raises(ValidationError):
        Job(annual_income=income, annual_tax_deferred=too_much_deferred)


def test_job_allows_tax_deferred_equal_to_income() -> None:
    income = Decimal("100000")

    job = Job(annual_income=income, annual_tax_deferred=income)

    assert job.annual_tax_deferred == income
```

- [ ] **Step 2: Scaffold to a logical red**

Create `packages/core/core/job.py` with the models but a deliberately wrong/missing cross-field check so the first test fails on assertion, not import:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from core.streams import Boundary


class SabbaticalWindow(BaseModel):
    """A window over which a job's pay is reduced (or fully paused).

    remaining_fraction is the share of pay still earned: 0 => full break,
    0.5 => half pay, 1 => no reduction. The job's underlying raise clock keeps
    running across the window, so the person returns at the grown salary.
    """

    start: Boundary
    end: Boundary
    remaining_fraction: Decimal = Field(ge=0, le=1)


class Job(BaseModel):
    """One job held by a person, as a real (today's-dollar) income source.

    Amounts are annual; the domain compiles them to a monthly TimedStream.
    annual_raise is a REAL raise (growth above inflation). Inflation is never
    applied here.
    """

    label: str | None = None
    annual_income: Decimal = Field(ge=0)
    annual_tax_deferred: Decimal = Field(default=Decimal(0), ge=0)
    annual_raise: Decimal = Decimal(0)
    start: Boundary | None = None
    end: Boundary | None = None
    social_security_eligible: bool = True
    sabbaticals: list[SabbaticalWindow] = Field(default_factory=list)
```

- [ ] **Step 3: Run test to verify it fails logically**

Run: `uv run pytest packages/core/tests/test_job.py::test_job_rejects_tax_deferred_above_income -v`
Expected: FAIL — `DID NOT RAISE ValidationError` (logical, not an import error).

- [ ] **Step 4: Implement the cross-field validator**

Add to `Job` in `packages/core/core/job.py`:

```python
from pydantic import BaseModel, Field, model_validator
```

```python
    @model_validator(mode="after")
    def _tax_deferred_within_income(self) -> "Job":
        if self.annual_tax_deferred > self.annual_income:
            raise ValueError("annual_tax_deferred must not exceed annual_income")
        return self
```

- [ ] **Step 5: Run both tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_job.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/job.py packages/core/tests/test_job.py
git commit -m "feat(core): add Job and SabbaticalWindow config models"
```

---

## Task 2: Persist `jobs` on `PersonHousehold`

**Files:**

- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_job.py`

- [ ] **Step 1: Write the failing round-trip test**

Append to `packages/core/tests/test_job.py`:

```python
from datetime import date

from core.defaults import default_plan
from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary


def test_plan_with_jobs_round_trips_through_repository(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    annual_income = Decimal("120000")
    job = Job(
        label="Engineer",
        annual_income=annual_income,
        annual_tax_deferred=Decimal("23000"),
        annual_raise=Decimal("0.03"),
        end=CalendarMonthBoundary(year=date.today().year + 30, month=1),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=date.today().year + 5, month=1),
                end=CalendarMonthBoundary(year=date.today().year + 5, month=12),
                remaining_fraction=Decimal("0.5"),
            )
        ],
    )
    plan.household.person1.jobs.append(job)

    repo.save(plan_id, plan)
    reloaded = repo.get_by_id(plan_id)

    assert reloaded is not None
    assert reloaded.household.person1.jobs == plan.household.person1.jobs
    assert reloaded.household.person1.jobs[0].annual_income == annual_income
```

> The `repo` fixture comes from the repo-root `conftest.py`.

- [ ] **Step 2: Run test to verify it fails logically**

Run: `uv run pytest packages/core/tests/test_job.py::test_plan_with_jobs_round_trips_through_repository -v`
Expected: FAIL — `AttributeError: 'PersonHousehold' object has no attribute 'jobs'` is structural; if you see it, that is the cue to add the field (Step 3), then it should fail logically only if the field is wrong. (Adding the field is minimal scaffolding here.)

- [ ] **Step 3: Add the field**

Modify `packages/core/core/models.py`:

```python
from core.job import Job
from core.streams import TimedStream
```

```python
class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_job.py::test_plan_with_jobs_round_trips_through_repository -v`
Expected: PASS.

- [ ] **Step 5: Confirm default plan + existing core tests still pass**

Run: `uv run pytest packages/core -v`
Expected: PASS (all green, including existing `test_repository`, `test_streams`, `test_timeline`).

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_job.py
git commit -m "feat(core): persist jobs on PersonHousehold"
```

---

## Task 3: `boundary_to_year_month` resolver + break the import cycle

**Files:**

- Modify: `packages/core/core/timeline.py`
- Test: `packages/core/tests/test_timeline.py`

**Why:** The `Household` validator (Task 5) must resolve any boundary to an absolute `(year, month)` using birth dates only. That logic belongs in `core.timeline` and must be importable from `core.models` — so `timeline`'s runtime import of `core.models` is moved under `TYPE_CHECKING`.

- [ ] **Step 1: Write the failing tests**

Append to `packages/core/tests/test_timeline.py`:

```python
from core.timeline import boundary_to_year_month


def test_boundary_to_year_month_calendar_is_identity() -> None:
    year, month = 2031, 7

    result = boundary_to_year_month(
        CalendarMonthBoundary(year=year, month=month), default_plan().household
    )

    assert result == (year, month)


def test_boundary_to_year_month_person_age_uses_birth_plus_age() -> None:
    household = default_plan().household
    person = household.person1
    age_months = 600  # 50 years

    result = boundary_to_year_month(
        PersonAgeBoundary(person="person1", age_months=age_months), household
    )

    assert result == (person.birth_year + age_months // 12, person.birth_month)
```

- [ ] **Step 2: Scaffold to a logical red**

In `packages/core/core/timeline.py`, add a stub (keep existing code intact for now):

```python
def boundary_to_year_month(boundary: Boundary, household: Household) -> tuple[int, int]:
    raise NotImplementedError
```

> `Household` is only referenced in the annotation; with `from __future__ import annotations` it is a string at runtime.

- [ ] **Step 3: Run tests to verify logical failure**

Run: `uv run pytest packages/core/tests/test_timeline.py::test_boundary_to_year_month_calendar_is_identity -v`
Expected: FAIL with `NotImplementedError` (logical).

- [ ] **Step 4: Implement the resolver, refactor `index_of`, and move the import**

In `packages/core/core/timeline.py`:

1. Replace the top-of-file `core.models` import with a `TYPE_CHECKING` block:

```python
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from core.streams import (
    Boundary,
    CalendarMonthBoundary,
    PersonAgeBoundary,
    TimedStream,
)

if TYPE_CHECKING:
    from core.models import Household, PersonHousehold, Plan
```

1. Implement the resolver:

```python
def boundary_to_year_month(boundary: Boundary, household: Household) -> tuple[int, int]:
    """Resolve a boundary to an absolute (year, month). Birth-date only; no `today`."""
    if isinstance(boundary, CalendarMonthBoundary):
        return boundary.year, boundary.month
    if isinstance(boundary, PersonAgeBoundary):
        person = getattr(household, boundary.person)
        return add_months(person.birth_year, person.birth_month, boundary.age_months)
    raise TypeError(f"Unknown boundary: {boundary!r}")
```

1. Refactor `Timeline.index_of` to delegate:

```python
    def index_of(self, boundary: Boundary) -> int:
        year, month = boundary_to_year_month(boundary, self.plan.household)
        return self._offset(year, month)
```

- [ ] **Step 5: Run timeline + full core tests**

Run: `uv run pytest packages/core/tests/test_timeline.py -v`
Then: `uv run pytest packages/core -v`
Expected: PASS (existing `index_of` tests still pass via the delegated path).

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_timeline.py
git commit -m "feat(core): add boundary_to_year_month resolver and reuse in index_of"
```

---

## Task 4: `Timeline.month_boundary` (inverse of the offset)

**Files:**

- Modify: `packages/core/core/timeline.py`
- Test: `packages/core/tests/test_timeline.py`

- [ ] **Step 1: Write the failing test**

Append to `packages/core/tests/test_timeline.py`:

```python
def test_month_boundary_is_inverse_of_index_of() -> None:
    timeline = Timeline(default_plan(), today=date(2026, 6, 1))
    index = 19

    boundary = timeline.month_boundary(index)

    assert isinstance(boundary, CalendarMonthBoundary)
    assert timeline.index_of(boundary) == index
```

- [ ] **Step 2: Scaffold to a logical red**

Add to the `Timeline` class:

```python
    def month_boundary(self, index: int) -> CalendarMonthBoundary:
        raise NotImplementedError
```

- [ ] **Step 3: Run test to verify logical failure**

Run: `uv run pytest packages/core/tests/test_timeline.py::test_month_boundary_is_inverse_of_index_of -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement**

```python
    def month_boundary(self, index: int) -> CalendarMonthBoundary:
        """The calendar month at `index` months from today (index 0 == this month)."""
        year, month = add_months(self.today.year, self.today.month, index)
        return CalendarMonthBoundary(year=year, month=month)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_timeline.py::test_month_boundary_is_inverse_of_index_of -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_timeline.py
git commit -m "feat(core): add Timeline.month_boundary"
```

---

## Task 5: `Household` sabbatical-window validator

**Files:**

- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_job.py`

**Behavior:** For each person's each job, resolve boundaries to absolute `year*12 + month` and require: each window `start <= end`; windows strictly ordered and non-overlapping (`next.start > prev.end`, inclusive months); each window within the job's **explicit** bounds (open `None` bounds are not enforced).

- [ ] **Step 1: Write the failing tests**

Append to `packages/core/tests/test_job.py`:

```python
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.streams import PersonAgeBoundary


def _household_with_person1_jobs(jobs: list[Job]) -> Household:
    return Household(
        person1=PersonHousehold(birth_month=1, birth_year=1980, jobs=jobs),
        person2=PersonHousehold(birth_month=1, birth_year=1982),
    )


def test_overlapping_sabbatical_windows_rejected() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=1),
                end=CalendarMonthBoundary(year=2030, month=6),
                remaining_fraction=Decimal("0.5"),
            ),
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=6),
                end=CalendarMonthBoundary(year=2030, month=12),
                remaining_fraction=Decimal("0"),
            ),
        ],
    )

    with pytest.raises(ValidationError):
        _household_with_person1_jobs([job])


def test_window_outside_explicit_job_bounds_rejected() -> None:
    job_start_year = 2030
    job = Job(
        annual_income=Decimal("100000"),
        start=CalendarMonthBoundary(year=job_start_year, month=1),
        end=CalendarMonthBoundary(year=job_start_year + 5, month=12),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=job_start_year - 1, month=1),
                end=CalendarMonthBoundary(year=job_start_year - 1, month=6),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    with pytest.raises(ValidationError):
        _household_with_person1_jobs([job])


def test_window_against_open_bound_is_accepted() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=PersonAgeBoundary(person="person1", age_months=720),
                end=PersonAgeBoundary(person="person1", age_months=732),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    household = _household_with_person1_jobs([job])

    assert household.person1.jobs[0].sabbaticals[0].remaining_fraction == Decimal("0")


def test_cross_person_and_mixed_boundary_kinds_resolve() -> None:
    # window bounded by a calendar start and person2's age — both must resolve
    job = Job(
        annual_income=Decimal("100000"),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2030, month=1),
                end=PersonAgeBoundary(person="person2", age_months=720),  # person2 born 1982 -> 2042
                remaining_fraction=Decimal("0.5"),
            )
        ],
    )

    household = _household_with_person1_jobs([job])

    assert len(household.person1.jobs[0].sabbaticals) == 1
```

- [ ] **Step 2: Scaffold to a logical red**

Add the validator skeleton + helper to `packages/core/core/models.py` (import the resolver — now safe per Task 3):

```python
from pydantic import BaseModel, Field, model_validator

from core.job import Job
from core.streams import TimedStream
from core.timeline import boundary_to_year_month
```

```python
def _validate_job_windows(job: "Job", household: "Household") -> None:
    raise NotImplementedError


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> "Household":
        for person in (self.person1, self.person2):
            for job in person.jobs:
                _validate_job_windows(job, self)
        return self
```

- [ ] **Step 3: Run tests to verify logical failure**

Run: `uv run pytest packages/core/tests/test_job.py::test_window_against_open_bound_is_accepted -v`
Expected: FAIL — `NotImplementedError` wrapped in `ValidationError` (logical). The two "rejected" tests will pass for the wrong reason at this point; the accepting/resolving tests prove the implementation in Step 5.

- [ ] **Step 4: Implement `_validate_job_windows`**

```python
def _validate_job_windows(job: "Job", household: "Household") -> None:
    def absolute(boundary) -> int:
        year, month = boundary_to_year_month(boundary, household)
        return year * 12 + month

    low = absolute(job.start) if job.start is not None else None
    high = absolute(job.end) if job.end is not None else None

    previous_end: int | None = None
    for window in job.sabbaticals:
        start = absolute(window.start)
        end = absolute(window.end)
        if start > end:
            raise ValueError("sabbatical window start must not be after its end")
        if low is not None and start < low:
            raise ValueError("sabbatical window starts before the job's start")
        if high is not None and end > high:
            raise ValueError("sabbatical window ends after the job's end")
        if previous_end is not None and start <= previous_end:
            raise ValueError("sabbatical windows must be ordered and non-overlapping")
        previous_end = end
```

- [ ] **Step 5: Run the window tests and full core suite**

Run: `uv run pytest packages/core/tests/test_job.py -v`
Then: `uv run pytest packages/core -v`
Expected: PASS (all). Confirm `test_window_against_open_bound_is_accepted` and `test_cross_person_and_mixed_boundary_kinds_resolve` now pass via real logic.

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_job.py
git commit -m "feat(core): validate sabbatical windows on Household"
```

---

## Task 6: Compile a job into a projected gross series

**Files:**

- Create: `packages/domain/domain/job_income/__init__.py` (empty package marker for now — a docstring only)
- Create: `packages/domain/domain/job_income/compile.py`
- Test: `packages/domain/tests/test_job_income.py`

**Approach:** Split the job window at sabbatical boundaries into `(start_index, end_index, remaining_fraction)` segments (full between/around windows, reduced inside). Each segment is a `TimedStream` whose `monthly_amount` is the **un-quantized** re-anchored base `base_monthly * remaining * (1 + raise) ** ((segment_start - job_start) / 12)`; `project_stream` then applies within-segment growth and the single cents rounding. Disjoint segment series are summed to the job's gross.

- [ ] **Step 1: Write the failing tests**

```python
# packages/domain/tests/test_job_income.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline, add_months, project_stream

from domain.job_income.compile import project_job_gross


def _timeline() -> Timeline:
    return Timeline(default_plan(), today=date(2026, 1, 1))


def test_single_job_matches_growth_curve() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    rate = Decimal("0.12")
    job = Job(annual_income=annual_income, annual_raise=rate)

    gross = project_job_gross(job, timeline)

    reference = project_stream(
        TimedStream(monthly_amount=annual_income / Decimal(12), annual_growth_rate=rate),
        timeline,
    )
    assert gross == reference


def test_full_break_zeroes_window_and_resumes_on_curve() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    rate = Decimal("0.12")
    break_start_index = 12
    break_end_index = 23
    resume_index = break_end_index + 1
    start_y, start_m = add_months(timeline.today.year, timeline.today.month, break_start_index)
    end_y, end_m = add_months(timeline.today.year, timeline.today.month, break_end_index)
    job = Job(
        annual_income=annual_income,
        annual_raise=rate,
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=start_y, month=start_m),
                end=CalendarMonthBoundary(year=end_y, month=end_m),
                remaining_fraction=Decimal("0"),
            )
        ],
    )

    gross = project_job_gross(job, timeline)

    no_break = project_job_gross(Job(annual_income=annual_income, annual_raise=rate), timeline)
    assert gross[break_start_index] == Decimal("0.00")
    assert gross[break_end_index] == Decimal("0.00")
    assert gross[resume_index] == no_break[resume_index]


def test_partial_reduction_scales_window() -> None:
    timeline = _timeline()
    annual_income = Decimal("120000")
    remaining = Decimal("0.5")
    window_index = 6
    win_y, win_m = add_months(timeline.today.year, timeline.today.month, window_index)
    job = Job(
        annual_income=annual_income,
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=win_y, month=win_m),
                end=CalendarMonthBoundary(year=win_y, month=win_m),
                remaining_fraction=remaining,
            )
        ],
    )

    gross = project_job_gross(job, timeline)

    full_monthly = (annual_income / Decimal(12)).quantize(Decimal("0.01"))
    assert gross[window_index] == (full_monthly * remaining).quantize(Decimal("0.01"))
```

- [ ] **Step 2: Scaffold to a logical red**

Create `packages/domain/domain/job_income/__init__.py`:

```python
"""Job income: compile jobs into projected monthly cashflow series."""
```

Create `packages/domain/domain/job_income/compile.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.job import Job
from core.streams import TimedStream
from core.timeline import Timeline, project_stream

_MONTHS_PER_YEAR = Decimal(12)


def project_job_gross(job: Job, timeline: Timeline) -> list[Decimal]:
    raise NotImplementedError
```

- [ ] **Step 3: Run tests to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_job_income.py::test_single_job_matches_growth_curve -v`
Expected: FAIL with `NotImplementedError` (logical, not import).

- [ ] **Step 4: Implement the compiler**

Replace `project_job_gross` in `compile.py`:

```python
def _segments(
    job: Job, timeline: Timeline, job_start: int, job_end: int
) -> list[tuple[int, int, Decimal]]:
    """(start_index, end_index, remaining_fraction) segments covering the job."""
    segments: list[tuple[int, int, Decimal]] = []
    cursor = job_start
    for window in job.sabbaticals:
        window_start = timeline.index_of(window.start)
        window_end = timeline.index_of(window.end)
        if window_start > cursor:
            segments.append((cursor, window_start - 1, Decimal(1)))
        segments.append((window_start, window_end, window.remaining_fraction))
        cursor = window_end + 1
    if cursor <= job_end:
        segments.append((cursor, job_end, Decimal(1)))
    return segments


def _segment_stream(
    base_monthly: Decimal,
    remaining: Decimal,
    segment_start: int,
    job_start: int,
    growth: Decimal,
    timeline: Timeline,
    segment_end: int,
) -> TimedStream:
    anchor_exponent = Decimal(segment_start - job_start) / _MONTHS_PER_YEAR
    segment_base = base_monthly * remaining * (Decimal(1) + growth) ** anchor_exponent
    return TimedStream(
        monthly_amount=segment_base,
        start=timeline.month_boundary(segment_start),
        end=timeline.month_boundary(segment_end),
        annual_growth_rate=growth,
        is_nominal=False,
    )


def project_job_gross(job: Job, timeline: Timeline) -> list[Decimal]:
    """Project one job to a horizon-length monthly gross series (sabbaticals applied)."""
    horizon = timeline.horizon_months
    series = [Decimal("0.00")] * horizon
    if horizon <= 0:
        return series

    base_monthly = job.annual_income / _MONTHS_PER_YEAR
    growth = job.annual_raise
    job_start = 0 if job.start is None else timeline.index_of(job.start)
    job_end = horizon - 1 if job.end is None else timeline.index_of(job.end)

    for segment_start, segment_end, remaining in _segments(job, timeline, job_start, job_end):
        if segment_start > segment_end:
            continue
        stream = _segment_stream(
            base_monthly, remaining, segment_start, job_start, growth, timeline, segment_end
        )
        segment_series = project_stream(stream, timeline)
        for i in range(horizon):
            series[i] += segment_series[i]
    return series
```

- [ ] **Step 5: Run the compile tests + existing domain test**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Then: `uv run pytest packages/domain -v`
Expected: PASS (incl. `test_domain_scaffold`). The re-anchoring test passes because `segment_base` is un-quantized — `project_stream` applies the single cents rounding, so the post-break value equals the no-break curve exactly.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/job_income/__init__.py packages/domain/domain/job_income/compile.py packages/domain/tests/test_job_income.py
git commit -m "feat(domain): compile jobs into projected gross series with sabbatical re-anchoring"
```

---

## Task 7: `project_job_income` aggregator + result types

**Files:**

- Modify: `packages/domain/domain/job_income/__init__.py`
- Test: `packages/domain/tests/test_job_income.py`

- [ ] **Step 1: Write the failing tests**

Append to `packages/domain/tests/test_job_income.py`:

```python
from core.models import Household, PersonHousehold, Plan, Portfolio

from domain.job_income import (
    JobIncomeProjection,
    PersonJobIncome,
    project_job_income,
)


def _plan_with_jobs(person1_jobs: list[Job], person2_jobs: list[Job]) -> Plan:
    base = default_plan()
    return Plan(
        name=base.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=base.household.person1.birth_month,
                birth_year=base.household.person1.birth_year,
                max_age_years=base.household.person1.max_age_years,
                jobs=person1_jobs,
            ),
            person2=PersonHousehold(
                birth_month=base.household.person2.birth_month,
                birth_year=base.household.person2.birth_year,
                max_age_years=base.household.person2.max_age_years,
                jobs=person2_jobs,
            ),
        ),
        portfolio=base.portfolio,
    )


def test_concurrent_jobs_sum_per_person() -> None:
    timeline = _timeline()
    income_a = Decimal("60000")
    income_b = Decimal("36000")
    plan = _plan_with_jobs(
        [Job(annual_income=income_a), Job(annual_income=income_b)], []
    )

    projection = project_job_income(plan, timeline)

    expected_month0 = (
        income_a / Decimal(12) + income_b / Decimal(12)
    ).quantize(Decimal("0.01"))
    assert projection.person1.gross[0] == expected_month0


def test_non_ss_covered_job_excluded_from_ss_series() -> None:
    timeline = _timeline()
    covered = Decimal("60000")
    uncovered = Decimal("48000")
    plan = _plan_with_jobs(
        [
            Job(annual_income=covered, social_security_eligible=True),
            Job(annual_income=uncovered, social_security_eligible=False),
        ],
        [],
    )

    projection = project_job_income(plan, timeline)

    assert projection.person1.gross[0] == (
        covered / Decimal(12) + uncovered / Decimal(12)
    ).quantize(Decimal("0.01"))
    assert projection.person1.ss_covered_gross[0] == (
        covered / Decimal(12)
    ).quantize(Decimal("0.01"))


def test_tax_deferred_scales_with_income_fraction() -> None:
    timeline = _timeline()
    income = Decimal("100000")
    deferred = Decimal("20000")
    plan = _plan_with_jobs([Job(annual_income=income, annual_tax_deferred=deferred)], [])

    projection = project_job_income(plan, timeline)

    fraction = deferred / income
    expected = (
        (income / Decimal(12)).quantize(Decimal("0.01")) * fraction
    ).quantize(Decimal("0.01"))
    assert projection.person1.tax_deferred[0] == expected


def test_zero_income_job_has_zero_tax_deferred() -> None:
    timeline = _timeline()
    plan = _plan_with_jobs([Job(annual_income=Decimal("0"))], [])

    projection = project_job_income(plan, timeline)

    assert all(value == Decimal("0.00") for value in projection.person1.tax_deferred)


def test_household_totals_equal_sum_of_persons() -> None:
    timeline = _timeline()
    income1 = Decimal("90000")
    income2 = Decimal("72000")
    plan = _plan_with_jobs([Job(annual_income=income1)], [Job(annual_income=income2)])

    projection = project_job_income(plan, timeline)

    assert projection.total_gross[0] == (
        projection.person1.gross[0] + projection.person2.gross[0]
    )
```

- [ ] **Step 2: Scaffold to a logical red**

Replace `packages/domain/domain/job_income/__init__.py` with stubs:

```python
"""Job income: compile jobs into projected monthly cashflow series."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel

from core.models import Plan, PersonHousehold
from core.timeline import Timeline

from domain.job_income.compile import project_job_gross

_CENTS = Decimal("0.01")


class PersonJobIncome(BaseModel):
    gross: list[Decimal]
    ss_covered_gross: list[Decimal]
    tax_deferred: list[Decimal]


class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome


def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection:
    raise NotImplementedError
```

- [ ] **Step 3: Run tests to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_job_income.py::test_concurrent_jobs_sum_per_person -v`
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement aggregation + totals**

Replace the stub bodies in `__init__.py`:

```python
def _add(left: list[Decimal], right: list[Decimal]) -> list[Decimal]:
    return [a + b for a, b in zip(left, right, strict=True)]


class PersonJobIncome(BaseModel):
    gross: list[Decimal]
    ss_covered_gross: list[Decimal]
    tax_deferred: list[Decimal]


class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome
    total_gross: list[Decimal]
    total_ss_covered_gross: list[Decimal]
    total_tax_deferred: list[Decimal]


def _project_person(person: PersonHousehold, timeline: Timeline) -> PersonJobIncome:
    horizon = timeline.horizon_months
    gross = [Decimal("0.00")] * horizon
    ss_covered = [Decimal("0.00")] * horizon
    tax_deferred = [Decimal("0.00")] * horizon
    for job in person.jobs:
        job_gross = project_job_gross(job, timeline)
        gross = _add(gross, job_gross)
        if job.social_security_eligible:
            ss_covered = _add(ss_covered, job_gross)
        if job.annual_income > 0:
            fraction = job.annual_tax_deferred / job.annual_income
            job_deferred = [
                (value * fraction).quantize(_CENTS, rounding=ROUND_HALF_UP)
                for value in job_gross
            ]
            tax_deferred = _add(tax_deferred, job_deferred)
    return PersonJobIncome(
        gross=gross, ss_covered_gross=ss_covered, tax_deferred=tax_deferred
    )


def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection:
    person1 = _project_person(plan.household.person1, timeline)
    person2 = _project_person(plan.household.person2, timeline)
    return JobIncomeProjection(
        person1=person1,
        person2=person2,
        total_gross=_add(person1.gross, person2.gross),
        total_ss_covered_gross=_add(person1.ss_covered_gross, person2.ss_covered_gross),
        total_tax_deferred=_add(person1.tax_deferred, person2.tax_deferred),
    )
```

- [ ] **Step 5: Run domain tests + full core/domain suites**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Then: `uv run pytest packages/core packages/domain -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/job_income/__init__.py packages/domain/tests/test_job_income.py
git commit -m "feat(domain): aggregate per-person and household job income projection"
```

---

## Task 8: Documentation + active-phase pointer + full gate

**Files:**

- Modify: `packages/domain/OVERVIEW.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Update the domain port map**

In `packages/domain/OVERVIEW.md`, change the job-income row status:

```markdown
| `job_income.py` (incl. planned sabbaticals) | `domain/job_income/` | 2b | done |
```

- [ ] **Step 2: Update the rebuild index active phase**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, set the Active phase table and check Phase 2b exit criteria:

```markdown
| **Current phase** | Phase 2c — plan |
| **Active plan** | *(to write)* `2026-06-12-phase-2c-domain-social-security.md` |
| **Next action** | Write Phase 2c plan before coding |
```

Tick the Phase 2b exit-criteria checkboxes (`- [x]`) in that file, and add the Phase 2b plan to the "Completed plans" table:

```markdown
| Phase 2b | `2026-06-12-phase-2b-domain-job-income.md` | complete |
```

- [ ] **Step 3: Run the full gate**

Run: `make`
Expected: lint + type-check + all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/domain/OVERVIEW.md docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "docs: mark Phase 2b job income complete; point index at Phase 2c"
```

---

## Self-Review

**Spec coverage (spec §-by-§):**

- §3 models → Tasks 1, 2. §3 validation (field/Job/Household) → Tasks 1, 5. §3 `boundary_to_year_month` + `index_of` reuse → Task 3.
- §4 segmented compilation + re-anchoring + `month_boundary` → Tasks 4, 6.
- §5 `JobIncomeProjection` per-person + totals; uncapped `ss_covered_gross`; tax-deferred fraction (incl. `annual_income==0`) → Task 7.
- §6 file layout → all tasks. §7 testing table → tests across Tasks 1–7. §8 error handling → Tasks 1, 5, 6. §9 exit criteria → Task 8 + suite. §10 deferred → not implemented (correct).

**Type consistency:** `project_job_gross(job, timeline) -> list[Decimal]` (Task 6) is consumed unchanged in Task 7. `PersonJobIncome` fields `gross` / `ss_covered_gross` / `tax_deferred` and `JobIncomeProjection.person1/person2` + `total_`* properties are consistent between definition (Task 7) and tests. `boundary_to_year_month(boundary, household)` signature matches its caller in `index_of` (Task 3) and `_validate_job_windows` (Task 5). `Timeline.month_boundary(index)` matches usage in `_segment_stream` (Task 6).

**Placeholder scan:** no `TBD`/`TODO`/"handle edge cases"; every code step shows complete code; every test step shows the assertion.

**Import-cycle check:** Task 3 moves `core.models` import in `timeline.py` under `TYPE_CHECKING`, so `core.models` importing `boundary_to_year_month` from `core.timeline` (Task 5) does not create a runtime cycle.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-12-phase-2b-domain-job-income.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
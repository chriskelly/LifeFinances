# Phase 2b — Domain: Job Income Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port legacy job income onto the Phase 2a `TimedStream` foundation — multiple jobs per person, each with per-job sabbatical windows (full break or % reduction), projected into per-person month-indexed series for Phase 2c/2d.

**Architecture:** Config models (`Job`, `SabbaticalWindow`) live in `core` and persist on `PersonHousehold.jobs`. A `Household` Pydantic validator enforces sabbatical-window structure using birth-date-only boundary resolution. The `domain.job_income` package compiles each job into re-anchored `TimedStream` segments (reusing `core.timeline.project_stream`) and aggregates them into a `JobIncomeProjection`.

**Tech Stack:** Python 3.14, Pydantic v2, `Decimal`, pytest, uv workspace. Run all commands from the repo root `/Users/chris/Projects/life-finances-workspace/LifeFInances`.

**Status:** in progress

**Spec:** [`docs/superpowers/specs/2026-06-12-phase-2b-domain-job-income-design.md`](../specs/2026-06-12-phase-2b-domain-job-income-design.md)

---

## File structure

| File | Responsibility |
|------|----------------|
| `packages/core/core/job.py` (new) | `Job`, `SabbaticalWindow` config models + `Job`-level validator |
| `packages/core/core/models.py` (modify) | `PersonHousehold.jobs`; `Household` sabbatical-window validator |
| `packages/core/core/timeline.py` (modify) | `boundary_to_year_month` resolver; `Timeline.month_boundary`; `index_of` reuses resolver |
| `packages/domain/domain/job_income/__init__.py` (new) | `project_job_income`, `JobIncomeProjection`, `PersonJobIncome` |
| `packages/domain/domain/job_income/compile.py` (new) | `compile_job_to_streams` (segment split + re-anchoring) |
| `packages/core/tests/test_job.py` (new) | `Job` + `Household` validation, repository round-trip |
| `packages/core/tests/test_timeline.py` (modify) | `boundary_to_year_month`, `month_boundary` |
| `packages/domain/tests/test_job_income.py` (new) | compiler + projection behavior |
| `packages/domain/OVERVIEW.md` (modify) | job-income port status |
| `docs/superpowers/plans/2026-06-12-rebuild-index.md` (modify) | mark Phase 2b complete |

**Build order:** Task 1 (models) → Task 2 (wire + persist) → Task 3 (resolver/helpers) → Task 4 (Household validator) → Task 5 (compiler) → Task 6 (projection) → Task 7 (docs + green).

---

## Task 1: `Job` and `SabbaticalWindow` config models

**Files:**
- Create: `packages/core/core/job.py`
- Test: `packages/core/tests/test_job.py`

- [ ] **Step 1: Write the failing test**

Create `packages/core/tests/test_job.py`:

```python
from __future__ import annotations

from decimal import Decimal

import pytest
from core.job import Job, SabbaticalWindow
from core.streams import CalendarMonthBoundary
from pydantic import ValidationError


def test_job_rejects_tax_deferred_above_income() -> None:
    income = Decimal("100000")
    too_much = income + Decimal("1")

    with pytest.raises(ValidationError):
        Job(annual_income=income, annual_tax_deferred=too_much)


def test_job_allows_tax_deferred_equal_to_income() -> None:
    income = Decimal("80000")

    job = Job(annual_income=income, annual_tax_deferred=income)

    assert job.annual_tax_deferred == income


def test_sabbatical_window_rejects_remaining_fraction_above_one() -> None:
    with pytest.raises(ValidationError):
        SabbaticalWindow(
            start=CalendarMonthBoundary(year=2030, month=1),
            end=CalendarMonthBoundary(year=2030, month=6),
            remaining_fraction=Decimal("1.5"),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_job.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.job'`. If so, add the empty scaffold below and re-run; expected next failure is logical (`ValidationError` not raised). Confirm the failure is logical before implementing.

- [ ] **Step 3: Write minimal implementation**

Create `packages/core/core/job.py`:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from core.streams import Boundary


class SabbaticalWindow(BaseModel):
    """A window over which a job's pay is reduced (or fully paused).

    `remaining_fraction` is the share of pay still earned: 0 => full break,
    0.5 => half pay, 1 => no reduction. The job's underlying raise clock keeps
    running across the window, so the person returns at the grown salary.
    Window ordering / overlap / containment is validated on `Household`.
    """

    start: Boundary
    end: Boundary
    remaining_fraction: Decimal = Field(ge=0, le=1)


class Job(BaseModel):
    """One job held by a person, modeled as a real (today's-dollar) income source.

    Amounts are annual; the domain compiles them to a monthly stream.
    `annual_raise` is a REAL raise (growth above inflation). Inflation is never
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

    @model_validator(mode="after")
    def _tax_deferred_within_income(self) -> Job:
        if self.annual_tax_deferred > self.annual_income:
            raise ValueError("annual_tax_deferred must not exceed annual_income")
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_job.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/job.py packages/core/tests/test_job.py
git commit -m "feat(core): add Job and SabbaticalWindow config models"
```

---

## Task 2: Wire `PersonHousehold.jobs` and prove SQLite round-trip

**Files:**
- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_repository.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/core/tests/test_repository.py`:

```python
def test_round_trip_preserves_person_jobs(repo: PlanRepository) -> None:
    from decimal import Decimal

    from core.job import Job, SabbaticalWindow
    from core.streams import CalendarMonthBoundary

    plan_id, plan = repo.get_or_create_default()
    expected_income = Decimal("123456.78")
    job = Job(
        label="Engineer",
        annual_income=expected_income,
        annual_tax_deferred=Decimal("23000"),
        annual_raise=Decimal("0.03"),
        sabbaticals=[
            SabbaticalWindow(
                start=CalendarMonthBoundary(year=2032, month=1),
                end=CalendarMonthBoundary(year=2032, month=12),
                remaining_fraction=Decimal("0.5"),
            )
        ],
    )
    plan.household.person1.jobs = [job]

    repo.save(plan_id, plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    loaded_job = loaded.household.person1.jobs[0]
    assert loaded_job.annual_income == expected_income
    assert loaded_job.sabbaticals[0].remaining_fraction == Decimal("0.5")
    assert isinstance(loaded_job.sabbaticals[0].start, CalendarMonthBoundary)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_repository.py::test_round_trip_preserves_person_jobs -v`
Expected: FAIL — logical failure setting `.jobs` (Pydantic `ValueError` "object has no field 'jobs'") because `PersonHousehold` has no `jobs` field yet.

- [ ] **Step 3: Write minimal implementation**

Modify `packages/core/core/models.py`. Add the import and the field:

```python
from core.job import Job
from core.streams import TimedStream


class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)
```

(Keep the existing `Household`, `Portfolio`, `Plan` classes unchanged in this task.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_repository.py -v`
Expected: PASS (all repository tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_repository.py
git commit -m "feat(core): persist per-person jobs on PersonHousehold"
```

---

## Task 3: `boundary_to_year_month` resolver + `Timeline.month_boundary`

**Files:**
- Modify: `packages/core/core/timeline.py`
- Test: `packages/core/tests/test_timeline.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/core/tests/test_timeline.py`:

```python
from core.timeline import boundary_to_year_month


def test_boundary_to_year_month_resolves_person_age_without_today() -> None:
    plan = default_plan()
    person = plan.household.person1
    age_months = 480  # 40 years

    year, month = boundary_to_year_month(
        PersonAgeBoundary(person="person1", age_months=age_months),
        plan.household,
    )

    assert year == person.birth_year + age_months // 12
    assert month == person.birth_month


def test_month_boundary_is_inverse_of_index_of() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)
    index = 27

    boundary = timeline.month_boundary(index)

    assert timeline.index_of(boundary) == index
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_timeline.py -k "boundary_to_year_month or month_boundary" -v`
Expected: FAIL with `ImportError` for `boundary_to_year_month`. Add the scaffolds (a `boundary_to_year_month` that returns `(0, 0)` and a `month_boundary` returning `CalendarMonthBoundary(year=0, month=1)`), re-run, confirm the failure is now logical (`AssertionError`) before implementing.

- [ ] **Step 3: Write minimal implementation**

Modify `packages/core/core/timeline.py`. Add the import of `Household` and the resolver, and refactor `index_of` to reuse it; add `month_boundary`:

```python
from core.models import Household, PersonHousehold, Plan


def boundary_to_year_month(boundary: Boundary, household: Household) -> tuple[int, int]:
    """Resolve a boundary to an absolute (year, month). Birth-date only; no `today`."""
    if isinstance(boundary, CalendarMonthBoundary):
        return boundary.year, boundary.month
    if isinstance(boundary, PersonAgeBoundary):
        person = getattr(household, boundary.person)
        return add_months(person.birth_year, person.birth_month, boundary.age_months)
    raise TypeError(f"Unknown boundary: {boundary!r}")
```

Replace the body of `Timeline.index_of` with:

```python
    def index_of(self, boundary: Boundary) -> int:
        year, month = boundary_to_year_month(boundary, self.plan.household)
        return self._offset(year, month)
```

Add to `Timeline`:

```python
    def month_boundary(self, index: int) -> CalendarMonthBoundary:
        """The calendar month at `index` months from today (index 0 == this month)."""
        year, month = add_months(self.today.year, self.today.month, index)
        return CalendarMonthBoundary(year=year, month=month)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_timeline.py -v`
Expected: PASS (existing + 2 new tests; `index_of` tests still green after refactor).

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_timeline.py
git commit -m "feat(core): add boundary_to_year_month resolver and Timeline.month_boundary"
```

---

## Task 4: `Household` sabbatical-window validator

**Files:**
- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_job.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/core/tests/test_job.py`:

```python
from core.models import Household, PersonHousehold


def _person(birth_year: int, jobs: list[Job]) -> PersonHousehold:
    return PersonHousehold(birth_month=1, birth_year=birth_year, jobs=jobs)


def _window(start_month: int, end_month: int, remaining: str = "0") -> SabbaticalWindow:
    return SabbaticalWindow(
        start=CalendarMonthBoundary(year=2030, month=start_month),
        end=CalendarMonthBoundary(year=2030, month=end_month),
        remaining_fraction=Decimal(remaining),
    )


def test_household_rejects_overlapping_sabbatical_windows() -> None:
    job = Job(annual_income=Decimal("100000"), sabbaticals=[_window(1, 6), _window(5, 9)])

    with pytest.raises(ValidationError):
        Household(person1=_person(1980, [job]), person2=_person(1982, []))


def test_household_rejects_window_outside_explicit_job_bounds() -> None:
    job = Job(
        annual_income=Decimal("100000"),
        start=CalendarMonthBoundary(year=2030, month=3),
        end=CalendarMonthBoundary(year=2030, month=8),
        sabbaticals=[_window(1, 4)],  # starts before job start
    )

    with pytest.raises(ValidationError):
        Household(person1=_person(1980, [job]), person2=_person(1982, []))


def test_household_accepts_ordered_in_bounds_windows() -> None:
    job = Job(annual_income=Decimal("100000"), sabbaticals=[_window(1, 3), _window(5, 7)])

    household = Household(person1=_person(1980, [job]), person2=_person(1982, []))

    assert household.person1.jobs[0].sabbaticals[1].start.month == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/core/tests/test_job.py -k household -v`
Expected: FAIL — logical failure: the two "reject" tests do not raise `ValidationError` because no `Household` validator exists yet.

- [ ] **Step 3: Write minimal implementation**

Modify `packages/core/core/models.py`. Add a `model_validator(mode="after")` to `Household` (import `model_validator` from pydantic). The `boundary_to_year_month` import is local to avoid a circular import with `core.timeline`:

```python
from pydantic import BaseModel, Field, model_validator


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold

    @model_validator(mode="after")
    def _validate_sabbatical_windows(self) -> "Household":
        from core.timeline import boundary_to_year_month

        def abs_month(boundary) -> int:
            year, month = boundary_to_year_month(boundary, self)
            return year * 12 + (month - 1)

        for person in (self.person1, self.person2):
            for job in person.jobs:
                job_lo = abs_month(job.start) if job.start is not None else None
                job_hi = abs_month(job.end) if job.end is not None else None
                prev_end: int | None = None
                for window in job.sabbaticals:
                    start = abs_month(window.start)
                    end = abs_month(window.end)
                    if start > end:
                        raise ValueError("sabbatical window start must not be after end")
                    if job_lo is not None and start < job_lo:
                        raise ValueError("sabbatical window starts before job start")
                    if job_hi is not None and end > job_hi:
                        raise ValueError("sabbatical window ends after job end")
                    if prev_end is not None and start <= prev_end:
                        raise ValueError("sabbatical windows must be ordered and non-overlapping")
                    prev_end = end
        return self
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/core/tests/test_job.py -v`
Expected: PASS (all `Job` + `Household` tests).

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/models.py packages/core/tests/test_job.py
git commit -m "feat(core): validate sabbatical windows on Household"
```

---

## Task 5: Compile a `Job` into re-anchored `TimedStream` segments

**Files:**
- Create: `packages/domain/domain/job_income/__init__.py`
- Create: `packages/domain/domain/job_income/compile.py`
- Test: `packages/domain/tests/test_job_income.py`

- [ ] **Step 1: Write the failing test**

Create `packages/domain/tests/test_job_income.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.job import Job, SabbaticalWindow
from core.streams import CalendarMonthBoundary
from core.timeline import Timeline, project_stream
from domain.job_income.compile import compile_job_to_streams


def _timeline() -> Timeline:
    return Timeline(default_plan(), today=date(2026, 1, 1))


def _project(job: Job, timeline: Timeline) -> list[Decimal]:
    horizon = timeline.horizon_months
    totals = [Decimal("0.00")] * horizon
    for stream in compile_job_to_streams(job, timeline):
        for index, value in enumerate(project_stream(stream, timeline)):
            totals[index] += value
    return totals


def test_single_job_converts_annual_to_monthly() -> None:
    timeline = _timeline()
    annual = Decimal("120000")
    job = Job(annual_income=annual)

    series = _project(job, timeline)

    assert series[0] == (annual / 12).quantize(Decimal("0.01"))


def test_full_break_resumes_on_the_no_break_growth_curve() -> None:
    timeline = _timeline()
    annual = Decimal("120000")
    rate = Decimal("0.12")
    break_start, break_end = 12, 23
    resume_index = break_end + 1
    windowed = Job(
        annual_income=annual,
        annual_raise=rate,
        sabbaticals=[
            SabbaticalWindow(
                start=timeline.month_boundary(break_start),
                end=timeline.month_boundary(break_end),
                remaining_fraction=Decimal("0"),
            )
        ],
    )
    continuous = Job(annual_income=annual, annual_raise=rate)

    windowed_series = _project(windowed, timeline)
    continuous_series = _project(continuous, timeline)

    assert windowed_series[break_start] == Decimal("0.00")
    assert windowed_series[resume_index] == continuous_series[resume_index]


def test_partial_reduction_scales_grown_amount() -> None:
    timeline = _timeline()
    annual = Decimal("120000")
    rate = Decimal("0.12")
    remaining = Decimal("0.5")
    reduce_at = 12
    reduced = Job(
        annual_income=annual,
        annual_raise=rate,
        sabbaticals=[
            SabbaticalWindow(
                start=timeline.month_boundary(reduce_at),
                end=timeline.month_boundary(reduce_at + 5),
                remaining_fraction=remaining,
            )
        ],
    )
    full = Job(annual_income=annual, annual_raise=rate)

    reduced_series = _project(reduced, timeline)
    full_series = _project(full, timeline)

    expected = (full_series[reduce_at] * remaining).quantize(Decimal("0.01"))
    assert reduced_series[reduce_at] == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'domain.job_income'`. Add the package scaffold (empty `__init__.py` and a `compile_job_to_streams` returning `[]`), re-run, and confirm the failure is logical (`AssertionError` / `IndexError`) before implementing.

- [ ] **Step 3: Write minimal implementation**

Create `packages/domain/domain/job_income/__init__.py`:

```python
"""Job income: compile jobs into timed-stream segments and project them."""
```

Create `packages/domain/domain/job_income/compile.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.job import Job
from core.streams import TimedStream
from core.timeline import Timeline


def compile_job_to_streams(job: Job, timeline: Timeline) -> list[TimedStream]:
    """Split a job into full/reduced `TimedStream` segments.

    Each segment's base is re-anchored to the job's start so the segments stitch
    into one continuous `base * (1 + raise) ** ((t - job_start) / 12)` curve,
    scaled by `remaining_fraction` inside sabbatical windows (Phase 2a §6.1).
    """
    base_monthly = job.annual_income / Decimal(12)
    growth_base = Decimal(1) + job.annual_raise
    job_start_index = 0 if job.start is None else timeline.index_of(job.start)
    job_end_index = None if job.end is None else timeline.index_of(job.end)

    windows = [
        (
            timeline.index_of(window.start),
            timeline.index_of(window.end),
            window.remaining_fraction,
        )
        for window in job.sabbaticals
    ]

    streams: list[TimedStream] = []

    def make_segment(start_index: int, end_index: int | None, remaining: Decimal) -> None:
        exponent = Decimal(start_index - job_start_index) / Decimal(12)
        segment_base = base_monthly * remaining * (growth_base**exponent)
        streams.append(
            TimedStream(
                monthly_amount=segment_base,
                start=timeline.month_boundary(start_index),
                end=None if end_index is None else timeline.month_boundary(end_index),
                annual_growth_rate=job.annual_raise,
                is_nominal=False,
            )
        )

    cursor = job_start_index
    for window_start, window_end, remaining in windows:
        if cursor <= window_start - 1:
            make_segment(cursor, window_start - 1, Decimal(1))
        make_segment(window_start, window_end, remaining)
        cursor = window_end + 1

    if job_end_index is None:
        make_segment(cursor, None, Decimal(1))
    elif cursor <= job_end_index:
        make_segment(cursor, job_end_index, Decimal(1))

    return streams
```

> Note: `monthly_amount` must be `>= 0`; `remaining_fraction` is in `[0, 1]` and the growth factor is positive, so `segment_base >= 0` always holds.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/job_income/__init__.py packages/domain/domain/job_income/compile.py packages/domain/tests/test_job_income.py
git commit -m "feat(domain): compile jobs into re-anchored sabbatical-aware stream segments"
```

---

## Task 6: `project_job_income` → `JobIncomeProjection`

**Files:**
- Modify: `packages/domain/domain/job_income/__init__.py`
- Test: `packages/domain/tests/test_job_income.py`

- [ ] **Step 1: Write the failing test**

Add to `packages/domain/tests/test_job_income.py`:

```python
from domain.job_income import JobIncomeProjection, project_job_income


def _plan_with_jobs(person1_jobs, person2_jobs):
    plan = default_plan()
    plan.household.person1.jobs = person1_jobs
    plan.household.person2.jobs = person2_jobs
    return plan


def test_concurrent_jobs_sum_per_person() -> None:
    timeline = _timeline()
    job_a = Job(annual_income=Decimal("60000"))
    job_b = Job(annual_income=Decimal("36000"))
    plan = _plan_with_jobs([job_a, job_b], [])

    projection = project_job_income(plan, timeline)

    expected = (Decimal("60000") / 12 + Decimal("36000") / 12).quantize(Decimal("0.01"))
    assert projection.person1.gross[0] == expected


def test_ss_covered_gross_excludes_non_covered_job_and_applies_no_cap() -> None:
    timeline = _timeline()
    covered = Job(annual_income=Decimal("90000"), social_security_eligible=True)
    not_covered = Job(annual_income=Decimal("90000"), social_security_eligible=False)
    plan = _plan_with_jobs([covered, not_covered], [])

    projection = project_job_income(plan, timeline)

    covered_monthly = (Decimal("90000") / 12).quantize(Decimal("0.01"))
    assert projection.person1.gross[0] == covered_monthly * 2
    assert projection.person1.ss_covered_gross[0] == covered_monthly


def test_tax_deferred_is_fraction_of_gross() -> None:
    timeline = _timeline()
    annual_income = Decimal("100000")
    annual_deferred = Decimal("20000")
    job = Job(annual_income=annual_income, annual_tax_deferred=annual_deferred)
    plan = _plan_with_jobs([job], [])

    projection = project_job_income(plan, timeline)

    fraction = annual_deferred / annual_income
    expected = (projection.person1.gross[0] * fraction).quantize(Decimal("0.01"))
    assert projection.person1.tax_deferred[0] == expected


def test_household_total_gross_equals_per_person_sum() -> None:
    timeline = _timeline()
    plan = _plan_with_jobs(
        [Job(annual_income=Decimal("60000"))],
        [Job(annual_income=Decimal("48000"))],
    )

    projection = project_job_income(plan, timeline)

    assert projection.total_gross[0] == (
        projection.person1.gross[0] + projection.person2.gross[0]
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/domain/tests/test_job_income.py -k "per_person or covered or tax_deferred or total" -v`
Expected: FAIL with `ImportError` for `project_job_income` / `JobIncomeProjection`. Add the scaffolds (classes with the listed fields + a `project_job_income` returning a zero-filled projection), re-run, confirm logical failure (`AssertionError`) before implementing.

- [ ] **Step 3: Write minimal implementation**

Replace the contents of `packages/domain/domain/job_income/__init__.py`:

```python
"""Job income: compile jobs into timed-stream segments and project them."""

from __future__ import annotations

from decimal import Decimal

from core.models import PersonHousehold, Plan
from core.timeline import Timeline, project_stream
from pydantic import BaseModel

from domain.job_income.compile import compile_job_to_streams

_CENTS = Decimal("0.01")


class PersonJobIncome(BaseModel):
    gross: list[Decimal]
    ss_covered_gross: list[Decimal]
    tax_deferred: list[Decimal]


def _sum(left: list[Decimal], right: list[Decimal]) -> list[Decimal]:
    return [a + b for a, b in zip(left, right, strict=True)]


class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome

    @property
    def total_gross(self) -> list[Decimal]:
        return _sum(self.person1.gross, self.person2.gross)

    @property
    def total_ss_covered_gross(self) -> list[Decimal]:
        return _sum(self.person1.ss_covered_gross, self.person2.ss_covered_gross)

    @property
    def total_tax_deferred(self) -> list[Decimal]:
        return _sum(self.person1.tax_deferred, self.person2.tax_deferred)


def _project_person(person: PersonHousehold, timeline: Timeline) -> PersonJobIncome:
    horizon = timeline.horizon_months
    gross = [Decimal("0.00")] * horizon
    ss_covered = [Decimal("0.00")] * horizon
    tax_deferred = [Decimal("0.00")] * horizon

    for job in person.jobs:
        fraction = (
            job.annual_tax_deferred / job.annual_income
            if job.annual_income
            else Decimal(0)
        )
        job_series = [Decimal("0.00")] * horizon
        for stream in compile_job_to_streams(job, timeline):
            for index, value in enumerate(project_stream(stream, timeline)):
                job_series[index] += value
        for index in range(horizon):
            month_gross = job_series[index]
            gross[index] += month_gross
            if job.social_security_eligible:
                ss_covered[index] += month_gross
            tax_deferred[index] += (month_gross * fraction).quantize(_CENTS)

    return PersonJobIncome(
        gross=gross, ss_covered_gross=ss_covered, tax_deferred=tax_deferred
    )


def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection:
    return JobIncomeProjection(
        person1=_project_person(plan.household.person1, timeline),
        person2=_project_person(plan.household.person2, timeline),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest packages/domain/tests/test_job_income.py -v`
Expected: PASS (all compiler + projection tests).

- [ ] **Step 5: Commit**

```bash
git add packages/domain/domain/job_income/__init__.py packages/domain/tests/test_job_income.py
git commit -m "feat(domain): aggregate jobs into a per-person JobIncomeProjection"
```

---

## Task 7: Update docs and confirm full green

**Files:**
- Modify: `packages/domain/OVERVIEW.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Mark the job-income port done in `packages/domain/OVERVIEW.md`**

Change the port-map row:

```markdown
| `job_income.py` (incl. planned sabbaticals) | `domain/job_income/` | 2b | done |
```

- [ ] **Step 2: Update the rebuild index**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`:
- Check the four Phase 2b exit-criteria boxes (`- [x]`).
- In the **Active phase** table set current phase to `Phase 2c — plan`, active plan to `2026-06-12-phase-2c-domain-social-security.md`, next action to "Write Phase 2c plan before coding".
- Add a row to **Completed plans**: `| Phase 2b | 2026-06-12-phase-2b-domain-job-income.md | complete |`.
- Set this plan's header `**Status:**` to `complete`.

- [ ] **Step 3: Run the full suite and linters**

Run: `make`
Expected: lint + all package tests pass (`core`, `domain`, `simulation`, `web`).

- [ ] **Step 4: Commit**

```bash
git add packages/domain/OVERVIEW.md docs/superpowers/plans/2026-06-12-rebuild-index.md docs/superpowers/plans/2026-06-12-phase-2b-domain-job-income.md
git commit -m "docs: mark Phase 2b job income complete"
```

---

## Self-review notes

- **Spec coverage:** Job/SabbaticalWindow models (Task 1) · `PersonHousehold.jobs` + persistence (Task 2) · `boundary_to_year_month` + `month_boundary` + `index_of` reuse (Task 3) · `Household` window validator with no-`today` resolution and open-bound tolerance (Task 4) · segment compilation with re-anchoring (Task 5) · per-person `gross`/`ss_covered_gross`/`tax_deferred` + household totals, uncapped SS, fraction tax-deferred, divide-by-zero guard (Task 6) · OVERVIEW + index (Task 7).
- **No system-level retirement state** — never introduced; "no income" is just zeros.
- **Type consistency:** `compile_job_to_streams(job, timeline)`, `project_job_income(plan, timeline)`, `JobIncomeProjection.person{1,2}` / `total_*`, `PersonJobIncome.{gross,ss_covered_gross,tax_deferred}`, `boundary_to_year_month(boundary, household)`, `Timeline.month_boundary(index)` are used identically across tasks.
- **Circular import:** `core.models.Household` validator imports `boundary_to_year_month` locally (function body), since `core.timeline` imports `core.models` at module load.

---

## Execution handoff

Implement via **superpowers:subagent-driven-development** (recommended) — one subagent per task, review between tasks — or **superpowers:executing-plans** for batched inline execution.

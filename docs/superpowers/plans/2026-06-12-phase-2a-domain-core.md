# Phase 2a — Domain Core Types & Timed Streams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lean, reusable timed-stream type plus calendar/age month-indexing and a single-stream projection utility to `packages/core`, wire a persisted (dormant) `manual_income_streams` field onto `Plan`, consolidate horizon math into `core`, and complete the `domain` package's `OVERVIEW.md`.

**Architecture:** `core/streams.py` defines `TimedStream` + a discriminated `Boundary` union. `core/timeline.py` owns all calendar→`month_index` math (`person_end_date`, `horizon_months`, `Timeline.index_of`) and `project_stream`. `simulation/horizon.py` becomes a thin re-export so there is one source of truth. No finance logic and no inflation handling land here — those are Phase 2b+.

**Tech Stack:** Python 3.14, Pydantic v2, `Decimal` money, pytest, ruff, pyright, uv workspace.

**Spec:** [`docs/superpowers/specs/2026-06-12-phase-2a-domain-core-design.md`](../specs/2026-06-12-phase-2a-domain-core-design.md)

---

## Conventions (read before starting)

- Every module starts with `from __future__ import annotations`.
- Money/rates are `Decimal`. Never use `float` for amounts.
- Tests inject a fixed `today: date` — never call `date.today()` in a test assertion.
- Pull shared values from source (import `default_plan`, `DEFAULT_*`); do not duplicate a literal across arrange and assert.
- Run commands from the **repository root**.
- Run a single test: `uv run pytest <path>::<test> -v`
- `make` runs lint + test and must pass before the phase is complete.

---

## Task 1: `TimedStream` type and boundaries

**Files:**
- Create: `packages/core/core/streams.py`
- Create: `packages/core/tests/test_streams.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_streams.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.streams import (
    CalendarMonthBoundary,
    PersonAgeBoundary,
    TimedStream,
)


def test_timed_stream_round_trips_through_json_preserving_decimal() -> None:
    expected_amount = Decimal("1234.56")
    expected_growth = Decimal("0.03")
    stream = TimedStream(
        label="Salary",
        monthly_amount=expected_amount,
        start=CalendarMonthBoundary(year=2030, month=4),
        end=PersonAgeBoundary(person="person1", age_months=780),
        is_nominal=True,
        annual_growth_rate=expected_growth,
    )

    loaded = TimedStream.model_validate_json(stream.model_dump_json())

    assert loaded.monthly_amount == expected_amount
    assert loaded.annual_growth_rate == expected_growth
    assert loaded.is_nominal is True


def test_boundary_union_resolves_to_correct_kind() -> None:
    calendar_year, calendar_month = 2031, 7
    age_months = 744
    stream = TimedStream(
        monthly_amount=Decimal("500"),
        start=CalendarMonthBoundary(year=calendar_year, month=calendar_month),
        end=PersonAgeBoundary(person="person2", age_months=age_months),
    )

    loaded = TimedStream.model_validate_json(stream.model_dump_json())

    assert isinstance(loaded.start, CalendarMonthBoundary)
    assert loaded.start.year == calendar_year
    assert loaded.start.month == calendar_month
    assert isinstance(loaded.end, PersonAgeBoundary)
    assert loaded.end.person == "person2"
    assert loaded.end.age_months == age_months
```

- [ ] **Step 2: Run the tests to verify they fail structurally, then logically**

Run: `uv run pytest packages/core/tests/test_streams.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.streams'` (structural). After Step 3 the import resolves and assertions pass.

- [ ] **Step 3: Write the implementation**

Create `packages/core/core/streams.py`:

```python
from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

PersonId = Literal["person1", "person2"]


class CalendarMonthBoundary(BaseModel):
    kind: Literal["calendar_month"] = "calendar_month"
    year: int
    month: int = Field(ge=1, le=12)


class PersonAgeBoundary(BaseModel):
    kind: Literal["person_age"] = "person_age"
    person: PersonId
    age_months: int = Field(ge=0)


Boundary = Annotated[
    CalendarMonthBoundary | PersonAgeBoundary,
    Field(discriminator="kind"),
]


class TimedStream(BaseModel):
    """A monthly recurring income or spending stream over a bounded window.

    Amounts are face amounts in the stream's OWN basis. Inflation is never
    applied here (see spec section 6); `is_nominal` is carried metadata for the
    simulation layer.
    """

    label: str | None = None
    monthly_amount: Decimal = Field(ge=0)
    start: Boundary | None = None
    end: Boundary | None = None
    is_nominal: bool = False
    annual_growth_rate: Decimal = Decimal(0)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_streams.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/streams.py packages/core/tests/test_streams.py
git commit -m "feat(core): add lean TimedStream type and boundary union"
```

---

## Task 2: Timeline month indexing + horizon consolidation

Move the canonical horizon math into `core.timeline` and make `simulation.horizon` delegate. Add `Timeline.index_of`.

**Files:**
- Create: `packages/core/core/timeline.py`
- Create: `packages/core/tests/test_timeline.py`
- Modify: `packages/simulation/simulation/horizon.py` (delegate to core)

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_timeline.py`:

```python
from __future__ import annotations

from datetime import date

from core.defaults import default_plan
from core.streams import CalendarMonthBoundary, PersonAgeBoundary
from core.timeline import Timeline, horizon_months, person_end_date


def test_index_of_calendar_month_is_offset_from_today() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)
    target_year, target_month = 2027, 9

    result = timeline.index_of(
        CalendarMonthBoundary(year=target_year, month=target_month)
    )

    expected = (target_year - today.year) * 12 + (target_month - today.month)
    assert result == expected


def test_index_of_past_calendar_month_is_negative() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)

    result = timeline.index_of(CalendarMonthBoundary(year=2026, month=1))

    assert result == -5


def test_index_of_person_age_uses_birth_month_plus_age_months() -> None:
    today = date(2026, 1, 1)
    plan = default_plan()
    person = plan.household.person1
    age_months = 600  # 50 years
    timeline = Timeline(plan, today=today)

    result = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=age_months)
    )

    reached_year = person.birth_year + age_months // 12
    reached_month = person.birth_month  # age_months is a whole number of years
    expected = (reached_year - today.year) * 12 + (reached_month - today.month)
    assert result == expected


def test_horizon_months_matches_max_age_person_age_boundary() -> None:
    today = date(2026, 6, 1)
    plan = default_plan()
    timeline = Timeline(plan, today=today)
    later = max(
        person_end_date(plan.household.person1),
        person_end_date(plan.household.person2),
    )

    expected = (later.year - today.year) * 12 + (later.month - today.month)
    assert timeline.horizon_months == expected
    assert horizon_months(plan, today=today) == expected
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest packages/core/tests/test_timeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.timeline'` (structural). After Step 3, assertions evaluate and pass.

- [ ] **Step 3: Write the implementation**

Create `packages/core/core/timeline.py`:

```python
from __future__ import annotations

from datetime import date

from core.models import PersonHousehold, Plan
from core.streams import Boundary, CalendarMonthBoundary, PersonAgeBoundary


def add_months(year: int, month: int, months: int) -> tuple[int, int]:
    """Add `months` to a (year, month) pair. `month` is 1-12."""
    total = year * 12 + (month - 1) + months
    return total // 12, total % 12 + 1


def person_end_date(person: PersonHousehold) -> date:
    return date(person.birth_year + person.max_age_years, person.birth_month, 1)


def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    household = plan.household
    end = max(person_end_date(household.person1), person_end_date(household.person2))
    return (end.year - today.year) * 12 + (end.month - today.month)


class Timeline:
    """Resolves plan boundaries to month indices relative to `today`.

    month_index 0 is the current calendar month (today's year/month).
    """

    def __init__(self, plan: Plan, *, today: date | None = None) -> None:
        self.plan = plan
        self.today = today or date.today()

    @property
    def horizon_months(self) -> int:
        return horizon_months(self.plan, today=self.today)

    def _offset(self, year: int, month: int) -> int:
        return (year - self.today.year) * 12 + (month - self.today.month)

    def index_of(self, boundary: Boundary) -> int:
        if isinstance(boundary, CalendarMonthBoundary):
            return self._offset(boundary.year, boundary.month)
        if isinstance(boundary, PersonAgeBoundary):
            person = getattr(self.plan.household, boundary.person)
            reached_year, reached_month = add_months(
                person.birth_year, person.birth_month, boundary.age_months
            )
            return self._offset(reached_year, reached_month)
        raise TypeError(f"Unknown boundary: {boundary!r}")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_timeline.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Make `simulation.horizon` delegate to core**

Replace the body of `packages/simulation/simulation/horizon.py` with a re-export so there is one source of truth and the Phase 1 public API is preserved:

```python
from __future__ import annotations

from core.timeline import horizon_months, person_end_date

__all__ = ["horizon_months", "person_end_date"]
```

- [ ] **Step 6: Run the simulation horizon tests to verify delegation is transparent**

Run: `uv run pytest packages/simulation/tests/test_horizon.py -v`
Expected: PASS (existing Phase 1 test still green — `from simulation.horizon import horizon_months, person_end_date` resolves to the re-exported core functions)

- [ ] **Step 7: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_timeline.py packages/simulation/simulation/horizon.py
git commit -m "feat(core): add Timeline month indexing; consolidate horizon into core"
```

---

## Task 3: `project_stream` projection

**Files:**
- Modify: `packages/core/core/timeline.py` (add `project_stream`)
- Create: `packages/core/tests/test_projection.py`

- [ ] **Step 1: Write the failing tests**

Create `packages/core/tests/test_projection.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.defaults import default_plan
from core.streams import CalendarMonthBoundary, TimedStream
from core.timeline import Timeline, add_months, project_stream


def _timeline() -> Timeline:
    return Timeline(default_plan(), today=date(2026, 1, 1))


def test_open_stream_fills_whole_horizon_flat() -> None:
    timeline = _timeline()
    amount = Decimal("1000.00")
    stream = TimedStream(monthly_amount=amount)

    series = project_stream(stream, timeline)

    assert len(series) == timeline.horizon_months
    assert series[0] == amount
    assert series[-1] == amount


def test_bounded_window_is_zero_outside_and_amount_inside() -> None:
    timeline = _timeline()
    amount = Decimal("500.00")
    start_index = 12
    end_index = 23
    start_year, start_month = add_months(
        timeline.today.year, timeline.today.month, start_index
    )
    end_year, end_month = add_months(
        timeline.today.year, timeline.today.month, end_index
    )
    start = CalendarMonthBoundary(year=start_year, month=start_month)
    end = CalendarMonthBoundary(year=end_year, month=end_month)
    stream = TimedStream(monthly_amount=amount, start=start, end=end)

    series = project_stream(stream, timeline)

    assert timeline.index_of(start) == start_index
    assert timeline.index_of(end) == end_index
    assert series[start_index - 1] == Decimal("0.00")
    assert series[start_index] == amount
    assert series[end_index] == amount
    assert series[end_index + 1] == Decimal("0.00")


def test_growth_compounds_monthly_from_start_anchor() -> None:
    timeline = _timeline()
    base = Decimal("1000.00")
    rate = Decimal("0.12")
    stream = TimedStream(monthly_amount=base, annual_growth_rate=rate)

    series = project_stream(stream, timeline)

    expected_month_12 = (base * (Decimal(1) + rate) ** (Decimal(12) / Decimal(12))).quantize(
        Decimal("0.01")
    )
    assert series[0] == base.quantize(Decimal("0.01"))
    assert series[12] == expected_month_12


def test_window_entirely_in_past_returns_all_zero() -> None:
    timeline = _timeline()
    stream = TimedStream(
        monthly_amount=Decimal("100.00"),
        start=CalendarMonthBoundary(year=2000, month=1),
        end=CalendarMonthBoundary(year=2001, month=1),
    )

    series = project_stream(stream, timeline)

    assert len(series) == timeline.horizon_months
    assert all(value == Decimal("0.00") for value in series)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest packages/core/tests/test_projection.py -v`
Expected: FAIL with `ImportError: cannot import name 'project_stream'` (structural). After Step 3, assertions evaluate and pass.

- [ ] **Step 3: Add the implementation to `core/timeline.py`**

Update the imports at the top of `packages/core/core/timeline.py` so the import
block reads exactly (add the `decimal` line; extend the existing `core.streams`
import to include `TimedStream` — do NOT add a second `core.streams` import line,
or ruff's import sorter will fail):

```python
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from core.models import PersonHousehold, Plan
from core.streams import (
    Boundary,
    CalendarMonthBoundary,
    PersonAgeBoundary,
    TimedStream,
)
```

Append `project_stream` to `packages/core/core/timeline.py`:

```python
_CENTS = Decimal("0.01")


def project_stream(stream: TimedStream, timeline: Timeline) -> list[Decimal]:
    """Project one stream into a horizon-length series of face amounts.

    - Fills `monthly_amount` for indices in [start, end]; 0 elsewhere.
    - start defaults to 0 (now); end defaults to horizon - 1.
    - The window is clamped to [0, horizon - 1].
    - Monthly-compounded growth anchored at the (unclamped) start index:
      amount(t) = monthly_amount * (1 + annual_growth_rate) ** ((t - start) / 12)
    - Inflation is NOT applied (spec section 6).
    """
    horizon = timeline.horizon_months
    series = [Decimal("0.00")] * horizon
    if horizon <= 0:
        return series

    start_index = 0 if stream.start is None else timeline.index_of(stream.start)
    end_index = horizon - 1 if stream.end is None else timeline.index_of(stream.end)

    low = max(start_index, 0)
    high = min(end_index, horizon - 1)
    growth_base = Decimal(1) + stream.annual_growth_rate

    for month_index in range(low, high + 1):
        exponent = Decimal(month_index - start_index) / Decimal(12)
        factor = growth_base**exponent
        series[month_index] = (stream.monthly_amount * factor).quantize(
            _CENTS, rounding=ROUND_HALF_UP
        )
    return series
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest packages/core/tests/test_projection.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/timeline.py packages/core/tests/test_projection.py
git commit -m "feat(core): add project_stream with monthly-compounded growth"
```

---

## Task 4: Persist `manual_income_streams` on `Plan`

**Files:**
- Modify: `packages/core/core/models.py` (add field)
- Modify: `packages/core/core/__init__.py` (export `TimedStream`)
- Create: `packages/core/tests/test_plan_streams.py` (repository round-trip)

- [ ] **Step 1: Write the failing test**

Create `packages/core/tests/test_plan_streams.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.repository import PlanRepository
from core.streams import CalendarMonthBoundary, PersonAgeBoundary, TimedStream


def test_manual_income_streams_round_trip_through_sqlite(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_amount = Decimal("2500.00")
    expected_growth = Decimal("0.02")
    age_months = 900
    plan.manual_income_streams = [
        TimedStream(
            label="Rental",
            monthly_amount=expected_amount,
            start=CalendarMonthBoundary(year=2030, month=6),
            end=PersonAgeBoundary(person="person2", age_months=age_months),
            is_nominal=True,
            annual_growth_rate=expected_growth,
        )
    ]

    repo.save(plan_id, plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert len(loaded.manual_income_streams) == 1
    stream = loaded.manual_income_streams[0]
    assert stream.monthly_amount == expected_amount
    assert stream.annual_growth_rate == expected_growth
    assert stream.is_nominal is True
    assert isinstance(stream.start, CalendarMonthBoundary)
    assert isinstance(stream.end, PersonAgeBoundary)
    assert stream.end.age_months == age_months
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest packages/core/tests/test_plan_streams.py -v`
Expected: FAIL with `AttributeError`/`ValidationError` — `Plan` has no `manual_income_streams` (logical, the symbols exist). After Step 3 it passes.

- [ ] **Step 3: Add the field to `Plan`**

Modify `packages/core/core/models.py`. Add the import and field:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from core.streams import TimedStream


class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold


class Portfolio(BaseModel):
    current_savings_balance: Decimal = Field(ge=0)


class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    manual_income_streams: list[TimedStream] = Field(default_factory=list)
```

- [ ] **Step 4: Export `TimedStream` from the package**

Modify `packages/core/core/__init__.py`:

```python
"""Plan model and SQLite persistence."""

from core.defaults import default_plan
from core.models import Plan
from core.repository import PlanRepository
from core.streams import TimedStream

__all__ = ["Plan", "PlanRepository", "TimedStream", "default_plan"]
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest packages/core/tests/test_plan_streams.py -v`
Expected: PASS (1 test)

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/models.py packages/core/core/__init__.py packages/core/tests/test_plan_streams.py
git commit -m "feat(core): persist dormant manual_income_streams on Plan"
```

---

## Task 5: Complete `domain` package `OVERVIEW.md`

The `domain` package skeleton (pyproject, `__init__.py`, scaffold test) already exists from Phase 0. This task adds the legacy port map and records the real/nominal/growth + sabbatical contract pointers.

**Files:**
- Create: `packages/domain/OVERVIEW.md`

- [ ] **Step 1: Create the OVERVIEW**

Create `packages/domain/OVERVIEW.md`:

```markdown
# Domain Package — Overview

Ported legacy finance logic that produces unified timed income/spending streams
and tax-adjusted cashflows. Depends only on `core`. Never imports `web`.

## Stream primitive

Income and spending sources are built from `core.streams.TimedStream` and
projected with `core.timeline.project_stream`. See the Phase 2a design spec:
`docs/superpowers/specs/2026-06-12-phase-2a-domain-core-design.md`.

- **Real vs nominal (spec §6):** `is_nominal=False` => today's dollars, inflation
  applied by the simulation layer, growth is a real raise. `is_nominal=True` =>
  fixed nominal dollars, inflation not applied, growth is a nominal raise.
- **Future-dated nominal anchoring is NOT supported** (spec §6) — only add a
  3-way mode when a consumer needs it.
- **Composition (spec §6.1):** features that modify income over a sub-window
  (e.g. planned sabbaticals — break or % reduction) are expressed by composing
  multiple `TimedStream` segments, honoring the growth re-anchoring rule (§4).

## Legacy port map

| Legacy module | Destination | Phase | Status |
|---------------|-------------|-------|--------|
| `social_security.py` | `domain/social_security/` | 2b | not started |
| `job_income.py` (incl. planned sabbaticals) | `domain/job_income/` | 2c | not started |
| `pension.py` | `domain/pension/` | 2d | not started |
| `taxes.py` (income-side) | `domain/taxes/` | 2d | not started |
| `build_monthly_cashflows(plan)` aggregator | `domain/__init__.py` | 2d | not started |

Port pattern: adapt legacy tests -> implement with monthly boundaries -> wire to
the engine.
```

- [ ] **Step 2: Verify the domain package still imports**

Run: `uv run pytest packages/domain/tests/test_domain_scaffold.py -v`
Expected: PASS (unchanged scaffold test)

- [ ] **Step 3: Commit**

```bash
git add packages/domain/OVERVIEW.md
git commit -m "docs(domain): add OVERVIEW port map and stream contract pointers"
```

---

## Task 6: Full verification and index update

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (mark Phase 2a complete; update active phase + completed table)

- [ ] **Step 1: Run the full suite and linters**

Run: `make`
Expected: ruff (lint + format check) passes, pyright passes, all pytest tests pass across `core`, `domain`, `simulation`, `web`.

If pyright flags the `Decimal ** Decimal` power in `project_stream`, confirm the annotation is `Decimal` end-to-end (no `float` leaks) before changing anything.

- [ ] **Step 2: Update the rebuild index**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`:
- Check off the Phase 2a exit-criteria boxes.
- Set the **Active phase** table to Phase 2b (plan) and **Next action** to "Write Phase 2b plan before coding".
- Add Phase 2a to the **Completed plans** table with `status: complete`.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "docs: mark Phase 2a complete; advance active phase to 2b"
```

---

## Spec coverage check

| Spec section | Task(s) |
|--------------|---------|
| §3 `TimedStream` + boundaries | Task 1 |
| §4 `Timeline` indexing + `project_stream` | Tasks 2, 3 |
| §5 `Plan.manual_income_streams` + repository round-trip | Task 4 |
| §6 / §6.1 real-nominal-growth + sabbatical contract (documented) | Task 5 (OVERVIEW) + spec docstrings in Task 1/3 |
| §7 `domain` skeleton (already exists) + OVERVIEW | Task 5 |
| §9 testing (serialization, indexing, projection, round-trip, delegation) | Tasks 1–4 |
| Decision #9 horizon consolidation | Task 2 |
| Exit criteria + `make` | Task 6 |
```

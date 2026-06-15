# Phase 2b — Domain: Job Income Design

**Date:** 2026-06-15
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-12-phase-2a-domain-core-design.md](./2026-06-12-phase-2a-domain-core-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-2b-domain-job-income.md` *(to write after spec approval)*

---

## 1. Goal & scope

Port legacy `job_income.py` onto the Phase 2a `TimedStream` foundation.

A person can hold **multiple jobs** (concurrent or sequential). Each job grows with
raises and can have **per-job sabbatical windows** (a full break or a partial
reduction over a window). Phase 2b delivers:

1. **Plan-config models** (`Job`, `SabbaticalWindow`) persisted on the `Plan`.
2. A **domain projection** (`project_job_income`) that compiles jobs into
   month-indexed series for downstream consumers.

Phase 2b is **not** responsible for: system-level retirement state,
`try_to_optimize`, the Social Security wage-base cap (Phase 2c), tax computation
(Phase 2d), `build_monthly_cashflows` aggregation (Phase 2d), inflation
(simulation layer), nominal jobs, or any editor/UI.

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Multiple jobs per person**, concurrent or sequential | Real users hold more than one job over time and at once; the projection sums them per person |
| 2 | **Per-job sabbatical windows** (not per-person) | Keeps the segment math local to one job's growth curve; a "real" full sabbatical is a window on each active job |
| 3 | Sabbatical severity = **`remaining_fraction` 0..1** (0 = full break, 0.5 = half pay) | One field expresses both full break and partial reduction |
| 4 | During a sabbatical the **raise clock keeps running** | Person returns at the grown salary; this is exactly the Phase 2a §6.1 re-anchoring rule, so segments stitch into one continuous curve |
| 5 | **Annual dollars** on the `Job`, compiled to monthly (÷12) | Matches how users enter salary and 401k/HSA limits |
| 6 | **Smooth monthly-compounded growth**, reusing `project_stream` | No legacy calendar-year step-ups; we are not chasing legacy numeric parity |
| 7 | Tax-deferred **stored as the user's annual dollar amount**, modeled **internally as a fraction** of base income | Users understand dollar limits; fractional modeling makes deferral scale with raises and sabbatical reductions (legacy effective behavior). Fixed inflation-only-growth dollars considered and **deferred** (not worth the complexity) |
| 8 | Keep per-job **`social_security_eligible` flag** | Models SS-covered vs non-covered employment; this fact cannot be reconstructed from a summed gross series |
| 9 | Projection exposes **per-person breakdowns + household totals** | SS (2c) computes PIA per individual; taxes/cashflows (2d) want household aggregates |
| 10 | `Job` / `SabbaticalWindow` live in **`core`** | `Plan` persists them through the JSON-blob repository, exactly like `TimedStream` |
| 11 | **Real-only** jobs (`is_nominal=False`); `annual_raise` is a real raise | Nominal jobs deferred (YAGNI) |
| 12 | **No system-level retirement state** | Per rebuild-index exit criteria; "retired" is just an absence of income, not a flag |

---

## 3. Config models (`core`)

`Job` and `SabbaticalWindow` live in `core` because `Plan` persists them through
the existing JSON-blob repository (no schema migration — the `plans` column
already stores `Plan.model_dump_json()`), exactly as `TimedStream` does.

```python
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
    start: Boundary | None = None          # None => plan start (month_index 0, "now")
    end: Boundary | None = None            # None => plan horizon end
    social_security_eligible: bool = True
    sabbaticals: list[SabbaticalWindow] = Field(default_factory=list)
```

`PersonHousehold` gains one field:

```python
class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)   # NEW
```

The default plan leaves `jobs` empty; existing default-plan behavior is unchanged.

### Validation
- Field-level: `annual_income >= 0`, `annual_tax_deferred >= 0`,
  `remaining_fraction in [0, 1]`.
- Model-level on `Job`: `annual_tax_deferred <= annual_income`.
- **Sabbatical windows** must resolve (via the timeline) to ranges that are
  inside `[job start, job end]`, ordered, and non-overlapping. Boundary-to-index
  resolution needs a `Timeline`, so these structural checks live in the
  **compiler** (§4) and raise a clear domain error, not in Pydantic field
  validators.

---

## 4. Compilation: `Job` → segmented `TimedStream`s (`domain`)

A job with *N* sabbatical windows compiles into up to *2N+1* `TimedStream`
segments (full / reduced / full / …). Each segment reuses the Phase 2a
`project_stream`, so **all growth math lives in one place**.

Re-anchoring (Phase 2a §6.1) makes the segments stitch into one continuous curve
with the raise clock running underneath the whole job:

```
base_monthly      = annual_income / 12
segment_base(s)   = base_monthly
                    * remaining_fraction(s)
                    * (1 + annual_raise) ** ((segment_start_index - job_start_index) / 12)
```

Each segment becomes:

```python
TimedStream(
    monthly_amount=segment_base,
    start=<segment start boundary>,
    end=<segment end boundary>,
    annual_growth_rate=annual_raise,
    is_nominal=False,
)
```

`project_stream` then compounds within the segment, yielding a continuous
`base_monthly * (1 + annual_raise) ** ((t - job_start_index) / 12)` curve, scaled
by `remaining_fraction` inside windows. Outside `[job start, job end]` the series
is zero.

**`job_start_index`** is `0` when `Job.start is None`, else
`timeline.index_of(job.start)`. The growth anchor is the job start, **not** the
clamped/visible window, so a job that started in the past still grows correctly
into the visible horizon.

### `core.timeline.month_boundary` helper (new)

To build segment streams from computed month indices while still reusing
`project_stream` (rather than re-implementing growth), add the inverse of the
today-offset:

```python
def month_boundary(self, index: int) -> CalendarMonthBoundary:
    """The calendar month at `index` months from today (index 0 == this month)."""
```

The compiler computes integer segment start/end indices, then converts them to
`CalendarMonthBoundary` for each segment's `TimedStream`. This keeps a single
growth implementation and a single index↔calendar mapping.

---

## 5. Output: `JobIncomeProjection` (the Phase 2b deliverable)

```python
def project_job_income(plan: Plan, timeline: Timeline) -> JobIncomeProjection: ...
```

```python
class PersonJobIncome(BaseModel):     # all lists length == timeline.horizon_months
    gross: list[Decimal]              # all of the person's jobs, summed
    ss_covered_gross: list[Decimal]   # gross from jobs with social_security_eligible=True, else 0
    tax_deferred: list[Decimal]       # sum over jobs of gross_job * (annual_tax_deferred / annual_income)


class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome

    # household totals (element-wise sums), e.g. as computed properties:
    #   total_gross, total_ss_covered_gross, total_tax_deferred
```

- **Per-person** because SS (2c) computes PIA per individual.
- **`ss_covered_gross` is UNCAPPED.** It is "earnings from SS-covered jobs"; the
  Social Security wage-base / taxable-maximum cap is applied **downstream in
  Phase 2c**, never here. The field docstring states this so the boundary is
  unambiguous.
- **`tax_deferred`** uses the per-job fraction `annual_tax_deferred / annual_income`
  (guard divide-by-zero when `annual_income == 0` → fraction 0), applied to that
  job's already-grown, already-sabbatical-scaled monthly gross, then summed. It
  therefore scales with raises and reductions automatically.
- **Concurrent jobs** are summed element-wise per person; **sequential jobs**
  simply occupy disjoint windows.
- Household totals are element-wise sums of the two persons' series.

---

## 6. File layout (delta from current tree)

```
packages/core/
├── core/
│   ├── job.py            # NEW — Job, SabbaticalWindow
│   ├── models.py         # + PersonHousehold.jobs
│   ├── streams.py        # unchanged (Boundary reused)
│   └── timeline.py       # + Timeline.month_boundary(index)
└── tests/
    ├── test_job.py        # NEW — config validation, repository round-trip
    └── test_timeline.py   # + month_boundary behavior

packages/domain/
├── domain/
│   └── job_income/
│       ├── __init__.py    # project_job_income, JobIncomeProjection, PersonJobIncome
│       └── compile.py     # Job -> segmented TimedStreams (re-anchoring, window split)
├── tests/
│   └── test_job_income.py # NEW
└── OVERVIEW.md            # job_income status -> in progress / done
```

---

## 7. Testing (TDD, one behavior per test)

Per repo testing policy: behavior test first, scaffold to a *logical* red, then
implement. Inject `today: date`. Pull shared values from source; never duplicate
a literal across arrange and assert.

| Area | Representative behaviors |
|------|--------------------------|
| `Job` validation | `annual_tax_deferred > annual_income` rejected; `remaining_fraction` outside `[0,1]` rejected |
| Repository round-trip | `Plan` with `PersonHousehold.jobs` (incl. sabbaticals + `Decimal`) → SQLite → equal |
| `Timeline.month_boundary` | `month_boundary(index)` is the inverse of `index_of(CalendarMonthBoundary)` for sample indices |
| Single job | annual→monthly conversion; flat-then-grown monthly series matches `base*(1+raise)^(t/12)` |
| Concurrent jobs | two overlapping jobs sum element-wise per person |
| Sequential jobs | disjoint windows, no overlap, zero between |
| Full break (`remaining=0`) | window zeroed; **post-break value equals the no-break curve at that month** (re-anchoring proven) |
| Partial reduction | window scaled by `remaining_fraction`; growth still compounds underneath |
| `ss_covered_gross` | excludes jobs with `social_security_eligible=False`; **no cap applied** |
| `tax_deferred` | equals `gross * (annual_tax_deferred/annual_income)`; scales with growth and reductions; `annual_income==0` → 0 |
| Household totals | equal element-wise per-person sums |

Do **not** test pure Pydantic validation of trivial fields or library behavior.

---

## 8. Error handling

| Situation | Behavior |
|-----------|----------|
| Sabbatical window outside `[job start, job end]` | Compiler raises a clear domain `ValueError` |
| Overlapping / out-of-order sabbatical windows | Compiler raises a clear domain `ValueError` |
| `annual_tax_deferred > annual_income` | Pydantic `ValidationError` at model construction |
| `annual_income == 0` | Allowed (zero-income placeholder job); tax-deferred fraction is 0 |
| Job window entirely in the past / beyond horizon | All-zero contribution (via `project_stream` clamping), no error |
| Unknown boundary `kind` in stored JSON | Pydantic discriminated-union `ValidationError`, surfaced by repo as today |

---

## 9. Exit criteria (from rebuild index, made concrete)

- [ ] `Job` + `SabbaticalWindow` in `core`, persisted on `PersonHousehold.jobs`, round-trip through SQLite (proven by test)
- [ ] Job income projects to month-indexed series via `project_job_income`, reusing `project_stream`
- [ ] Planned sabbaticals: full break and % reduction, composed from segmented streams with correct growth re-anchoring (raise clock continues)
- [ ] Per-person `gross` / `ss_covered_gross` / `tax_deferred` + household totals
- [ ] `ss_covered_gross` is uncapped; wage-base cap explicitly deferred to Phase 2c
- [ ] No system-level retirement state
- [ ] `Timeline.month_boundary` added and tested as the inverse of the offset
- [ ] `packages/domain/OVERVIEW.md` documents job-income port status
- [ ] `make` (lint + test) passes

---

## 10. Deferred (explicitly out of 2b)

- **Nominal jobs** and future-dated nominal anchoring (Phase 2a §6 deferral stands).
- **Tax-deferred as fixed inflation-only-growth dollars** — the alternative raised
  in brainstorming; considered, not worth the added complexity now.
- **The SS wage-base cap** — Phase 2c.
- **Tax computation** and `build_monthly_cashflows` aggregation — Phase 2d.
- **`try_to_optimize`**, system-level retirement state — dropped.
- **Editor sections** for jobs — Phase 4.
- **Inflation application** — Phase 3a+.

---

## 11. Next step

After spec approval: invoke **writing-plans** to produce
`docs/superpowers/plans/2026-06-12-phase-2b-domain-job-income.md`, then execute
via subagent-driven development.

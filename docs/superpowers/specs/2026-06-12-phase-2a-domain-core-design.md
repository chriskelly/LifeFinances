# Phase 2a — Domain Core Types & Timed Streams Design

**Date:** 2026-06-14
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-2a-domain-core.md` *(to write after spec approval)*

---

## 1. Goal

Establish the foundational, reusable building blocks that every income/spending
source in the simulator will sit on:

1. A **lean timed-stream type** (`TimedStream`) that future modules
   (Social Security, job income, pension, manual income, extra spending) all
   reuse.
2. A **timeline utility** that converts human-meaningful boundaries (a calendar
   month, or a person's age) into a `month_index` relative to today.
3. A **projection mechanic** (`project_stream`) that turns one stream into a
   month-indexed series of face amounts.
4. A **`domain` package skeleton** so Phase 2b can start cleanly.

Phase 2a is **not** responsible for any finance logic (SS/job/pension/tax),
`build_monthly_cashflows`, extra-spending plan fields, inflation handling, any
UI/editor, or growth consumers. Those arrive in 2b–4.

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Lean** monthly-recurring stream type | Smallest correct foundation; richer tpaw timing (one-time, every-X-months, named ages) deferred until a consumer needs it |
| 2 | Stream type + timeline + projection **all live in `core`** | Month-indexing is generic calendar math on `Plan`, not finance domain logic; needs nothing beyond `stdlib + pydantic` |
| 3 | Files: `core/streams.py` (type) + `core/timeline.py` (calendar/index + projection) | Keeps `core/models.py` focused on `Plan` |
| 4 | Boundary = **discriminated union** `CalendarMonth \| PersonAge` | Covers job-income end-date and SS claiming-age cleanly; mirrors tpaw's `Month` in lean form |
| 5 | Wire **`Plan.manual_income_streams: list[TimedStream] = []`** now | Real, intended field (annuities/rental per parent §3); proves the discriminated-union + `Decimal` round-trips through the JSON-blob SQLite repository. Persisted but **not consumed or editable** in 2a |
| 6 | **Include** `annual_growth_rate`, **monthly-compounded** | User chose growth now; smooth `(1+rate)^(t/12)` ramp |
| 7 | Keep **`is_nominal`** as carried metadata | Free flag, documents real-vs-nominal intent; `simulation` consumes it later |
| 8 | **Orthogonal real/nominal + growth contract** (tpaw-style) | See §6; supports both fixed-nominal annuities and raises-above-inflation |
| 9 | **Consolidate** horizon math into `core.timeline`; `simulation.horizon` delegates | Single source of truth; avoids drift with the formula shipped in Phase 1 |

---

## 3. `core/streams.py` — the timed-stream type

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

    Amounts are expressed in the stream's own basis (see design §6); inflation
    is NOT applied here — that is a simulation-layer concern.
    """

    label: str | None = None
    monthly_amount: Decimal = Field(ge=0)
    start: Boundary | None = None   # None => plan start (month_index 0, "now")
    end: Boundary | None = None     # None => runs to the plan horizon end
    is_nominal: bool = False        # False => real (today's $); True => fixed nominal $
    annual_growth_rate: Decimal = Decimal(0)
```

### Notes
- `PersonId` is shared; `Household` keeps its `person1`/`person2` attribute names,
  and boundaries reference persons by this literal.
- No `id` / `sortIndex` / `colorIndex` (tpaw UI concerns) and no ordering/overlap
  validation in 2a — deferred until an editor or aggregator needs them.
- `monthly_amount` and `annual_growth_rate` are `Decimal` for exact persistence.

---

## 4. `core/timeline.py` — month indexing + projection

A `Timeline` is built from a `Plan` plus an **injectable `today: date`** (per the
testing policy — no wall-clock reads inside logic).

### Conventions
- `month_index = 0` is the **current calendar month** (`today.year`, `today.month`).
- A calendar month `(y, m)` maps to `(y - today.year) * 12 + (m - today.month)`.
  Indices before today are **negative** and treated as outside the visible window.
- `horizon_months` = months from today to the **later** of the two persons'
  max-age month — identical to the formula shipped in `simulation/horizon.py`
  (Phase 1). The projected series has length `horizon_months`, valid indices
  `0 .. horizon_months - 1`.

### Surface (illustrative)

```python
class Timeline:
    def __init__(self, plan: Plan, *, today: date | None = None) -> None: ...

    @property
    def horizon_months(self) -> int: ...

    def index_of(self, boundary: Boundary) -> int:
        """Resolve a boundary to a month_index relative to today.

        - CalendarMonthBoundary: direct offset from today.
        - PersonAgeBoundary: the month the person reaches `age_months`
          (birth month + age_months), expressed as an offset from today.
        """
```

`PersonAgeBoundary` resolution uses the person's `birth_year` / `birth_month`
from the plan's `Household`. A small "add N months to (year, month)" helper backs
both the boundary math and horizon.

### `project_stream`

```python
def project_stream(stream: TimedStream, timeline: Timeline) -> list[Decimal]:
    """Project one stream into a month-indexed series of FACE amounts.

    - Length == timeline.horizon_months.
    - Fills `monthly_amount` for indices in [start_index, end_index]; 0 elsewhere.
        - start defaults to 0 (plan start / "now").
        - end defaults to horizon_months - 1.
        - the window is clamped to [0, horizon_months - 1].
    - Applies monthly-compounded growth: amount(t) = monthly_amount *
      (1 + annual_growth_rate) ** ((t - start_index) / 12), for t in window.
    - Does NOT apply inflation. The series is in the stream's own basis; the
      `is_nominal` flag is carried by the caller for the simulation layer.
    """
```

Growth is anchored at the stream's **start index** (the first in-window month is
the base amount). The implementation plan will pin a fixed `Decimal`
quantization for the growth factor so projections are deterministic and testable.

> **Composition constraint (relevant to segmented streams, e.g. sabbaticals).**
> Because growth re-anchors at each stream's own `start`, a single logical income
> that is split into segments (see §6.1) must have each later segment's
> `monthly_amount` set to the **already-grown** value at that segment's start —
> `base * (1 + g) ** (segment_start_index / 12)` — so the segments stitch back
> into one continuous `base * (1 + g) ** (t / 12)` curve. This is a **consumer**
> (Phase 2c) responsibility; `core` only projects each stream independently.

---

## 5. `Plan` schema change

`core/models.py` gains one field:

```python
class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    manual_income_streams: list[TimedStream] = []
```

- **Persisted** via the existing JSON-blob repository (no migration of the
  `plans` table; the column already stores `Plan.model_dump_json()`).
- **Not consumed** (no aggregator/engine reads it until 2b–3) and **not
  editable** (no editor section until a later phase). This is intentional and
  documented so the field is not mistaken for a wired-up feature.
- The default factory in `core/defaults.py` leaves it empty (`[]`); existing
  default-plan behavior is unchanged.

The dated-plan fields and per-person end age (`birth_month`, `birth_year`,
`max_age_years=100`) required by the rebuild-index exit criteria already exist
from Phase 1; 2a does not change them.

---

## 6. Real vs nominal vs growth — the contract

Two **independent** concepts, kept orthogonal:

1. **Inflation indexing** — encoded by `is_nominal`:
   - `is_nominal=False` (**real**): `monthly_amount` is in **today's dollars**;
     the simulation layer **applies** the inflation path so purchasing power is
     preserved. `annual_growth_rate` is a **real** raise (growth *above*
     inflation).
   - `is_nominal=True` (**nominal**): `monthly_amount` is **fixed actual
     dollars**; the simulation layer does **not** apply inflation, so real value
     erodes over time. `annual_growth_rate` is a **nominal** raise.
2. **Explicit growth** — `annual_growth_rate`, always expressed **in the
   stream's own basis** (real for real streams, nominal for nominal streams).

This supports both ends of the spectrum:
- A **COLA'd salary with raises above inflation** → `is_nominal=False`,
  `annual_growth_rate` = the real raise.
- A **fixed (non-COLA) annuity or pension** that pays a flat dollar amount
  forever while its real value erodes → `is_nominal=True`,
  `annual_growth_rate=0`.

Entering a "nominal starting value as of today" is **not a separate case**: at
`month_index 0` today's nominal dollars equal today's real dollars, so it is
simply the real case.

### Explicitly NOT supported in 2a (documented to avoid confusion)

> **Future-dated nominal anchoring is not supported.** There is no way to enter
> an amount "in *future* dollars at a future start month and then index it to
> inflation thereafter" — e.g. *"my pension begins in 2040 and will be \$5,000/mo
> in 2040 dollars, growing with inflation after that."*
>
> This is a genuinely distinct third behavior that a boolean `is_nominal` cannot
> express. It is **deliberately deferred**. Supporting it later requires
> replacing the boolean with a 3-way mode (e.g. `real` / `fixed_nominal` /
> `nominal_anchored_then_indexed`), and should only be added when a consumer
> actually needs it.
>
> During brainstorming this was easy to conflate with "a nominal starting
> value." It is not the same thing: a nominal value *as of today* is already the
> real case (factor = 1 at t=0); the unsupported case is a nominal value *as of a
> future month*.

`core` never applies inflation. The contract above is what `core` **documents**
for `simulation` to honor; `project_stream` only emits face amounts with growth.

### 6.1 Why the primitive stays minimal — expressing features by composition

The lean `TimedStream` is deliberately a single bounded window with one
`monthly_amount`. Higher-level features that modify income over a sub-window are
expressed by **composing multiple streams** at the consumer layer, not by adding
timing variants to the primitive.

The motivating example is **planned sabbaticals** (a future Phase 2c feature):
an income break, or a percentage reduction, over a defined window.

- **Full break** → two streams: the job stream ending at the sabbatical start,
  plus another starting at the sabbatical end.
- **Percentage reduction** (e.g. 50% pay) → three non-negative segments
  (full / reduced / full), summed by the aggregator. `monthly_amount >= 0` is
  never violated.

This confirms 2a needs **no** new boundary kinds, one-time/every-X-months timing,
or a first-class "reduction window" for sabbaticals. The only constraint a
consumer must honor is the growth re-anchoring rule in §4 (back-compute each
later segment's base). If segment-composition ever proves too unwieldy for a
real consumer, a richer per-stream modifier can be added then — not now.

---

## 7. `domain` package skeleton

Create `packages/domain/` as a uv-workspace member that depends on `core`:

```
packages/domain/
├── pyproject.toml          # name = "domain"; depends on core
├── domain/
│   └── __init__.py         # empty (no logic in 2a)
├── OVERVIEW.md             # legacy port map placeholder (Phase 2 backlog)
├── AGENTS.md               # optional; package boundary reminder
└── tests/
    └── __init__.py
```

- Registered in the workspace root `pyproject.toml` / `uv` members so
  `web → domain → core` is importable in later phases.
- `OVERVIEW.md` seeded with the legacy→destination port table from the parent
  spec §7 (status: not started).
- **No** domain logic, no `build_monthly_cashflows` — those are 2b–2d.

---

## 8. File layout (delta from current tree)

```
packages/core/
├── core/
│   ├── models.py        # + manual_income_streams on Plan; + PersonId reuse
│   ├── streams.py       # NEW — TimedStream, boundaries
│   ├── timeline.py      # NEW — Timeline, index_of, horizon, project_stream
│   ├── defaults.py      # unchanged behavior (empty streams)
│   └── repository.py    # unchanged
└── tests/
    ├── test_streams.py    # NEW
    ├── test_timeline.py   # NEW
    └── test_repository.py # + round-trip with manual_income_streams

packages/simulation/
└── simulation/
    └── horizon.py       # delegates to core.timeline (public fn preserved)

packages/domain/         # NEW skeleton (see §7)
```

---

## 9. Testing (TDD, one behavior per test)

Per repo testing policy: write the behavior test first, scaffold to a *logical*
red, then implement. Inject `today: date`. Pull shared values from source; do not
duplicate literals across arrange/assert.

| Area | Representative behaviors |
|------|--------------------------|
| `TimedStream` serialization | round-trips via `model_dump_json` / `model_validate`; discriminated boundary union resolves to the correct `kind`; `Decimal` fields preserved |
| `Timeline.index_of` | calendar-month offset (incl. negative for past months); person-age boundary resolves to birth-month + `age_months` offset |
| `Timeline.horizon_months` | equals the later person's max-age offset; matches `simulation.horizon` for the same plan/today |
| `project_stream` | length == horizon; flat fill over default window; bounded window honored; window clamped to `[0, horizon-1]`; monthly-compounded growth at the start anchor; zero outside window |
| Repository round-trip | `Plan` with `manual_income_streams` → SQLite → back yields equal streams (incl. boundary kinds + `Decimal`) |
| `simulation.horizon` delegation | existing Phase 1 horizon tests still pass after delegating to `core.timeline` |

Do **not** test pure Pydantic validation or trivial getters.

---

## 10. Error handling

| Situation | Behavior |
|-----------|----------|
| Boundary with unknown `kind` in stored JSON | Pydantic discriminated-union `ValidationError`; repository surfaces it as it does today (no crash) |
| `PersonAgeBoundary` referencing a person | always valid — both `person1`/`person2` exist in `Household` |
| Calendar month out of `1..12` | Pydantic field validation |
| Stream window entirely in the past / beyond horizon | `project_stream` returns all-zero series of horizon length (no error) |

---

## 11. Exit criteria (from rebuild index, made concrete)

- [ ] `TimedStream` (lean `LabeledAmountTimed` equivalent) defined in `core/streams.py`
- [ ] `Boundary` discriminated union (`CalendarMonth` / `PersonAge`) with month indexing in `core/timeline.py`
- [ ] `project_stream` produces face-amount series with monthly-compounded growth, no inflation
- [ ] `Plan.manual_income_streams` persists and round-trips through SQLite (proven by test)
- [ ] Plan retains dated-plan fields + per-person end age (default 100) — unchanged from Phase 1
- [ ] `core.timeline` is the single source of horizon math; `simulation.horizon` delegates and its Phase 1 tests still pass
- [ ] `packages/domain` skeleton importable, depends on `core`, with `OVERVIEW.md` port map
- [ ] Unit tests for stream serialization and month indexing pass
- [ ] `make` (lint + test) passes
- [ ] Real/nominal/growth contract and the unsupported future-dated-nominal case documented (in `OVERVIEW.md` or stream docstrings)

---

## 12. Deferred (explicitly out of 2a)

- One-time amounts, `every-X-months` recurrence, named-age boundaries
  (`lastWorkingMonth`/`retirement`), `inThePast` timing — add per consumer need.
- **Planned sabbaticals** (income break / % reduction over a window) — expressed
  by stream composition (§6.1); the feature itself lands in Phase 2c (job income).
- `id` / `sortIndex` / `colorIndex` and stream ordering/overlap validation — add
  with the editor.
- Future-dated nominal anchoring (the 3-way mode) — see §6.
- `build_monthly_cashflows`, SS/job/pension/tax logic — Phase 2b–2d.
- Any inflation application — Phase 3a+.
- Editor sections for streams — Phase 4.

---

## 13. Next step

After spec approval: invoke **writing-plans** to produce
`docs/superpowers/plans/2026-06-12-phase-2a-domain-core.md`, then execute via
subagent-driven development.

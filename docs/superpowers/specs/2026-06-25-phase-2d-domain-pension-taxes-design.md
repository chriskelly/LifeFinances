# Phase 2d — Domain: Pension and Taxes Design

**Date:** 2026-06-25
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-23-phase-2c-domain-social-security-design.md](./2026-06-23-phase-2c-domain-social-security-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-2d-domain-pension-taxes.md` *(to write after spec approval)*
**Follow-up:** Phase 2e — optional `person2` and filing-status wiring (see rebuild index)

---

## 1. Goal & scope

Port legacy pension and income-side tax logic onto the Phase 2a–2c monthly domain
foundation, and deliver `domain.build_monthly_cashflows(plan)` — the aggregator
that assembles all income sources, applies income-side taxes, and returns
month-indexed net cashflows for the simulation layer.

Phase 2d includes:

1. **Job-attached formula defined-benefit pension** — generic model with CalSTRS
  defaults; single source of truth with the pensionable job.
2. **Manual pension path** — reuse existing `Plan.manual_income_streams`.
3. **Income-side taxes** — federal + state (CA, NY, none), FICA, flat SS/pension
  inclusion; annual aggregation with monthly distribution.
4. **Household `filing_status`** — user-configurable MFJ vs single; taxes honor it
  now; auto-wiring to household size deferred to Phase 2e.
5. `**build_monthly_cashflows**` aggregator API.

Phase 2d does **not** include:

- Portfolio / withdrawal / capital-gains taxes (income-side only per architecture
spec §6 item 9).
- Optional `person2` / single-person households (Phase 2e).
- Inflation application to benefit or tax streams (simulation layer, Phase 3).
- Provisional-income SS taxation (kept simple via flat inclusion fraction).
- Pension or tax editor UI (Phase 4).

Dropped from legacy pension:

- Admin-specific hardcoded benefit-rate tables keyed by calendar year (2043–2053).
- **Net-worth claiming strategy** — simulation-state-dependent; same rationale as
dropping SS net-worth claiming in Phase 2c.
- **Cash-out lump-sum strategy** — one-time payout; users model via manual income
stream if needed.

---

## 2. Decisions captured from brainstorming


| #   | Decision                                               | Rationale                                                                                                                                   |
| --- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **Job-attached formula DB pension**                    | Single source of truth: job end date, salary, raises, and sabbaticals drive service credit and final compensation automatically             |
| 2   | **Age-factor tables in `domain/statutory/pension.py`** | CalSTRS and future agency tables (railroad, etc.) live alongside SS/tax statutory data; plans reference a table or supply a custom override |
| 3   | **Manual pensions via `manual_income_streams`**        | No new model; a manual pension is a labeled `TimedStream`                                                                                   |
| 4   | **Annual tax aggregation, monthly distribution**       | Progressive brackets need real annual totals; uneven within-year income (job ends mid-year) handled correctly                               |
| 5   | **Flat SS/pension inclusion fraction**                 | Matches legacy `DISCOUNT_ON_PENSION_TAX`; configurable `taxable_fraction` (default 0.80)                                                    |
| 6   | **CA + NY + none state support**                       | Matches legacy coverage; statutory-table pattern from Phase 2c                                                                              |
| 7   | `**Household.filing_status` field now**                | Taxes select brackets/deductions from explicit MFJ or single; default MFJ                                                                   |
| 8   | **Keep `person2` required in 2d**                      | Avoids cross-cutting SS spousal / job-income changes; Phase 2e makes `person2` optional and wires filing status to household size           |
| 9   | **Keep FICA**                                          | Medicare 1.45% + SS payroll 6.2% to wage base on job gross; genuinely income-side                                                           |
| 10  | **Return projected series, not `TimedStream`s**        | Pension formula output and tax breakdowns are clearer as deterministic monthly series                                                       |
| 11  | **`stored_total` for sum series**                      | Pension and tax month-totals computed once at projection/compute time; name signals snapshot (not live-derived) and avoids O(n) re-sum on each access |


**Naming note:** `SocialSecurityProjection` already exposes a stored `total` from Phase 2c. New pension and tax models use `stored_total` for the same snapshot semantics with an explicit name.
---

## 3. Pension — job-attached formula DB

### Config models (`core`)

Pension config attaches to the pensionable `Job`, not as a free-floating person field.

```python
from decimal import Decimal
from pydantic import BaseModel, Field

from core.streams import Boundary


class AgeFactor(BaseModel):
    """Defined-benefit age factor at a given age."""

    age_months: int = Field(ge=0)
    factor: Decimal = Field(ge=0)  # e.g. Decimal("0.024") == 2.4%


class FormulaPension(BaseModel):
    """Defined-benefit pension formula attached to a job.

    Benefit = service_credit_years × age_factor × final_compensation.
    All dollar amounts are in today's real dollars (inflation applied by
    simulation layer on the projected benefit stream).
    """

    service_start: Boundary  # start of pensionable service (may predate today)
    claim: Boundary  # benefit start (typically PersonAgeBoundary)
    age_factor_table: list[AgeFactor]  # default from statutory CALSTRS_2_AT_62_AGE_FACTORS
    final_comp_averaging_months: int = Field(default=36, ge=1)
    trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    benefit_real_growth_rate: Decimal = Decimal(0)  # optional real COLA offset
```

`Job` gains one optional field:

```python
class Job(BaseModel):
    # ... existing fields ...
    pension: FormulaPension | None = None
```

### Statutory age-factor tables (`domain/statutory/pension.py`)

Named defined-benefit age-factor tables live under `domain/statutory/`, following
the same versioned source-data pattern as Social Security and tax tables. This
keeps agency-specific factors discoverable in one place and makes it easy to add
other common plans later (e.g. railroad retirement, other public-pension systems)
without touching pension calculation logic.

Phase 2d ships **CalSTRS 2%@62** as `CALSTRS_2_AT_62_AGE_FACTORS`:


| Age | Factor |
| --- | ------ |
| 55y | 0.0116 |
| 56y | 0.0128 |
| 57y | 0.0140 |
| 58y | 0.0152 |
| 59y | 0.0164 |
| 60y | 0.0176 |
| 61y | 0.0188 |
| 62y | 0.0200 |
| 63y | 0.0213 |
| 64y | 0.0227 |
| 65y | 0.0240 |


```python
# domain/statutory/pension.py (illustrative)

SOURCE_NOTES = {
    "calstrs_2_at_62": "CalSTRS 2% at 62 age factors: https://www.calstrs.com/age-factor",
}

CALSTRS_2_AT_62_AGE_FACTORS: tuple[tuple[int, Decimal], ...] = (
    (55 * 12, Decimal("0.0116")),
    # ...
)


def age_factors_from_statutory(
    rows: tuple[tuple[int, Decimal], ...],
) -> list[AgeFactor]:
    """Convert statutory (age_months, factor) rows to plan config models."""
    ...
```

`FormulaPension.age_factor_table` defaults to
`age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)` via a `default_factory`.
Users with other DB plans can either pick a future statutory preset or supply a
custom `age_factor_table` on the job's `FormulaPension` (the persisted plan still
stores the resolved table — statutory modules are the source of shipped defaults,
not runtime lookups).

New agency tables are added as additional named constants in
`domain/statutory/pension.py` (e.g. `RAILROAD_TIER_I_AGE_FACTORS`) with their own
`SOURCE_NOTES` entry; no change to `domain/pension/formula.py` required.

### Computation

Given a job with `FormulaPension`, the pension module:

1. **Projects job gross** (reuses Phase 2b `project_job_gross` for that job).
2. **Service credit years** = years from `service_start` to job `end`, minus
  future sabbatical loss: `Σ (1 − remaining_fraction) × window_years` for each
   sabbatical window. Past unpaid breaks are baked into `service_start`.
3. **Final compensation** = annualized average of projected gross over the
  trailing `final_comp_averaging_months` immediately before job end.
4. **Age factor** = linear interpolation in `age_factor_table` at claim age
  (monthly granularity, same pattern as SS claim multiplier).
5. **Annual benefit** = `service_credit × age_factor × final_compensation`.
6. **Monthly benefit** = `annual_benefit / 12 × trust_factor`, projected as a
  real stream from `claim` through horizon, with optional
   `benefit_real_growth_rate` monthly compounding.

### Manual pension path

Non-formula pensions use `Plan.manual_income_streams` — a labeled `TimedStream`
with appropriate start/end boundaries. No new model.

### Output

```python
class PensionProjection(BaseModel):
    formula: list[Decimal]  # sum of all formula pensions across jobs
    manual: list[Decimal]   # sum of manual_income_streams
    stored_total: list[Decimal]  # formula + manual; snapshot at projection time
```

Public API:

```python
def project_pension(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> PensionProjection: ...
```

---

## 4. Taxes — income-side only

### Household filing status (`core`)

```python
from typing import Literal

FilingStatus = Literal["married_filing_jointly", "single"]


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold  # still required in Phase 2d; optional in Phase 2e
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus = "married_filing_jointly"
    residence_state: str | None = None  # "California", "New York", or None
    ss_pension_taxable_fraction: Decimal = Field(
        default=Decimal("0.80"), ge=0, le=1
    )  # fraction of SS + pension included in income tax base
```

Tax bracket selection and standard deductions use `household.filing_status` directly.
Phase 2e will auto-set `filing_status` from household size when `person2` becomes
optional; until then users set it explicitly.

### Statutory tables (`domain/statutory/taxes.py`)

Follow the Phase 2c statutory-data pattern:

- **Current sets** (replaced yearly, `LAST_REVIEWED_YEAR` + soft staleness):
  - Federal brackets + standard deduction (MFJ and single).
  - California brackets + standard deduction (MFJ and single).
  - New York brackets + standard deduction (MFJ and single).
  - FICA rates: `MEDICARE_TAX_RATE = 0.0145`, `SOCIAL_SECURITY_TAX_RATE = 0.062`.
- **Reuse** `SS_MAX_EARNINGS_BY_YEAR` from `domain/statutory/social_security.py`
for the FICA SS wage-base cap (no duplication).

Port federal and New York bracket data from legacy `backend/app/data/taxes.py`,
converting legacy thousands values to dollars (multiply caps, cumulative prior
tax, and standard deductions by 1000). California brackets use the current FTB
single and married-filing-jointly schedule (head of household excluded). Bracket
format:
`(rate, highest_dollar_at_rate, cumulative_tax_in_prior_brackets)` — all dollar
amounts are actual dollars, matching the rest of the domain's `Decimal` money
math. Use underscore grouping in literals for readability (e.g.
`Decimal("25_000_001")`).

### Tax computation granularity

1. **Build monthly taxable income** per month:
  - Job taxable = `gross − tax_deferred` (from `JobIncomeProjection`).
  - SS + pension taxable = `(ss.total + pension.stored_total) × ss_pension_taxable_fraction`.
  - Total taxable = job taxable + SS/pension taxable.
2. **Group by calendar year** using `timeline.month_boundary` (same helper
  pattern as SS earnings grouping).
3. **Run progressive brackets once** per calendar year on the year's real total
  taxable income minus the applicable standard deduction (federal + state).
4. **Distribute year's tax back** across months proportional to each month's
  taxable income (zero months get zero share).
5. **FICA** computed monthly (not annualized):
  - Medicare = `MEDICARE_TAX_RATE × job_gross` per month.
  - SS payroll = `SOCIAL_SECURITY_TAX_RATE × min(job_gross, remaining_wage_base)`
  per month, with wage-base cap tracked per calendar year per person.

All amounts are real today's-dollars. Brackets are current-set values in today's
dollars; no inflation adjustment needed in domain.

### Output

```python
class TaxBreakdown(BaseModel):
    federal_income: list[Decimal]
    state_income: list[Decimal]
    fica_medicare: list[Decimal]
    fica_social_security: list[Decimal]
    stored_total: list[Decimal]  # sum of components; snapshot at compute time
```

Public API:

```python
def compute_taxes(
    *,
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
    social_security: SocialSecurityProjection,
    pension: PensionProjection,
) -> TaxBreakdown: ...
```

Tax values are **negative** (outflows), matching legacy sign convention.

---

## 5. Aggregator — `build_monthly_cashflows`

```python
class MonthlyCashflows(BaseModel):
    gross_job: list[Decimal]
    gross_social_security: list[Decimal]
    gross_pension: list[Decimal]
    gross_manual: list[Decimal]
    total_gross: list[Decimal]
    taxes: TaxBreakdown
    net_cashflow: list[Decimal]  # total_gross + taxes.stored_total (taxes are negative)
```

Public API:

```python
def build_monthly_cashflows(
    plan: Plan,
    *,
    today: date | None = None,
) -> MonthlyCashflows: ...
```

Orchestration:

1. `Timeline(plan, today=today)`
2. `project_job_income(plan, timeline)`
3. `project_social_security(plan, timeline, job_income)`
4. `project_pension(plan, timeline, job_income)`
5. Project `manual_income_streams` via `core.timeline.project_stream`
6. `compute_taxes(...)`
7. Assemble `MonthlyCashflows`

All series length == `timeline.horizon_months`. Amounts are real today's-dollars.

---

## 6. File layout

```text
packages/core/
├── core/
│   ├── job.py              # + FormulaPension, AgeFactor; Job.pension
│   └── models.py           # + Household.filing_status, residence_state,
│                           #   ss_pension_taxable_fraction
└── tests/
    └── test_pension_config.py

packages/domain/
├── domain/
│   ├── statutory/
│   │   ├── pension.py      # CALSTRS_2_AT_62_AGE_FACTORS; future agency tables
│   │   └── taxes.py        # federal + CA/NY brackets, deductions, FICA rates
│   ├── pension/
│   │   ├── __init__.py     # project_pension, PensionProjection
│   │   └── formula.py      # service credit, final comp, age-factor lookup
│   ├── taxes/
│   │   ├── __init__.py     # compute_taxes, TaxBreakdown
│   │   └── brackets.py     # bracket math, annual aggregate + distribute
│   └── __init__.py         # build_monthly_cashflows, MonthlyCashflows
├── tests/
│   ├── test_pension.py
│   ├── test_taxes.py
│   └── test_cashflows.py
└── OVERVIEW.md             # pension + taxes + aggregator -> done
```

---

## 7. Error handling


| Situation                                      | Behavior                                                                           |
| ---------------------------------------------- | ---------------------------------------------------------------------------------- |
| `trust_factor` outside `[0, 1]`                | Pydantic `ValidationError`                                                         |
| `ss_pension_taxable_fraction` outside `[0, 1]` | Pydantic `ValidationError`                                                         |
| `filing_status` not MFJ or single              | Pydantic `ValidationError`                                                         |
| `residence_state` not CA, NY, or None          | Pydantic `ValidationError` (or allow any string and treat unknown as no state tax) |
| Job has `pension` but no `end` boundary        | `ValueError` — final comp and service credit need a job end                        |
| Empty `age_factor_table`                       | `ValueError` at projection time                                                    |
| Claim age below/above table range              | Extrapolate using nearest table endpoint (clamp)                                   |
| Year taxable income exceeds highest bracket    | `ValueError` with clear message                                                    |
| Timeline has non-positive horizon              | output lists are empty                                                             |
| No formula pension configured                  | `formula` series all zero                                                          |
| No manual income streams                       | `manual` series all zero                                                           |


---

## 8. Testing (TDD, one behavior per test)

Per repo testing policy: behavior test first, scaffold to a logical red, then
implement. Inject `today: date`. Pull shared values from source; never duplicate
a literal across arrange and assert.

### Pension


| Area                   | Behaviors                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Config                 | `FormulaPension` persists on `Job` through repository round-trip                                                        |
| Service credit         | years from `service_start` to job end; sabbaticals reduce credit by `(1 − remaining_fraction) × window`                 |
| Final comp             | trailing `final_comp_averaging_months` average of job gross before end                                                  |
| Age factor             | table lookup at exact age; linear interpolation between rows; default table imported from `domain/statutory/pension.py` |
| Benefit stream         | starts at `claim` boundary; zero before; trust factor scales amount                                                     |
| Single source of truth | changing job end date changes service credit without separate pension config edit                                       |
| Manual path            | `manual_income_streams` included in `PensionProjection.manual`                                                          |


### Taxes


| Area                 | Behaviors                                                            |
| -------------------- | -------------------------------------------------------------------- |
| Filing status        | MFJ vs single selects different brackets and standard deductions     |
| Annual aggregation   | uneven within-year income taxed correctly vs per-month annualization |
| Distribution         | year's tax allocated proportional to monthly taxable income          |
| SS/pension inclusion | `ss_pension_taxable_fraction` scales taxable SS + pension            |
| FICA Medicare        | flat 1.45% on job gross                                              |
| FICA SS              | 6.2% capped at annual wage base per calendar year                    |
| State                | CA brackets applied; NY brackets applied; None → zero state tax      |
| Statutory staleness  | soft `LAST_REVIEWED_YEAR` check on tax tables                        |
| Sign convention      | tax components are negative outflows                                 |


### Aggregator


| Area           | Behaviors                                                             |
| -------------- | --------------------------------------------------------------------- |
| Series length  | all lists == `timeline.horizon_months`                                |
| Net cashflow   | `total_gross + taxes.stored_total` (taxes negative)                          |
| Integration    | sabbatical-reduced job income flows through to SS, pension, and taxes |
| Manual streams | included in `gross_manual` and `total_gross`                          |


---

## 9. Exit criteria

- [x] `FormulaPension`, `AgeFactor` on `Job`; CalSTRS default age-factor table in `domain/statutory/pension.py`.
- [x] `Household.filing_status`, `residence_state`, `ss_pension_taxable_fraction`
  ```
  persist through SQLite round-trip.
  ```
- [x] `project_pension(plan, timeline, job_income)` returns `PensionProjection`.
- [x] Manual pension path via `manual_income_streams`.
- [x] Tax statutory tables in `domain/statutory/taxes.py` with staleness check.
- [x] `compute_taxes(...)` returns `TaxBreakdown`; honors `filing_status`.
- [x] `build_monthly_cashflows(plan)` returns `MonthlyCashflows`.
- [x] `packages/domain/OVERVIEW.md` documents pension + taxes + aggregator status.
- [x] `make` passes.

---

## 10. Deferred to Phase 2e

- Optional `person2` on `Household`.
- Auto-set `filing_status` from household size (MFJ when two people, single when one).
- SS spousal alternatives when partner absent.
- Job income / pension / horizon handling for single-person households.

## 11. Deferred to later phases

- Pension and tax editor UI (Phase 4).
- Inflation application to benefit and tax streams (Phase 3 simulation).
- Provisional-income SS taxation.
- Portfolio / withdrawal taxes.

## 12. Next step

After spec approval: invoke **writing-plans** to produce
`docs/superpowers/plans/2026-06-12-phase-2d-domain-pension-taxes.md`, then
execute via subagent-driven development.
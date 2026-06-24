# Phase 2c — Domain: Social Security Design

**Date:** 2026-06-23
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-12-phase-2b-domain-job-income-design.md](./2026-06-12-phase-2b-domain-job-income-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-2c-domain-social-security.md` *(to write after spec approval)*

---

## 1. Goal & scope

Port legacy `social_security.py` onto the Phase 2a/2b monthly domain foundation.

Phase 2c delivers deterministic Social Security projections from a per-person
claim age, historical SSA earnings records, and Phase 2b projected SS-covered
job income. The output is a month-indexed `SocialSecurityProjection`, mirroring
`JobIncomeProjection`, so Phase 2d can consume SS alongside other income sources.

Phase 2c includes:

1. **Plan-config models** for per-person Social Security claim age and
   historical annual FICA earnings, plus one household-level trust factor.
2. A **pure SSA statement XML parser** that extracts historical capped FICA
   earnings from SSA's exportable XML.
3. A **real-aware benefit calculation**: historical nominal earnings are indexed
   to today's dollars, while future job-income projections are already real and
   are not indexed again.
4. A **monthly claim-age formula** relative to Full Retirement Age 67.
5. **Spousal alternatives** and household totals in the projected output.

Phase 2c does **not** include upload UI or persistence wiring for SSA XML; those
belong in Phase 4 with the rest of the editor/import UI.

Dropped from the legacy model:

- **Net-worth claiming** — it is simulation-state-dependent and conflicts with
  deterministic domain projections.
- **Strategy enum** (`early`, `mid`, `late`, `same`) — replaced by a single
  per-person `claim_age_months` field.
- **WEP / `pension_eligible`** — WEP was repealed in 2025; the rebuild uses only
  the standard PIA formula.

Deferred to later phases:

- Taxation of Social Security benefits (Phase 2d).
- Inflation application to benefit streams (Phase 3 simulation layer).
- SSA XML upload, plan persistence wiring from uploaded files, and editor UX
  (Phase 4).

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Claim age only** (`claim_age_months`) | Keeps SS deterministic and compatible with pre-simulation domain projections |
| 2 | **Drop net-worth claiming** | It requires monthly simulation state (`net_worth`) and cannot be precomputed into a static domain series |
| 3 | **Keep spousal benefit behavior** | It is meaningful for single-earner-heavy households and remains deterministic once claim ages are fixed |
| 4 | **Use real-aware earnings indexing** | Future job income from Phase 2b is already in today's dollars; indexing it again would undercount |
| 5 | **Use SSA XML FICA earnings for historical values** | SSA exports the user's official SS-covered earnings; `FicaEarnings` is capped, while `MedicareEarnings` is not |
| 6 | **Include pure parser in Phase 2c; defer upload UI** | Parser is core domain/input logic; UI wiring belongs with Phase 4 editor/import work |
| 7 | **Use monthly claim-age formula relative to FRA 67** | More accurate than legacy integer-age lookup and supports mid-year claiming |
| 8 | **Drop WEP / `pension_eligible`** | WEP repeal makes the reduced 40/32/15 legacy path obsolete |
| 9 | **Return projected series, not `TimedStream`s** | Spousal step-ups and selected max benefit are clearer as deterministic monthly series |
| 10 | **Store `spousal_alternative`; compute `spousal_top_up`** | Keeps output intuitive while avoiding duplicate source-of-truth fields |
| 11 | **Use one household-level SS trust factor** | Trust is an assumption about the Social Security system, not person-specific data; applying one factor to PIA is equivalent to applying it later to all benefits |

---

## 3. Config models (`core`)

Social Security config lives in `core` because `Plan` persists it through the
existing JSON-blob repository, exactly like jobs and timed streams.

```python
from decimal import Decimal
from pydantic import BaseModel, Field


class AnnualEarnings(BaseModel):
    """One SSA historical annual FICA earnings row.

    FICA earnings from the SSA XML are SS-covered and already capped at that
    calendar year's taxable maximum. Values are nominal historical dollars.
    """

    year: int
    fica_earnings: Decimal = Field(ge=0)


class PersonSocialSecurityConfig(BaseModel):
    """Per-person Social Security calculation inputs."""

    claim_age_months: int = Field(default=67 * 12, ge=62 * 12, le=70 * 12)
    earnings_record: list[AnnualEarnings] = Field(default_factory=list)
```

`PersonHousehold` gains one field, and `Household` gains one household-level
trust factor:

```python
class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)
    social_security: PersonSocialSecurityConfig = Field(
        default_factory=PersonSocialSecurityConfig
    )


class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
```

The default claim age is 67 years because the rebuild targets current users born
in 1960 or later, where Full Retirement Age is 67. General FRA-by-birth-year
support can be added later if the app needs to model older cohorts.

`social_security_trust_factor` is a household-level assumption about future
Social Security payments. It applies once to each person's statutory PIA to
produce an effective PIA used by both own-benefit and spousal-alternative
calculations. Because the same factor applies to both people, this is
mathematically equivalent to multiplying the final selected household benefits,
while keeping downstream projected series in expected received dollars.

---

## 4. SSA XML parser

Phase 2c adds a pure parser that converts SSA's exportable Online Social
Security Statement XML into `list[AnnualEarnings]`.

```python
def parse_social_security_statement_xml(xml_text: str) -> list[AnnualEarnings]: ...
```

Parser rules:

- Accept the `http://ssa.gov/osss/schemas/2.0` namespace.
- Read `EarningsRecord/Earnings` rows.
- Require `startYear == endYear`; multi-year rows raise `ValueError`.
- Extract `FicaEarnings`; ignore `MedicareEarnings`.
- Skip `FicaEarnings == -1`, which SSA uses for years not yet recorded.
- Reject malformed rows and non-numeric values with useful `ValueError`
  messages.
- Ignore `EstimatedBenefits` for calculations.

`EstimatedBenefits` are not used because SSA's estimates assume continued work
under SSA's own assumptions. They can be useful later as reference metadata or a
sanity check, but the app's plan-driven calculation must respond to early
retirement, sabbaticals, and future jobs configured in LifeFinances.

---

## 5. Earnings pipeline

`project_social_security(plan, timeline, job_income)` combines two earnings
sources per person:

1. Historical `AnnualEarnings` from SSA XML, in nominal dollars.
2. Future projected `job_income.person*.ss_covered_gross`, in today's dollars.

The pipeline is real-aware:

1. Group future monthly `ss_covered_gross` by calendar year using `timeline`.
2. Convert historical earnings to today's dollars using AWI indexing factors.
3. Leave future projected earnings at face value because they are already real,
   today's-dollar values from Phase 2b.
4. Apply the Social Security taxable maximum cap per year in the same dollar
   basis as the earnings being capped.
5. Compute AIME from the highest 35 annual indexed earnings years, including
   implicit zero years when fewer than 35 years have earnings.
6. Compute PIA from standard bend points and rates.

Historical FICA earnings from SSA XML are already capped for their source year,
but the calculation still routes all earnings through a single cap step so tests
can prove the invariant and future earnings are capped consistently.

### Statutory tables and extrapolation

Phase 2c establishes the statutory-data pattern that later tax work can reuse.
Regularly updated statutory inputs live in `domain`, not `core`, because they are
calculation inputs rather than persisted plan configuration.

Social Security tables live under `domain/statutory/` and include:

- historical taxable maximum (`SS_MAX_EARNINGS`);
- AWI indexing factors (`SS_INDEXES`);
- bend points;
- PIA rates.

The tables are versioned source data checked into the repository, not fetched
live from SSA at runtime. Each table should carry source URLs, effective year,
and last-updated notes. Updates happen through normal code/data PRs so
simulations remain reproducible.

The legacy code used NumPy exponential fit helpers. The rebuild should not add
NumPy just for this phase; implement a small stdlib log-linear least-squares
helper for exponential extrapolation. The helper takes source table rows
`(year, value)` and returns an estimated value for a requested year, matching the
legacy shape without importing legacy app code.

---

## 6. PIA and claim-age calculation

AIME is:

```text
sum(top_35_indexed_annual_earnings) / 420
```

PIA uses the standard bend-point formula:

```text
90% of AIME up to the first bend point
32% of AIME between the first and second bend points
15% of AIME above the second bend point
```

WEP / `pension_eligible` is not ported.

The household trust factor is then applied to produce effective PIA:

```text
effective_pia = statutory_pia * household.social_security_trust_factor
```

The benefit multiplier is a monthly formula relative to Full Retirement Age 67:

- Claim before FRA:
  - reduce by `5/9%` per month for the first 36 months early;
  - reduce by `5/12%` per month for months earlier than that.
- Claim after FRA:
  - increase by `2/3%` per delayed month through age 70.

`claim_age_months` is constrained to `[62 * 12, 70 * 12]`, so no extrapolation
beyond SSA's early/delayed retirement bounds is required.

Each person's own monthly benefit starts in the calendar month they reach
`claim_age_months`:

```text
own_benefit = effective_pia * claim_age_multiplier
```

Amounts are projected as real monthly dollars. Inflation is applied later by the
simulation layer, not in the domain calculation.

---

## 7. Spousal alternatives

Phase 2c keeps the legacy spousal behavior, adapted to deterministic claim ages.

Once both spouses have claimed, each person can receive a spousal alternative:

```text
spousal_alternative = 0.5 * spouse_effective_pia * person's_claim_age_multiplier
```

Before both people have claimed, `spousal_alternative` is zero. A person's total
benefit is the month-by-month maximum of their own benefit and spousal
alternative:

```text
total = max(own_benefit, spousal_alternative)
```

The spousal alternative uses the worker's own claim-age multiplier, matching the
legacy behavior: the spouse's PIA defines the base, but the worker's claiming
age determines the reduction or delayed credit applied to the worker's benefit.

---

## 8. Output: `SocialSecurityProjection`

```python
from decimal import Decimal
from pydantic import BaseModel, computed_field


class PersonSocialSecurity(BaseModel):
    """Projected Social Security for one person.

    All series have length == timeline.horizon_months and are after household
    trust-factor scaling. spousal_alternative is the full alternative benefit,
    not only the incremental amount above own_benefit.
    """

    own_benefit: list[Decimal]
    spousal_alternative: list[Decimal]
    total: list[Decimal]

    @computed_field
    @property
    def spousal_top_up(self) -> list[Decimal]:
        return [
            total - own
            for own, total in zip(self.own_benefit, self.total, strict=True)
        ]


class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity
    total: list[Decimal]
```

Public API:

```python
def project_social_security(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> SocialSecurityProjection: ...
```

The module consumes the Phase 2b `JobIncomeProjection` instead of recomputing job
income. This proves that sabbatical-reduced SS-covered earnings flow through SS
without duplicating job-income logic.

---

## 9. File layout

```text
packages/core/
├── core/
│   ├── social_security.py   # NEW — AnnualEarnings, PersonSocialSecurityConfig
│   └── models.py            # + PersonHousehold.social_security; + Household.social_security_trust_factor
└── tests/
    └── test_social_security.py

packages/domain/
├── domain/
│   ├── statutory/
│   │   ├── __init__.py
│   │   └── social_security.py  # SS taxable max, AWI, bend points, PIA rates
│   └── social_security/
│       ├── __init__.py      # project_social_security, output models
│       ├── earnings.py      # XML parser + earnings/AIME helpers
│       └── benefits.py      # PIA + monthly claim-age multiplier
├── tests/
│   └── test_social_security.py
└── OVERVIEW.md              # social_security status -> done when complete
```

Exact module names can be adjusted during planning, but responsibilities should
stay separated: statutory tables, parser/earnings, benefit formula, and
projection orchestration.

---

## 10. Error handling

| Situation | Behavior |
|-----------|----------|
| `claim_age_months` outside 62-70 | Pydantic `ValidationError` |
| `social_security_trust_factor` outside `[0, 1]` | Pydantic `ValidationError` |
| negative `AnnualEarnings.fica_earnings` | Pydantic `ValidationError`; parser skips only SSA's `-1` sentinel before model construction |
| SSA XML missing `EarningsRecord` | `ValueError` with a clear message |
| SSA XML row has `startYear != endYear` | `ValueError` with the row years |
| SSA XML row has malformed `FicaEarnings` | `ValueError` with the year when available |
| no earnings history and no future SS-covered earnings | PIA is zero; output series are all zero |
| one spouse has zero PIA | their own benefit is zero; spouse's alternative from them is zero |
| timeline has non-positive horizon | output lists are empty, matching `project_stream` behavior |

---

## 11. Testing (TDD, one behavior per test)

Per repo testing policy: behavior test first, scaffold to a logical red, then
implement. Inject `today: date`. Pull shared values from source; never duplicate
a literal across arrange and assert.

Representative behaviors:

| Area | Behaviors |
|------|-----------|
| Core models | default claim age is FRA 67; claim age bounds enforced; household trust factor bounds enforced; repository round-trip persists earnings records |
| XML parser | extracts FICA earnings; ignores Medicare earnings; skips `-1`; handles SSA namespace; rejects missing/malformed/multi-year rows |
| Earnings aggregation | future monthly `ss_covered_gross` groups by calendar year; historical earnings are indexed; future real earnings are not indexed |
| Statutory tables | SS tables live under `domain/statutory`; tests import source constants instead of duplicating literals |
| Wage-base cap | annual earnings above the taxable max are capped before AIME |
| AIME | uses top 35 years; includes implicit zero years when fewer than 35 earnings years exist |
| PIA | standard 90/32/15 bend-point formula; no WEP path |
| Claim multiplier | monthly early/delayed formulas at 62, FRA, 70, and a mid-year claim age |
| Claim start | benefits begin in the exact calendar month the person reaches `claim_age_months` |
| Spousal alternative | zero before both people claim; present after both claim; total is max(own, alternative) |
| Trust factor | household trust factor scales effective PIA and therefore both own benefit and spousal alternative |
| Job-income integration | sabbatical-reduced `ss_covered_gross` changes future earnings and therefore AIME/PIA |
| Projection shape | per-person lists and household total have `timeline.horizon_months` length |

Do **not** test pure Pydantic validation of trivial fields beyond the model
contracts listed above.

---

## 12. Exit criteria

- [ ] `AnnualEarnings` and `PersonSocialSecurityConfig` models in `core`.
- [ ] `PersonHousehold.social_security` and `Household.social_security_trust_factor`
      persist through SQLite round-trip.
- [ ] SSA statement XML parser extracts historical FICA earnings and skips `-1`.
- [ ] Social Security statutory tables live under `domain/statutory`, setting the
      pattern for future tax-rate tables.
- [ ] `project_social_security(plan, timeline, job_income)` returns
      `SocialSecurityProjection`.
- [ ] Real-aware earnings pipeline: historical earnings indexed, future real
      earnings not indexed.
- [ ] Future SS earnings consume Phase 2b `ss_covered_gross`; sabbatical-reduced
      earnings flow through.
- [ ] AIME/PIA calculation uses standard formula only; WEP not ported.
- [ ] Monthly claim-age formula supports claim ages from 62 through 70.
- [ ] Spousal alternatives and computed `spousal_top_up` covered by tests.
- [ ] `packages/domain/OVERVIEW.md` documents SS port status.
- [ ] `make` passes.

---

## 13. Deferred

- SSA XML upload UI, parser wiring from uploaded files into saved plans, and
  editor UX.
- Taxation of Social Security benefits.
- Inflation application in simulation outputs.
- Optional parsing/storage of SSA `EstimatedBenefits` as reference metadata.

## 14. Next step

After spec approval: invoke **writing-plans** to produce
`docs/superpowers/plans/2026-06-12-phase-2c-domain-social-security.md`, then
execute via subagent-driven development.

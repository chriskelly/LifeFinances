# Phase 2e — Domain: Single-Person Household Design

**Date:** 2026-06-25
**Status:** Approved
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)
**Builds on:** [2026-06-25-phase-2d-domain-pension-taxes-design.md](./2026-06-25-phase-2d-domain-pension-taxes-design.md)
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-2e-domain-single-household.md` *(to write after spec approval)*

---

## 1. Goal & scope

Make the second household member optional so a plan can model a single person,
and auto-derive `filing_status` from household size while still honoring an
explicit override. This is the last domain phase before the simulation core
(Phase 3).

Phase 2e includes:

1. **Optional `person2`** — `Household.person2: PersonHousehold | None`; `None`
   means a single-person plan.
2. **Auto filing status** — `filing_status` becomes optional; `None` resolves to
   `single` for one person and `married_filing_jointly` for two. An explicit
   value always wins.
3. **Single-person domain projections** — job income, Social Security, pension,
   taxes, and `build_monthly_cashflows` all work with one person; spousal SS is
   skipped when the partner is absent.
4. **Minimal web toggle** — the household editor gets a "has partner" checkbox so
   a single-person plan is reachable from the UI.

Phase 2e does **not** include:

- A `filing_status` override control in the editor (Phase 4 tax UI).
- Filing statuses beyond MFJ / single (e.g. married filing separately, head of
  household).
- Any Phase 3 simulation or Phase 4 full-editor work.

---

## 2. Decisions captured from brainstorming

| #   | Decision                                                       | Rationale                                                                                                              |
| --- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 1   | **Optional `person2` fields throughout**                       | Honest shape: absent partner is `None`, not a synthetic zero person. Consumers guard for `None`; totals sum present people. |
| 2   | **`Household.people` helper**                                  | Single source for "iterate present members"; replaces hardcoded `(person1, person2)` loops in validators, timeline, pension. |
| 3   | **`filing_status: FilingStatus \| None = None` + resolver**     | `None` means "auto from household size"; an explicit value always wins (`resolved_filing_status` property).            |
| 4   | **`default_plan()` stays two-person**                          | No baseline change to existing plans/tests; default `filing_status=None` resolves to MFJ for the two-person default.    |
| 5   | **Include a minimal web toggle now**                           | Single-person plans should be reachable from the UI, not only programmatically; full editor/override UI remains Phase 4. |
| 6   | **No new bespoke errors**                                      | `has_partner=True` with missing person2 fields surfaces as a Pydantic `ValidationError` from `PersonHousehold`.        |

---

## 3. Core model changes (`packages/core`)

### `core/models.py`

```python
class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold | None = None
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
    filing_status: FilingStatus | None = None  # None = auto from household size
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

Notes:

- The `filing_status` default flips from `"married_filing_jointly"` to `None`.
  This is the mechanism that lets household size drive the result. Any plan that
  explicitly stored `"married_filing_jointly"` still round-trips and still wins
  over the auto rule.
- `resolved_filing_status` is the single read path for tax bracket/deduction
  selection. Code MUST NOT read `household.filing_status` directly for tax math.

### `core/timeline.py`

`horizon_months` uses present members only:

```python
def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    end = max(person_end_date(p) for p in plan.household.people)
    return (end.year - today.year) * 12 + (end.month - today.month)
```

### `core/defaults.py`

`default_plan()` stays two-person; no change required beyond the model default.

---

## 4. Domain projection changes (`packages/domain`)

The per-person projection result models gain an optional `person2`, and
totals/derived series count present people only.

### Job income (`domain/job_income/__init__.py`)

```python
class JobIncomeProjection(BaseModel):
    person1: PersonJobIncome
    person2: PersonJobIncome | None = None
    total_gross: list[Decimal]
    total_ss_covered_gross: list[Decimal]
    total_tax_deferred: list[Decimal]
```

`project_job_income` projects `person2` only when present; totals start from
`person1` and add `person2` when present.

### Social Security (`domain/social_security/__init__.py`)

```python
class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity | None = None
    total: list[Decimal]
```

When `person2` is absent, person1's spousal alternative is all-zeros (there is no
spouse PIA to halve), so `max_benefit == own_benefit`. `total` sums only present
members' `max_benefit`. The two-person path is unchanged.

### Pension (`domain/pension/__init__.py`)

No shape change — `PensionProjection` is already total-only series. The formula
loop iterates `household.people` instead of the hardcoded pair.

### Taxes (`domain/taxes/__init__.py`)

- Read `household.resolved_filing_status` instead of `household.filing_status`.
- `_fica_social_security` builds its per-person series from present projections
  only:

```python
person_series = [
    pi.ss_covered_gross
    for pi in (job_income.person1, job_income.person2)
    if pi is not None
]
```

Everything else in `compute_taxes` already reads totals
(`total_gross`, `total_tax_deferred`, `social_security.total`,
`pension.stored_total`), so no further change.

### Aggregator (`domain/__init__.py`)

Reads totals only; unchanged.

---

## 5. Web toggle (`packages/web`)

### `web/forms.py`

```python
HAS_PARTNER = "has_partner"

class HouseholdForm(BaseModel):
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

### `web/templates/editor_household.html`

- Add a `has_partner` checkbox (checked by default) bound to
  `forms.HAS_PARTNER`.
- Wrap the person2 fields in a container toggled by the checkbox via small inline
  JS (show/hide). Unchecked → `person2=None` saved → `resolved_filing_status`
  becomes `single`.
- HTML checkboxes submit nothing when unchecked, so `has_partner` defaults to
  `False` server-side.

### Route

`PLAN_HOUSEHOLD` is unchanged; FastAPI binds the flat `Form()` fields to the
extended DTO. `filing_status` stays out of the editor (override UI is Phase 4);
the toggle alone drives MFJ vs single via the resolver.

---

## 6. File layout

```text
packages/core/
├── core/
│   ├── models.py       # Household.person2 optional; people, resolved_filing_status; filing_status -> None default
│   └── timeline.py     # horizon_months over household.people
└── tests/
    └── test_household.py  # people, resolver, single-person horizon, validator

packages/domain/
├── domain/
│   ├── job_income/__init__.py        # JobIncomeProjection.person2 optional; totals over present
│   ├── social_security/__init__.py   # SocialSecurityProjection.person2 optional; skip spousal when absent
│   ├── pension/__init__.py           # iterate household.people
│   ├── taxes/__init__.py             # resolved_filing_status; FICA over present people
│   └── __init__.py                   # aggregator unchanged
├── tests/
│   ├── test_job_income.py            # single-person projection
│   ├── test_social_security.py       # no spousal when single
│   ├── test_pension.py               # single-person loop
│   ├── test_taxes.py                 # FICA single-person; resolved filing status
│   └── test_cashflows.py             # single-person end-to-end
└── OVERVIEW.md                       # + single-household support note

packages/web/
├── web/
│   ├── forms.py                      # HouseholdForm: has_partner + optional person2
│   └── templates/editor_household.html  # has_partner checkbox + toggle
└── tests/
    └── test_app.py                   # single vs two-person POST + round-trip
```

---

## 7. Error handling

| Situation                                         | Behavior                                                        |
| ------------------------------------------------- | --------------------------------------------------------------- |
| `has_partner=True` with missing person2 fields    | Pydantic `ValidationError` from `PersonHousehold` construction  |
| `person2=None` round-trip through SQLite          | Persists as `None`; rehydrates as single-person household       |
| `filing_status=None` round-trip                   | Persists as `None`; resolves at read time via household size    |
| Explicit `filing_status` on a single-person plan  | Honored as-is (override wins over the auto rule)                |

---

## 8. Testing (TDD, one behavior per test)

Per repo testing policy: behavior test first, scaffold to a logical red, then
implement. Inject `today: date`. Pull shared values from source; never duplicate
a literal across arrange and assert.

### Core

| Area                  | Behavior                                                                       |
| --------------------- | ------------------------------------------------------------------------------ |
| `people`              | returns one member when `person2 is None`, two when present                    |
| `resolved_filing_status` | `None`+1 person → `single`; `None`+2 → MFJ; explicit value wins in both sizes |
| Horizon               | single-person `horizon_months` uses person1's end date                         |
| Validator             | sabbatical-window validation runs for a single-person household                |

### Domain

| Area               | Behavior                                                               |
| ------------------ | ---------------------------------------------------------------------- |
| Job income         | single-person: `person2 is None`; totals equal person1                 |
| Social Security    | single-person: no spousal top-up; `total` equals person1 own benefit   |
| Pension            | single-person formula loop projects correctly                          |
| FICA               | single-person: no `person2` access error; wage-base cap tracked for one|
| Aggregator         | `build_monthly_cashflows` single-person end-to-end                     |
| Two-person regression | existing MFJ behavior unchanged (shared values pulled from source)  |

### Web

| Area               | Behavior                                                               |
| ------------------ | ---------------------------------------------------------------------- |
| Single POST        | household form without `has_partner` → `person2=None`, resolves `single`, round-trips through repo |
| Two-person POST    | household form with `has_partner` → two people, resolves MFJ           |

---

## 9. Exit criteria

- [ ] `Household.person2` optional (`None` = single-person plan).
- [ ] `filing_status` defaults from household size; explicit override honored
  (`resolved_filing_status`).
- [ ] Job income, SS, pension, and `build_monthly_cashflows` work with one person.
- [ ] Spousal SS logic skipped when partner absent.
- [ ] Web household editor can create a single-person plan via the `has_partner`
  toggle.
- [ ] `packages/domain/OVERVIEW.md` documents single-household support.
- [ ] `make` passes.

---

## 10. Deferred to later phases

- `filing_status` override control and full editor sections (Phase 4).
- Additional filing statuses (married filing separately, head of household).
- Inflation, simulation, and chart work (Phase 3+).

---

## 11. Next step

After spec approval: invoke **writing-plans** to produce
`docs/superpowers/plans/2026-06-12-phase-2e-domain-single-household.md`, then
execute via subagent-driven development.

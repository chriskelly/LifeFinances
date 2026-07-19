# Phase 4c — Web: Editor — Household & Income Design

**Date:** 2026-07-19  
**Status:** Approved

**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)  
**Builds on:** Phase 2b–2e domain (jobs, SS, pension, taxes, single household); [Phase 4a plan shell](./2026-07-14-phase-4a-plan-shell-design.md); [Phase 4b core charts](./2026-07-15-phase-4b-core-charts-design.md)  
**Phase plan:** [`2026-06-12-phase-4c-editor-income.md`](../plans/2026-06-12-phase-4c-editor-income.md) *(to write)*  
**Index:** Phase 4c in [2026-06-12-rebuild-index.md](../plans/2026-06-12-rebuild-index.md)  
**Domain map:** [`packages/domain/OVERVIEW.md`](../../../packages/domain/OVERVIEW.md)

---

## 1. Goal & scope

Make **income-side** plan domains editable in the split-pane editor so a realistic household can drive simulation without hand-editing SQLite/JSON.

### In scope

- Core: `PersonMaxAgeBoundary` + timeline resolution
- Fix `HouseholdForm.apply_to` so demographic saves **preserve** jobs, SS config, and tax fields
- Editor sections: Household (+ tax), Jobs, Social Security, Manual income — each with form DTO, PATCH route, and template partial (Phase 1 pattern)
- Jobs: add/edit/remove per person; sabbaticals; CalSTRS formula-pension preset (no free-form age-factor table); tooltip → [#197](https://github.com/chriskelly/LifeFinances/issues/197)
- SS: claim age; XML upload via existing `parse_social_security_statement_xml`; read-only earnings summary (not row editors)
- Manual income: `plan.manual_income_streams` list with shared boundary control
- Tax fields: explicit Single/MFJ filing status (prefilled from `resolved_filing_status`); `residence_state`; `ss_pension_taxable_fraction`; `social_security_trust_factor`
- Task 0: form DTO spike (hand-written vs `create_model`); bias hand-written + shared boundary/list helpers
- Gitignore personal SSA statement files at repo root (`social-security-statement.xml`)

### Out of scope

- Spending / simulation-config editors (4d)
- Extended charts (4e); legacy YAML import / launcher (4f)
- Free-form pension age-factor table UI (tracked in [#197](https://github.com/chriskelly/LifeFinances/issues/197))
- Hand-edited SS earnings rows; prefilling claim age from XML benefit estimates
- Row-level HTMX add/remove endpoints (full-section replace only)

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **CalSTRS preset** for formula pension; richer editor deferred ([#197](https://github.com/chriskelly/LifeFinances/issues/197)) | Covers the real case without dense table UI |
| 2 | **Full-section replace** for list editors | Matches existing debounce / `planUpdated`; lists stay small |
| 3 | **SS earnings via ss.gov XML upload** in 4c | Parser already shipped in Phase 2c; no row editors |
| 4 | **Separate sections** (Household+tax, Jobs, SS, Manual income) | One form + PATCH per concern; mirrors Phase 1 |
| 5 | **Both boundary kinds** (calendar + person-age) everywhere, plus context terminals | Matches how users and TPAW think about windows |
| 6 | **Form DTO spike** (Task 0); bias hand-written + helpers | Generation must still fight `Form()` + list indices |
| 7 | **Filing status always explicit** in UI (Single/MFJ); no Auto | Users need not see model `None`/auto mode; save always writes a value |
| 8 | **Hybrid terminals:** “Now” resolves at save; max-age stays symbolic | Living max-age link; Now is a one-shot stamp |
| 9 | **Approach 1:** extend `Boundary` with `PersonMaxAgeBoundary` + section forms | Required for decision 8 without stale `age_months` |

---

## 3. Boundaries & shared controls

### 3.1 Core model

Extend the `Boundary` discriminated union in `core.streams`:

```python
class PersonMaxAgeBoundary(BaseModel):
    kind: Literal["person_max_age"] = "person_max_age"
    person: PersonId  # "person1" | "person2"
```

`boundary_to_year_month` in `core.timeline` resolves it as that person’s birth month/year plus `max_age_years` (same end-of-life math as `person_end_date`). Existing `calendar_month` and `person_age` kinds are unchanged.

`None` start/end on fields that allow `Boundary | None` keep today’s projection semantics (plan start / plan horizon).

### 3.2 UI ↔ storage mapping

| User choice | Stored |
| ----------- | ------ |
| Calendar date | `CalendarMonthBoundary` |
| Age | `PersonAgeBoundary` (`person` + years/months → `age_months`) |
| Now | Stamp `CalendarMonthBoundary` for the current calendar month **at save** (not symbolic) |
| Until person’s max age | `PersonMaxAgeBoundary` |
| Plan start / plan horizon | `None`, only on fields that are `Boundary \| None` today |

Context filters which terminals appear (examples):

- Job **start:** Now, calendar, age, optional plan-start (`None`)
- Job **end:** calendar, age, max-age for self (and partner when present), optional plan-horizon (`None`)
- Pension service/claim: required concrete or max-age — not Now
- Manual stream start/end: full set including optional `None`

### 3.3 Shared UI building blocks

- One Jinja boundary partial + `web` parse helpers (`parse_boundary` / list collectors)
- Indexed field names for lists (`jobs[0].…`, `sabbaticals[1].…`)
- Client-side Add clones a blank row; Remove drops the row; one debounced PATCH posts the whole section

---

## 4. Editor sections

### 4.1 Household (extend existing)

- Keep demographics (births, max age, partner toggle)
- **`apply_to` must merge** into the existing `Household` — never rebuild a bare household that drops `jobs`, `social_security`, or tax fields
- Add tax fields on this section:
  - `filing_status`: Single / MFJ only; prefill from `resolved_filing_status`; every save writes an explicit enum value
  - `residence_state`
  - `ss_pension_taxable_fraction`
  - `social_security_trust_factor`
- When partner is unchecked, `person2=None`; Jobs/SS UI for person2 is hidden (data for a removed partner is dropped with `person2`, same as today’s partner toggle)

### 4.2 Jobs (new)

Per present person, a list of `Job` rows:

- label, annual income, annual tax-deferred, annual raise, SS-eligible
- start/end via shared boundary control
- sabbatical list (start/end/remaining_fraction)
- **Pension:** checkbox “CalSTRS 2% at 62”
  - On: build `FormulaPension` with `age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)` plus user-editable service start, claim, averaging months, trust factor, benefit real growth
  - Off: `pension=None`
  - Tooltip links to [#197](https://github.com/chriskelly/LifeFinances/issues/197) for a fuller pension editor
- Round-trip “preset detected” may compare age-factor table equality to the statutory CalSTRS table (no separate preset id required on the model)

### 4.3 Social Security (new)

Per present person:

- Claim age control → `claim_age_months` (years, or years+months)
- Earnings: **read-only summary** (year count and/or first–last year) after import — not editable rows
- Separate multipart **Upload statement XML** action (not on the debounced claim-age form):
  - `POST` with `?plan=` and `person=person1|person2`
  - Body: file upload
  - Server: `parse_social_security_statement_xml` → replace that person’s `earnings_record`
  - Success: re-render SS partial + trigger `planUpdated`
  - Failure: inline error; no partial write

Reuse the canned XML shape from `packages/domain/tests` (or a tiny fixture under `packages/web/tests/fixtures/`). Do **not** commit personal `social-security-statement.xml` from the repo root.

### 4.4 Manual income (new)

Editor for `plan.manual_income_streams`:

- label, monthly amount, `is_nominal`, `annual_growth_rate`
- start/end via shared boundary control
- Add/remove rows; full-list PATCH

---

## 5. Routes, forms, errors

### 5.1 Routes

All plan-scoped with `?plan={id}` (404 on unknown plan), mirroring existing editors:

| Method | Purpose |
| ------ | ------- |
| `GET` / `PATCH` | Household (extended), Jobs, Social Security, Manual income |
| `POST` | Social Security XML upload (`person` query/form field) |

Exact path constants live in `web/routes.py` (e.g. `/plan/jobs`, `/editor/jobs`, upload under the SS plan path).

### 5.2 Forms (Task 0)

1. Spike hand-written flat DTOs vs `create_model` + prefixed `model_fields`
2. Default implementation path unless the spike proves otherwise: **hand-written** section DTOs + field-name constants + shared boundary/list helpers
3. Form DTOs remain transport-only (no duplicated `ge`/`le` constraints); validation stays on `core.models`
4. Each `apply_to(plan)` merges that section only

Pension enablement calls statutory helpers at apply time (`domain.statutory.pension`).

### 5.3 Errors & HTMX

- Validation / `ValueError` on apply → re-render the section partial with a short error banner (keep prior saved plan state; do not persist the bad apply). Non-HTMX clients may still see `422`.
- XML parse failures: same pattern on the SS section; prior `earnings_record` unchanged
- Successful section `PATCH`: `hx-swap="none"` + existing `planUpdated` → results refresh
- Upload success swaps the SS partial so the earnings summary updates immediately, then triggers `planUpdated`
- `PersonMaxAgeBoundary.person="person2"` is invalid when `person2` is absent — reject at apply/validate time

---

## 6. Testing

| Area | Coverage |
| ---- | -------- |
| Core | `PersonMaxAgeBoundary` resolution; round-trip through plan JSON / repository |
| Web | Each section PATCH round-trip; household merge preserves nested income fields |
| Web | XML upload happy path + invalid XML; person targeting |
| Web | Partner absent → person2 job/SS blocks hidden / not required |
| Web | CalSTRS pension attach / clear |
| Fixtures | Synthetic SSA XML only; never personal statement files |

No network in tests. `make` must pass.

---

## 7. PR sizing

Prefer **one PR** for Phase 4c. Split only if the diff exceeds rebuild-index guidance (~2000 lines):

| Subphase | Contents |
| -------- | -------- |
| **4c-1** | `PersonMaxAgeBoundary` + shared boundary UI; household tax + merge fix; Jobs (+ CalSTRS) |
| **4c-2** | Social Security + XML upload; Manual income |

Each split must leave `main` green.

---

## 8. File / package touch map (expected)

```
packages/core/core/streams.py          # + PersonMaxAgeBoundary
packages/core/core/timeline.py         # resolve person_max_age
packages/web/web/forms.py              # section DTOs + helpers
packages/web/web/routes.py / sections.py / app.py
packages/web/web/templates/            # editor_* + boundary partial
packages/web/tests/                    # section + upload tests + fixture
.gitignore                             # social-security-statement.xml
docs/superpowers/plans/…-phase-4c…     # written after this spec
```

`web` may import `domain` for XML parse and CalSTRS statutory helpers (allowed: `web → domain`).

---

## 9. Exit criteria

- [ ] Jobs editor: add/edit/remove per person; sabbaticals; optional CalSTRS `FormulaPension`
- [ ] SS editor per person: claim age + XML upload → `earnings_record`; read-only summary
- [ ] Manual income streams editor
- [ ] Household tax fields editable; filing status always explicit Single/MFJ on save
- [ ] `PersonMaxAgeBoundary` persisted and resolved; “Now” stamps calendar month at save
- [ ] Demographic household PATCH preserves jobs/SS/tax
- [ ] Tooltip on pension preset links to [#197](https://github.com/chriskelly/LifeFinances/issues/197)
- [ ] Form DTO strategy decided via Task 0 spike (documented in plan / `web/AGENTS.md`)
- [ ] Personal SSA XML gitignored; not committed
- [ ] `make` passes

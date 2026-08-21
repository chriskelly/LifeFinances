# Phase 4c — Editor: Household & Income Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the income-side plan domains (household demographics + tax, jobs with sabbaticals and a CalSTRS pension preset, Social Security claim age + XML earnings import, and manual income streams) editable in the split-pane HTMX editor.

**Architecture:** Follow the Phase 1 flat-form + HTMX section pattern — one `<form>` (or upload form) per editor section, each `PATCH`ing its own `/plan/*` route with `?plan={id}`. Scalar sections bind via FastAPI `Form()`; list sections (jobs, manual income) read the raw multipart form and parse indexed field names (`jobs[0].label`, `sabbaticals[1].start_kind`) with shared collectors. A new `web/boundaries.py` centralizes parsing form fields into `core.streams.Boundary` values and rendering existing boundaries back into form state. Each section's `apply_to(plan)` **merges** into the full `Plan` (never rebuilds a bare object) so unrelated nested data is preserved.

**Tech Stack:** Python 3.14, FastAPI, Jinja2, HTMX, Pydantic 2, pytest. uv workspace (`web → simulation, domain, core`).

## Global Constraints

- Run all developer commands from the **repository root**.
- `make` (ruff check + ruff format check + pyright + pytest) MUST pass before any task is considered complete.
- Follow TDD: write the failing test, get past structural failure with minimal scaffolding, confirm a **logical** failure, implement, confirm green.
- Never hardcode a literal in both arrange/act and assert — bind to one variable. Import constants/defaults from source (`core.*`, `domain.*`) rather than copying.
- Form DTOs are **transport-only**: no `Field(ge=…/le=…)` constraints on them. All validation lives on `core.models` / `core.job` / `core.social_security` / `core.streams`; `apply_to()` builds core models and lets Pydantic validate.
- HTML `name` attributes MUST use the constants in `web/forms.py` / `web/boundaries.py` (prefixes + suffixes for indexed lists) — never hardcode field strings in templates.
- Package dependency direction is strict: `web` may import `domain` and `core`; never the reverse. Do NOT import `web` from `simulation`/`tools`.
- Use underscores in large numeric literals (`Decimal("1_000_000")`).
- Never commit `data/data.db`, `config.yml`, secrets, or the personal `social-security-statement.xml`.
- Never edit lockfiles by hand (`uv add`/`uv sync`), never touch `.github/workflows/`, never disable lint/type rules to pass CI.

**Design spec:** [`docs/superpowers/specs/2026-07-19-phase-4c-editor-income-design.md`](../specs/2026-07-19-phase-4c-editor-income-design.md)

## File structure

| File | Responsibility |
| ---- | -------------- |
| `packages/core/core/streams.py` | Add `PersonMaxAgeBoundary` to the `Boundary` union |
| `packages/core/core/timeline.py` | Resolve `person_max_age` to (year, month) |
| `packages/web/web/boundaries.py` | **New.** Wire-format constants, `parse_boundary`, `to_form`, indexed-row collectors |
| `packages/web/web/forms.py` | Section DTOs (`HouseholdForm` extended, `SocialSecurityForm`, `JobsForm`, `ManualIncomeForm`) + field-name constants |
| `packages/web/web/routes.py` | Path constants for new sections |
| `packages/web/web/sections.py` | Section title + label constants |
| `packages/web/web/app.py` | Editor GET routes, PATCH/POST routes, generic `planUpdated` |
| `packages/web/web/templates/_boundary.html` | **New.** Reusable boundary-control macro |
| `packages/web/web/templates/editor_household.html` | Extend with tax fields |
| `packages/web/web/templates/editor_jobs.html` | **New.** |
| `packages/web/web/templates/editor_social_security.html` | **New.** |
| `packages/web/web/templates/editor_manual_income.html` | **New.** |
| `packages/web/web/templates/index.html` | Include new partials; generic `planUpdated` trigger |
| `packages/web/web/static/editor_lists.js` | **New.** Boundary-kind toggling + add/remove row cloning |
| `packages/web/tests/` | Section + upload tests + synthetic SSA XML fixture |

## Form DTO decision (spec Task 0 spike)

We evaluated generating flat DTO fields from `core.models` via `create_model` + `model_fields` introspection versus hand-writing them. **Decision: hand-written section DTOs plus shared boundary/list helpers.** Rationale: the list sections (jobs, sabbaticals, manual income) require *indexed, nested* field names (`jobs[0].sabbaticals[1].start_kind`) that FastAPI's `Form()` binding cannot express, so those routes must read `await request.form()` and parse manually regardless of how scalar DTOs are produced. Generation would still have to fight `Form()` and index prefixing for the hard cases while adding indirection to the easy ones. This decision is recorded in `packages/web/AGENTS.md` in Task 3.

---

### Task 1: `PersonMaxAgeBoundary` core model + timeline resolution

**Files:**
- Modify: `packages/core/core/streams.py`
- Modify: `packages/core/core/timeline.py`
- Test: `packages/core/tests/test_streams.py`, `packages/core/tests/test_timeline.py`

**Interfaces:**
- Produces: `core.streams.PersonMaxAgeBoundary(kind="person_max_age", person: PersonId)`, added to the `Boundary` discriminated union. `core.timeline.boundary_to_year_month` resolves it to `(person.birth_year + person.max_age_years, person.birth_month)` — identical month/year math to `person_end_date`.

- [ ] **Step 1: Write both failing tests**

Add the persistence round-trip test to `packages/core/tests/test_streams.py`. This guards that a stored plan's `person_max_age` boundary re-parses through the discriminated union (plans persist as JSON), which is our union wiring — not generic Pydantic behavior:

```python
from core.streams import Boundary, PersonMaxAgeBoundary
from pydantic import TypeAdapter


def test_person_max_age_boundary_round_trips_through_boundary_union() -> None:
    expected_person = "person2"
    adapter = TypeAdapter(Boundary)

    parsed = adapter.validate_python(
        {"kind": "person_max_age", "person": expected_person}
    )

    assert isinstance(parsed, PersonMaxAgeBoundary)
    assert parsed.person == expected_person
```

Add the resolution test to `packages/core/tests/test_timeline.py` (reuse existing household helpers in that file if present; otherwise build a `Household` inline):

```python
from core.models import Household, PersonHousehold
from core.streams import PersonMaxAgeBoundary
from core.timeline import boundary_to_year_month


def test_person_max_age_boundary_resolves_to_birth_month_at_max_age() -> None:
    birth_month = 3
    birth_year = 1990
    max_age_years = 95
    household = Household(
        person1=PersonHousehold(
            birth_month=birth_month, birth_year=birth_year, max_age_years=max_age_years
        )
    )

    year, month = boundary_to_year_month(
        PersonMaxAgeBoundary(person="person1"), household
    )

    assert (year, month) == (birth_year + max_age_years, birth_month)
```

- [ ] **Step 2: Add minimal scaffolding (structure only, no resolution logic)**

Add the model + union member to `packages/core/core/streams.py`, after `PersonAgeBoundary`. Do **not** yet touch `boundary_to_year_month` — this leaves the resolution logic unimplemented so the timeline test fails logically rather than structurally:

```python
class PersonMaxAgeBoundary(BaseModel):
    kind: Literal["person_max_age"] = "person_max_age"
    person: PersonId


Boundary = Annotated[
    CalendarMonthBoundary | PersonAgeBoundary | PersonMaxAgeBoundary,
    Field(discriminator="kind"),
]
```

- [ ] **Step 3: Run both tests once — confirm a logical failure**

Run: `uv run pytest packages/core/tests/test_streams.py::test_person_max_age_boundary_round_trips_through_boundary_union packages/core/tests/test_timeline.py::test_person_max_age_boundary_resolves_to_birth_month_at_max_age -v`
Expected: the round-trip test **passes** (the union member now exists) and the timeline test **fails logically** — `TypeError: Unknown boundary` (the resolver runs the `isinstance` chain and hits our own `raise`), not an `ImportError`/`AttributeError`. If the timeline failure is structural, the scaffolding in Step 2 is incomplete — fix it before writing resolution logic.

- [ ] **Step 4: Implement `person_max_age` resolution in `boundary_to_year_month`**

In `packages/core/core/timeline.py`, extend the import and the resolver:

```python
from core.streams import (
    Boundary,
    CalendarMonthBoundary,
    PersonAgeBoundary,
    PersonMaxAgeBoundary,
    TimedStream,
)


def boundary_to_year_month(boundary: Boundary, household: Household) -> tuple[int, int]:
    """Resolve a boundary to an absolute (year, month). Birth-date only; no `today`."""
    if isinstance(boundary, CalendarMonthBoundary):
        return boundary.year, boundary.month
    if isinstance(boundary, PersonAgeBoundary):
        person = getattr(household, boundary.person)
        return add_months(person.birth_year, person.birth_month, boundary.age_months)
    if isinstance(boundary, PersonMaxAgeBoundary):
        person = getattr(household, boundary.person)
        return person.birth_year + person.max_age_years, person.birth_month
    raise TypeError(f"Unknown boundary: {boundary!r}")
```

- [ ] **Step 5: Run both new tests + the full core suite — confirm green**

Run: `uv run pytest packages/core/tests/test_timeline.py packages/core/tests/test_streams.py -v`
Expected: PASS. Then `uv run pytest packages/core -q` — Expected: PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/streams.py packages/core/core/timeline.py packages/core/tests/test_streams.py packages/core/tests/test_timeline.py
git commit -m "feat(core): add PersonMaxAgeBoundary and timeline resolution"
```

---

### Task 2: Household merge fix + tax fields

Fixes the data-loss bug where a demographics `PATCH` rebuilds a bare `Household`, dropping `jobs`, `social_security`, and tax fields. Adds explicit filing status, residence state, SS/pension taxable fraction, and SS trust factor to the Household section. Also switches the `index.html` `planUpdated` trigger to a generic `/plan/` prefix check so later sections need no JS edits.

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py` (`patch_household`)
- Modify: `packages/web/web/templates/editor_household.html`
- Modify: `packages/web/web/templates/index.html`
- Test: `packages/web/tests/test_app.py`

**Interfaces:**
- Consumes: `core.models.FilingStatus` (`Literal["married_filing_jointly", "single"]`), `Household.resolved_filing_status`.
- Produces: `HouseholdForm` with extra fields `filing_status: FilingStatus`, `residence_state: str | None`, `ss_pension_taxable_fraction: Decimal`, `social_security_trust_factor: Decimal`; new form-name constants `FILING_STATUS`, `RESIDENCE_STATE`, `SS_PENSION_TAXABLE_FRACTION`, `SOCIAL_SECURITY_TRUST_FACTOR`, and `FILING_STATUSES` / `FILING_STATUS_LABELS`.

- [ ] **Step 1: Write the failing merge-preservation test**

Add to `packages/web/tests/test_app.py`. This test seeds a plan that already has a job + earnings + tax fields, then PATCHes only demographics and asserts the nested income data survives:

```python
from core.job import Job
from core.social_security import AnnualEarnings
from web.forms import FILING_STATUS, RESIDENCE_STATE


def test_patch_household_preserves_jobs_ss_and_tax_fields(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    expected_job_label = "Engineer"
    expected_year = 2022
    expected_state = "CA"
    seeded.household.person1.jobs = [
        Job(label=expected_job_label, annual_income=Decimal("120000"))
    ]
    seeded.household.person1.social_security.earnings_record = [
        AnnualEarnings(year=expected_year, fica_earnings=Decimal("100000"))
    ]
    seeded.household.residence_state = expected_state
    repo.save(plan_id, seeded)

    form_data = _household_form_data()
    del form_data[PERSON2_BIRTH_MONTH]
    del form_data[PERSON2_BIRTH_YEAR]
    del form_data[PERSON2_MAX_AGE_YEARS]
    form_data[FILING_STATUS] = "single"

    response = client.patch(f"{PLAN_HOUSEHOLD}?plan={plan_id}", data=form_data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert [j.label for j in after.household.person1.jobs] == [expected_job_label]
    assert after.household.person1.social_security.earnings_record[0].year == (
        expected_year
    )
    assert after.household.residence_state == expected_state
```

- [ ] **Step 2: Write the failing explicit-filing-status test**

```python
def test_patch_household_writes_explicit_filing_status(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    chosen_status = "single"
    form_data = _household_form_data()
    form_data[HAS_PARTNER] = "on"  # partner present, but user forces single
    form_data[FILING_STATUS] = chosen_status

    response = client.patch(f"{PLAN_HOUSEHOLD}?plan={plan_id}", data=form_data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.filing_status == chosen_status
```

- [ ] **Step 3: Add scaffolding constants, then run once to confirm logical failures**

First add only the four name constants to `packages/web/web/forms.py` so the test imports resolve (structure exists), while leaving `HouseholdForm` and `patch_household` on their current rebuild logic (Step 4 completes the constant set and imports):

```python
FILING_STATUS = "filing_status"
RESIDENCE_STATE = "residence_state"
SS_PENSION_TAXABLE_FRACTION = "ss_pension_taxable_fraction"
SOCIAL_SECURITY_TRUST_FACTOR = "social_security_trust_factor"
```

Then run: `uv run pytest packages/web/tests/test_app.py::test_patch_household_preserves_jobs_ss_and_tax_fields packages/web/tests/test_app.py::test_patch_household_writes_explicit_filing_status -v`
Expected: both fail **logically** — the preserve test raises `AssertionError` (jobs dropped by the old rebuild `apply_to`) and the filing-status test raises `AssertionError` (`filing_status` is `None`, not `"single"`). Neither should be an `ImportError`. If either is structural, the scaffolding above is incomplete — fix it before implementing the merge.

- [ ] **Step 4: Extend `HouseholdForm` and add constants**

Replace the `HouseholdForm` block and add constants in `packages/web/web/forms.py`. Update imports at top:

```python
from typing import get_args

from core.models import (
    AppSettings,
    FilingStatus,
    Household,
    PersonHousehold,
    Plan,
    Portfolio,
)
```

Add name constants near the other `PERSON*` constants:

```python
FILING_STATUS = "filing_status"
RESIDENCE_STATE = "residence_state"
SS_PENSION_TAXABLE_FRACTION = "ss_pension_taxable_fraction"
SOCIAL_SECURITY_TRUST_FACTOR = "social_security_trust_factor"

FILING_STATUSES: tuple[FilingStatus, ...] = get_args(FilingStatus)
FILING_STATUS_LABELS = {
    "single": "Single",
    "married_filing_jointly": "Married filing jointly",
}
```

Replace `HouseholdForm` with a merging implementation:

```python
class HouseholdForm(BaseModel):
    """Flat transport DTO for HTML forms. Constraints live on core.models only."""

    person1_birth_month: int
    person1_birth_year: int
    person1_max_age_years: int
    filing_status: FilingStatus
    residence_state: str | None = None
    ss_pension_taxable_fraction: Decimal = Decimal("0.80")
    social_security_trust_factor: Decimal = Decimal(1)
    has_partner: bool = False
    person2_birth_month: int | None = None
    person2_birth_year: int | None = None
    person2_max_age_years: int | None = None

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        data["person1"].update(
            {
                "birth_month": self.person1_birth_month,
                "birth_year": self.person1_birth_year,
                "max_age_years": self.person1_max_age_years,
            }
        )
        if self.has_partner:
            existing2 = data.get("person2")
            if existing2 is None:
                existing2 = PersonHousehold(
                    birth_month=self.person2_birth_month or 1,
                    birth_year=self.person2_birth_year or 0,
                    max_age_years=self.person2_max_age_years or 1,
                ).model_dump()
            existing2.update(
                {
                    "birth_month": self.person2_birth_month,
                    "birth_year": self.person2_birth_year,
                    "max_age_years": self.person2_max_age_years,
                }
            )
            data["person2"] = existing2
        else:
            data["person2"] = None
        data["filing_status"] = self.filing_status
        data["residence_state"] = self.residence_state or None
        data["ss_pension_taxable_fraction"] = self.ss_pension_taxable_fraction
        data["social_security_trust_factor"] = self.social_security_trust_factor
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})
```

Note: `model_dump()` preserves `jobs`, `social_security`, and any tax fields not overwritten; `Household.model_validate` re-runs all validators (including the sabbatical-window check), so invalid demographics still raise `ValidationError` → 422.

- [ ] **Step 5: Wire the new form fields into `patch_household`**

In `packages/web/web/app.py`, extend the `patch_household` signature and construction. Add imports (`FilingStatus` from `core.models` is not needed here — annotate as `str` at the boundary and let the DTO/Pydantic validate the literal):

```python
    @web_app.patch(PLAN_HOUSEHOLD)
    def patch_household(
        person1_birth_month: Annotated[int, Form()],
        person1_birth_year: Annotated[int, Form()],
        person1_max_age_years: Annotated[int, Form()],
        filing_status: Annotated[str, Form()],
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        residence_state: Annotated[str | None, Form()] = None,
        ss_pension_taxable_fraction: Annotated[Decimal, Form()] = Decimal("0.80"),
        social_security_trust_factor: Annotated[Decimal, Form()] = Decimal(1),
        has_partner: Annotated[bool, Form()] = False,
        person2_birth_month: Annotated[int | None, Form()] = None,
        person2_birth_year: Annotated[int | None, Form()] = None,
        person2_max_age_years: Annotated[int | None, Form()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = HouseholdForm(
                person1_birth_month=person1_birth_month,
                person1_birth_year=person1_birth_year,
                person1_max_age_years=person1_max_age_years,
                filing_status=filing_status,  # type: ignore[arg-type]
                residence_state=residence_state,
                ss_pension_taxable_fraction=ss_pension_taxable_fraction,
                social_security_trust_factor=social_security_trust_factor,
                has_partner=has_partner,
                person2_birth_month=person2_birth_month,
                person2_birth_year=person2_birth_year,
                person2_max_age_years=person2_max_age_years,
            ).apply_to(plan_model)
        except ValidationError as exc:
            return HTMLResponse(_validation_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)
```

- [ ] **Step 6: Add tax fields to the household template**

Append a tax `<fieldset>` inside the existing `<form>` in `packages/web/web/templates/editor_household.html`, before the closing `</form>` (line 73). Prefill filing status from `resolved_filing_status`:

```html
    <fieldset class="tax-fields">
      <legend>Taxes</legend>
      <label>
        Filing status
        <select name="{{ forms.FILING_STATUS }}">
          {% for status in forms.FILING_STATUSES %}
          <option value="{{ status }}"{% if plan.household.resolved_filing_status == status %} selected{% endif %}>{{ forms.FILING_STATUS_LABELS[status] }}</option>
          {% endfor %}
        </select>
      </label>
      <label>
        Residence state
        <input
          type="text"
          name="{{ forms.RESIDENCE_STATE }}"
          value="{{ plan.household.residence_state or '' }}"
          maxlength="2"
          placeholder="e.g. CA"
        >
      </label>
      <label>
        SS &amp; pension taxable fraction
        <input
          type="number"
          step="0.01"
          name="{{ forms.SS_PENSION_TAXABLE_FRACTION }}"
          value="{{ plan.household.ss_pension_taxable_fraction }}"
        >
      </label>
      <label>
        Social Security trust factor
        <input
          type="number"
          step="0.01"
          name="{{ forms.SOCIAL_SECURITY_TRUST_FACTOR }}"
          value="{{ plan.household.social_security_trust_factor }}"
        >
      </label>
    </fieldset>
```

- [ ] **Step 7: Make the `index.html` `planUpdated` trigger generic**

In `packages/web/web/templates/index.html`, replace the `isPlanForm` condition so any editor form targeting a `/plan/` route dispatches `planUpdated` (removes per-route coupling for later sections):

```javascript
    const isPlanForm =
      form.tagName === "FORM" &&
      patchTarget &&
      patchTarget.startsWith("/plan/");
```

- [ ] **Step 8: Update the existing single-person household test to send filing status**

`_household_form_data()` must include a filing status so existing PATCH tests keep passing. Update the helper in `packages/web/tests/test_app.py`:

```python
def _household_form_data() -> dict[str, str]:
    plan = default_plan()
    p1 = plan.household.person1
    p2 = plan.household.person2
    assert p2 is not None
    return {
        PERSON1_BIRTH_MONTH: str(p1.birth_month),
        PERSON1_BIRTH_YEAR: str(p1.birth_year),
        PERSON1_MAX_AGE_YEARS: str(p1.max_age_years),
        FILING_STATUS: plan.household.resolved_filing_status,
        PERSON2_BIRTH_MONTH: str(p2.birth_month),
        PERSON2_BIRTH_YEAR: str(p2.birth_year),
        PERSON2_MAX_AGE_YEARS: str(p2.max_age_years),
    }
```

Add `FILING_STATUS` to the `from web.forms import (...)` block at the top of the test file.

- [ ] **Step 9: Run the household tests + full web suite**

Run: `uv run pytest packages/web/tests/test_app.py -v`
Expected: PASS (new tests + all previously-passing household/portfolio/settings tests).

- [ ] **Step 10: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/app.py packages/web/web/templates/editor_household.html packages/web/web/templates/index.html packages/web/tests/test_app.py
git commit -m "fix(web): preserve nested household data on demographic PATCH; add tax fields"
```

---

### Task 3: Shared boundary parsing + indexed-row collectors

Central helper module that turns flat form fields into `Boundary` values and back, plus collectors for indexed list rows. Pure functions, fully unit-tested with an injected `today`. Also records the form-DTO decision in `packages/web/AGENTS.md`.

**Files:**
- Create: `packages/web/web/boundaries.py`
- Modify: `packages/web/AGENTS.md`
- Test: `packages/web/tests/test_boundaries.py`

**Interfaces:**
- Produces:
  - Wire-kind constants `KIND_NONE="none"`, `KIND_NOW="now"`, `KIND_CALENDAR="calendar_month"`, `KIND_PERSON_AGE="person_age"`, `KIND_PERSON_MAX_AGE="person_max_age"`.
  - `parse_boundary(*, kind, year=None, month=None, person=None, age_years=None, age_months=None, today: date) -> Boundary | None`
  - `to_form(boundary: Boundary | None) -> dict[str, object]` (for template prefill; `"now"` is never produced because it stamps to calendar at save)
  - `collect_indexed_rows(form, prefix) -> list[list[tuple[str, str]]]` (ordered rows; each row is ordered `(rest_key, value)` pairs)
  - `row_scalar(row, field, default="") -> str`
  - `sub_rows(row, prefix) -> list[list[tuple[str, str]]]` (nested sub-list, e.g. `sabbaticals`)
  - `row_boundary(row, field_prefix, *, today) -> Boundary | None`

- [ ] **Step 1: Write failing `parse_boundary` tests**

Create `packages/web/tests/test_boundaries.py`:

```python
from datetime import date

import pytest
from core.streams import (
    CalendarMonthBoundary,
    PersonAgeBoundary,
    PersonMaxAgeBoundary,
)
from web import boundaries


def test_parse_boundary_none_returns_none() -> None:
    assert boundaries.parse_boundary(kind=boundaries.KIND_NONE, today=date(2026, 7, 19)) is None


def test_parse_boundary_now_stamps_current_calendar_month() -> None:
    today = date(2026, 7, 19)

    result = boundaries.parse_boundary(kind=boundaries.KIND_NOW, today=today)

    assert result == CalendarMonthBoundary(year=today.year, month=today.month)


def test_parse_boundary_calendar_uses_year_and_month() -> None:
    expected = CalendarMonthBoundary(year=2030, month=4)

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_CALENDAR,
        year=expected.year,
        month=expected.month,
        today=date(2026, 7, 19),
    )

    assert result == expected


def test_parse_boundary_person_age_combines_years_and_months() -> None:
    person = "person1"
    age_years = 65
    age_months = 2

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_PERSON_AGE,
        person=person,
        age_years=age_years,
        age_months=age_months,
        today=date(2026, 7, 19),
    )

    assert result == PersonAgeBoundary(
        person=person, age_months=age_years * 12 + age_months
    )


def test_parse_boundary_person_max_age_is_symbolic() -> None:
    person = "person2"

    result = boundaries.parse_boundary(
        kind=boundaries.KIND_PERSON_MAX_AGE, person=person, today=date(2026, 7, 19)
    )

    assert result == PersonMaxAgeBoundary(person=person)


def test_parse_boundary_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="unknown boundary kind"):
        boundaries.parse_boundary(kind="bogus", today=date(2026, 7, 19))
```

- [ ] **Step 2: Write failing collector tests**

Append to `packages/web/tests/test_boundaries.py`:

```python
from starlette.datastructures import FormData


def test_collect_indexed_rows_groups_and_orders_by_index() -> None:
    first_label = "First"
    second_label = "Second"
    form = FormData(
        [
            ("jobs[1].label", second_label),
            ("jobs[0].label", first_label),
            ("portfolio", "ignored"),
        ]
    )

    rows = boundaries.collect_indexed_rows(form, "jobs")

    assert [boundaries.row_scalar(r, "label") for r in rows] == [
        first_label,
        second_label,
    ]


def test_sub_rows_extracts_nested_list() -> None:
    first_fraction = "0.5"
    second_fraction = "0.25"
    form = FormData(
        [
            ("jobs[0].label", "Eng"),
            ("jobs[0].sabbaticals[0].remaining_fraction", first_fraction),
            ("jobs[0].sabbaticals[1].remaining_fraction", second_fraction),
        ]
    )
    (row,) = boundaries.collect_indexed_rows(form, "jobs")

    sabbaticals = boundaries.sub_rows(row, "sabbaticals")

    assert [boundaries.row_scalar(s, "remaining_fraction") for s in sabbaticals] == [
        first_fraction,
        second_fraction,
    ]


def test_row_boundary_reads_prefixed_fields() -> None:
    today = date(2026, 7, 19)
    person = "person1"
    age_years = 50
    form = FormData(
        [
            ("jobs[0].start_kind", boundaries.KIND_PERSON_AGE),
            ("jobs[0].start_person", person),
            ("jobs[0].start_age_years", str(age_years)),
            ("jobs[0].start_age_months", "0"),
        ]
    )
    (row,) = boundaries.collect_indexed_rows(form, "jobs")

    result = boundaries.row_boundary(row, "start", today=today)

    assert result == PersonAgeBoundary(person=person, age_months=age_years * 12)
```

- [ ] **Step 3: Add a stub module, then run once to confirm a logical failure**

Create `packages/web/web/boundaries.py` with the wire-kind constants and stub function bodies so imports resolve but no logic exists yet:

```python
from datetime import date

KIND_NONE = "none"
KIND_NOW = "now"
KIND_CALENDAR = "calendar_month"
KIND_PERSON_AGE = "person_age"
KIND_PERSON_MAX_AGE = "person_max_age"


def parse_boundary(*, kind, today: date, **kwargs):
    raise NotImplementedError


def to_form(boundary):
    raise NotImplementedError


def collect_indexed_rows(form, prefix):
    raise NotImplementedError


def row_scalar(row, field, default=""):
    raise NotImplementedError


def sub_rows(row, prefix):
    raise NotImplementedError


def row_boundary(row, field_prefix, *, today):
    raise NotImplementedError
```

Run: `uv run pytest packages/web/tests/test_boundaries.py -v`
Expected: every test fails **logically** with `NotImplementedError` (module + symbols import cleanly), not `ModuleNotFoundError`/`ImportError`. If any failure is structural, fix the stub signatures before implementing.

- [ ] **Step 4: Implement `web/boundaries.py`**

Replace the stub with the full implementation:

```python
from __future__ import annotations

import re
from datetime import date
from typing import cast

from core.streams import (
    Boundary,
    CalendarMonthBoundary,
    PersonAgeBoundary,
    PersonId,
    PersonMaxAgeBoundary,
)
from starlette.datastructures import FormData

KIND_NONE = "none"
KIND_NOW = "now"
KIND_CALENDAR = "calendar_month"
KIND_PERSON_AGE = "person_age"
KIND_PERSON_MAX_AGE = "person_max_age"

_ROW_RE = re.compile(r"^(?P<prefix>\w+)\[(?P<index>\d+)\]\.(?P<rest>.+)$")


def _int_or_none(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def parse_boundary(
    *,
    kind: str,
    year: int | None = None,
    month: int | None = None,
    person: str | None = None,
    age_years: int | None = None,
    age_months: int | None = None,
    today: date,
) -> Boundary | None:
    """Turn flat form values into a `Boundary` (or `None`). `today` stamps "now"."""
    if kind == KIND_NONE:
        return None
    if kind == KIND_NOW:
        return CalendarMonthBoundary(year=today.year, month=today.month)
    if kind == KIND_CALENDAR:
        if year is None or month is None:
            raise ValueError("calendar boundary requires year and month")
        return CalendarMonthBoundary(year=year, month=month)
    if kind == KIND_PERSON_AGE:
        if person is None:
            raise ValueError("person_age boundary requires person")
        total_months = (age_years or 0) * 12 + (age_months or 0)
        return PersonAgeBoundary(person=cast(PersonId, person), age_months=total_months)
    if kind == KIND_PERSON_MAX_AGE:
        if person is None:
            raise ValueError("person_max_age boundary requires person")
        return PersonMaxAgeBoundary(person=cast(PersonId, person))
    raise ValueError(f"unknown boundary kind: {kind!r}")


def to_form(boundary: Boundary | None) -> dict[str, object]:
    """Render an existing boundary into template prefill state."""
    if boundary is None:
        return {"kind": KIND_NONE}
    if isinstance(boundary, CalendarMonthBoundary):
        return {"kind": KIND_CALENDAR, "year": boundary.year, "month": boundary.month}
    if isinstance(boundary, PersonAgeBoundary):
        return {
            "kind": KIND_PERSON_AGE,
            "person": boundary.person,
            "age_years": boundary.age_months // 12,
            "age_months": boundary.age_months % 12,
        }
    return {"kind": KIND_PERSON_MAX_AGE, "person": boundary.person}


def collect_indexed_rows(form: FormData, prefix: str) -> list[list[tuple[str, str]]]:
    """Group `prefix[i].rest` form fields into ordered rows of (rest, value) pairs."""
    rows: dict[int, list[tuple[str, str]]] = {}
    for key, value in form.multi_items():
        match = _ROW_RE.match(key)
        if match is None or match.group("prefix") != prefix:
            continue
        rows.setdefault(int(match.group("index")), []).append(
            (match.group("rest"), value)
        )
    return [rows[index] for index in sorted(rows)]


def row_scalar(row: list[tuple[str, str]], field: str, default: str = "") -> str:
    for key, value in row:
        if key == field:
            return value
    return default


def sub_rows(row: list[tuple[str, str]], prefix: str) -> list[list[tuple[str, str]]]:
    rows: dict[int, list[tuple[str, str]]] = {}
    for key, value in row:
        match = _ROW_RE.match(key)
        if match is None or match.group("prefix") != prefix:
            continue
        rows.setdefault(int(match.group("index")), []).append(
            (match.group("rest"), value)
        )
    return [rows[index] for index in sorted(rows)]


def row_boundary(
    row: list[tuple[str, str]], field_prefix: str, *, today: date
) -> Boundary | None:
    return parse_boundary(
        kind=row_scalar(row, f"{field_prefix}_kind", KIND_NONE),
        year=_int_or_none(row_scalar(row, f"{field_prefix}_year")),
        month=_int_or_none(row_scalar(row, f"{field_prefix}_month")),
        person=row_scalar(row, f"{field_prefix}_person") or None,
        age_years=_int_or_none(row_scalar(row, f"{field_prefix}_age_years")),
        age_months=_int_or_none(row_scalar(row, f"{field_prefix}_age_months")),
        today=today,
    )
```

- [ ] **Step 5: Run the boundary tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_boundaries.py -v`
Expected: PASS

- [ ] **Step 6: Document the DTO decision in `packages/web/AGENTS.md`**

Replace the "Future (Phase 4c+)" bullet under "Template layout conventions" with the resolved decision:

```markdown
- **Form DTOs (decided Phase 4c):** hand-written flat DTOs + shared helpers in `web/boundaries.py`. We rejected `create_model`-generated DTOs because list sections (jobs, sabbaticals, manual income) use indexed/nested field names (`jobs[0].sabbaticals[1].start_kind`) that FastAPI `Form()` cannot bind; those routes read `await request.form()` and parse with `boundaries.collect_indexed_rows` / `row_boundary`. Boundary controls use a `{prefix}_kind` selector plus `{prefix}_year/_month/_person/_age_years/_age_months`. "Now" stamps a `CalendarMonthBoundary` at save; "max age" persists a `PersonMaxAgeBoundary`.
```

- [ ] **Step 7: Run lint/type on the new module**

Run: `uv run ruff check packages/web/web/boundaries.py && uv run pyright packages/web/web/boundaries.py`
Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add packages/web/web/boundaries.py packages/web/tests/test_boundaries.py packages/web/AGENTS.md
git commit -m "feat(web): add shared boundary parsing and indexed-row collectors"
```

---

### Task 4: Reusable boundary-control macro + list JS

A Jinja macro renders one boundary control (kind selector + conditional inputs); a small static script toggles which inputs are visible and clones/removes list rows. Registers the `boundaries` module as a Jinja global for section templates.

**Files:**
- Create: `packages/web/web/templates/_boundary.html`
- Create: `packages/web/web/static/editor_lists.js`
- Modify: `packages/web/web/app.py` (register `boundaries` Jinja global)
- Modify: `packages/web/web/templates/index.html` (load the script + init hooks)
- Test: `packages/web/tests/test_boundary_macro.py`

**Interfaces:**
- Consumes: `web.boundaries.to_form` (section templates call it to build `current`).
- Produces: Jinja macro `boundary_control(name_prefix, current, people, allow_none=False, allow_now=False, allow_max_age=False, none_label="—")` in `_boundary.html`. `current` is a `boundaries.to_form(...)` dict. `people` is a list of `(person_id, label)` tuples for present persons.

- [ ] **Step 1: Write failing macro tests**

Create `packages/web/tests/test_boundary_macro.py`:

```python
from web.app import templates


def _render(**kwargs) -> str:
    module = templates.get_template("_boundary.html").module
    return str(
        module.boundary_control(
            "start", {"kind": "none"}, [("person1", "You")], **kwargs
        )
    )


def test_boundary_control_includes_now_when_allowed() -> None:
    assert 'value="now"' in _render(allow_now=True, allow_none=True)


def test_boundary_control_omits_now_by_default() -> None:
    assert 'value="now"' not in _render(allow_none=True)


def test_boundary_control_includes_max_age_when_allowed() -> None:
    assert 'value="person_max_age"' in _render(allow_max_age=True)


def test_boundary_control_names_use_prefix() -> None:
    markup = _render(allow_none=True)

    assert 'name="start_kind"' in markup
    assert 'name="start_year"' in markup
    assert 'name="start_person"' in markup
```

- [ ] **Step 2: Add a stub macro, then run once to confirm a logical failure**

Create `packages/web/web/templates/_boundary.html` with a macro that accepts the full signature but renders nothing, so the template resolves but the option-filtering logic is absent:

```html
{% macro boundary_control(name_prefix, current, people, allow_none=False, allow_now=False, allow_max_age=False, none_label="—") -%}
{%- endmacro %}
```

Run: `uv run pytest packages/web/tests/test_boundary_macro.py -v`
Expected: the tests fail **logically** with `AssertionError` (e.g. `'value="now"' not in ''`) because the macro renders empty markup — not a `TemplateNotFound`. If it is structural, fix the stub before implementing.

- [ ] **Step 3: Implement `_boundary.html`**

Replace the stub with the full macro:

```html
{% macro boundary_control(name_prefix, current, people, allow_none=False, allow_now=False, allow_max_age=False, none_label="—") -%}
<span class="boundary-control" data-prefix="{{ name_prefix }}">
  <select name="{{ name_prefix }}_kind" class="boundary-kind">
    {% if allow_none %}<option value="none"{% if current.kind == 'none' %} selected{% endif %}>{{ none_label }}</option>{% endif %}
    {% if allow_now %}<option value="now"{% if current.kind == 'now' %} selected{% endif %}>Now</option>{% endif %}
    <option value="calendar_month"{% if current.kind == 'calendar_month' %} selected{% endif %}>Calendar date</option>
    <option value="person_age"{% if current.kind == 'person_age' %} selected{% endif %}>At age</option>
    {% if allow_max_age %}<option value="person_max_age"{% if current.kind == 'person_max_age' %} selected{% endif %}>Max age</option>{% endif %}
  </select>
  <span class="boundary-part" data-kinds="calendar_month">
    <input type="number" name="{{ name_prefix }}_year" value="{{ current.year if current.kind == 'calendar_month' else '' }}" placeholder="Year">
    <input type="number" name="{{ name_prefix }}_month" min="1" max="12" value="{{ current.month if current.kind == 'calendar_month' else '' }}" placeholder="Month">
  </span>
  <span class="boundary-part" data-kinds="person_age person_max_age">
    <select name="{{ name_prefix }}_person">
      {% for pid, label in people %}
      <option value="{{ pid }}"{% if current.person == pid %} selected{% endif %}>{{ label }}</option>
      {% endfor %}
    </select>
  </span>
  <span class="boundary-part" data-kinds="person_age">
    <input type="number" name="{{ name_prefix }}_age_years" value="{{ current.age_years if current.kind == 'person_age' else '' }}" placeholder="Years">
    <input type="number" name="{{ name_prefix }}_age_months" min="0" max="11" value="{{ current.age_months if current.kind == 'person_age' else '' }}" placeholder="Months">
  </span>
</span>
{%- endmacro %}
```

- [ ] **Step 4: Run macro tests to verify they pass**

Run: `uv run pytest packages/web/tests/test_boundary_macro.py -v`
Expected: PASS

- [ ] **Step 5: Create `static/editor_lists.js`**

Toggles boundary parts by selected kind and clones/removes list rows. Rows use a `<template class="row-template">` cloned into a `.rows` container; add/remove re-index `name` attributes.

Row containers carry `data-prefix` (`jobs`, `sabbaticals`, `streams`). Add/remove buttons carry bare `data-add-row` / `data-remove-row` attributes and are scoped by `closest(".rows")`, so nested sabbatical lists inside a job row work without global lookups. `reindex` renumbers the `prefix[i]` segment *anywhere* in a field name (so a job renumber preserves nested sabbatical indices) and recurses into nested `.rows`.

```javascript
(function () {
  function syncBoundary(control) {
    const kind = control.querySelector(".boundary-kind").value;
    control.querySelectorAll(".boundary-part").forEach(function (part) {
      const kinds = (part.dataset.kinds || "").split(" ");
      part.hidden = kinds.indexOf(kind) === -1;
    });
  }

  function rowChildren(container) {
    return Array.prototype.filter.call(container.children, function (child) {
      return child.classList.contains("row");
    });
  }

  function reindex(container) {
    const prefix = container.dataset.prefix;
    const pattern = new RegExp(prefix + "\\[\\d+\\]");
    rowChildren(container).forEach(function (row, index) {
      row.querySelectorAll("[name]").forEach(function (field) {
        field.name = field.name.replace(pattern, prefix + "[" + index + "]");
      });
      row.querySelectorAll(".rows").forEach(reindex);
    });
  }

  function initAll() {
    document.querySelectorAll(".boundary-control").forEach(syncBoundary);
    document.querySelectorAll(".rows").forEach(reindex);
  }

  document.addEventListener("change", function (event) {
    if (event.target.classList.contains("boundary-kind")) {
      syncBoundary(event.target.closest(".boundary-control"));
    }
  });

  document.addEventListener("click", function (event) {
    const addButton = event.target.closest("[data-add-row]");
    if (addButton) {
      event.preventDefault();
      const container = addButton.closest(".rows");
      const template = container.querySelector(":scope > .row-template");
      const clone = template.content.firstElementChild.cloneNode(true);
      container.insertBefore(clone, template);
      reindex(container);
      clone.querySelectorAll(".boundary-control").forEach(syncBoundary);
      container
        .closest("form")
        .dispatchEvent(new Event("change", { bubbles: true }));
      return;
    }
    const removeButton = event.target.closest("[data-remove-row]");
    if (removeButton) {
      event.preventDefault();
      const row = removeButton.closest(".row");
      const container = row.parentElement;
      const form = row.closest("form");
      row.remove();
      reindex(container);
      form.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });

  document.addEventListener("DOMContentLoaded", initAll);
  document.body.addEventListener("htmx:afterSettle", initAll);
})();
```

- [ ] **Step 6: Register `boundaries` Jinja global and load the script**

In `packages/web/web/app.py`, add the import and global registration next to the existing globals:

```python
from web import boundaries, charts, forms, routes, sections
...
templates.env.globals["boundaries"] = boundaries
```

In `packages/web/web/templates/index.html`, add the script tag at the end of the `{% block body %}` (after the existing `<script>` block, before `{% endblock %}`):

```html
<script src="{{ routes.STATIC }}/editor_lists.js"></script>
```

- [ ] **Step 7: Run the web suite (regression check on globals wiring)**

Run: `uv run pytest packages/web/tests/test_app.py packages/web/tests/test_boundary_macro.py -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add packages/web/web/templates/_boundary.html packages/web/web/static/editor_lists.js packages/web/web/app.py packages/web/web/templates/index.html packages/web/tests/test_boundary_macro.py
git commit -m "feat(web): add reusable boundary-control macro and list editor JS"
```

---

### Task 5: Jobs section (jobs, sabbaticals, CalSTRS pension)

Per-person jobs editor: add/edit/remove jobs, per-job start/end boundaries, a nested sabbatical list, and an optional CalSTRS-2%-at-62 formula pension preset. Full-section replace via one debounced form per present person.

**Files:**
- Modify: `packages/web/web/routes.py` (add `EDITOR_JOBS`, `PLAN_JOBS`)
- Modify: `packages/web/web/sections.py` (add `JOBS_TITLE`)
- Modify: `packages/web/web/forms.py` (add `JobsForm`, `_job_from_row`, `JOBS_PREFIX`)
- Modify: `packages/web/web/app.py` (add `_error_message`, `editor_jobs` GET, `patch_jobs` PATCH)
- Create: `packages/web/web/templates/editor_jobs.html`
- Modify: `packages/web/web/templates/index.html` (include the partial)
- Test: `packages/web/tests/test_jobs_editor.py`

**Interfaces:**
- Consumes: `web.boundaries.{collect_indexed_rows, sub_rows, row_scalar, row_boundary, to_form, KIND_*}`; `core.job.{Job, FormulaPension, SabbaticalWindow}`; `domain.statutory.pension.{CALSTRS_2_AT_62_AGE_FACTORS, age_factors_from_statutory}`.
- Produces: `JOBS_PREFIX = "jobs"`; `JobsForm(person: PersonId, jobs: list[Job])` with `JobsForm.from_form(form, *, person, today) -> JobsForm` and `apply_to(plan) -> Plan` (raises `ValueError` if `person` absent); routes `EDITOR_JOBS = "/editor/jobs"`, `PLAN_JOBS = "/plan/jobs"`.

- [ ] **Step 1: Write failing route/persistence tests**

Create `packages/web/tests/test_jobs_editor.py`:

```python
from decimal import Decimal

from core.job import Job
from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from fastapi.testclient import TestClient
from web.routes import EDITOR_JOBS, PLAN_JOBS
from web.sections import JOBS_TITLE


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_jobs_adds_job_to_person1(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_label = "Engineer"
    expected_income = "150000"
    data = {
        "jobs[0].label": expected_label,
        "jobs[0].annual_income": expected_income,
        "jobs[0].annual_tax_deferred": "0",
        "jobs[0].annual_raise": "0",
        "jobs[0].social_security_eligible": "on",
        "jobs[0].start_kind": "now",
        "jobs[0].end_kind": "none",
    }

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    jobs = after.household.person1.jobs
    assert [j.label for j in jobs] == [expected_label]
    assert jobs[0].annual_income == Decimal(expected_income)


def test_patch_jobs_empty_form_clears_jobs(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.household.person1.jobs = [Job(annual_income=Decimal("100000"))]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.jobs == []


def test_patch_jobs_attaches_calstrs_pension(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_table = age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS)
    data = {
        "jobs[0].annual_income": "100000",
        "jobs[0].start_kind": "now",
        "jobs[0].end_kind": "none",
        "jobs[0].pension_enabled": "on",
        "jobs[0].pension_service_start_kind": "calendar_month",
        "jobs[0].pension_service_start_year": "2015",
        "jobs[0].pension_service_start_month": "8",
        "jobs[0].pension_claim_kind": "person_age",
        "jobs[0].pension_claim_person": "person1",
        "jobs[0].pension_claim_age_years": "62",
        "jobs[0].pension_claim_age_months": "0",
    }

    response = client.patch(f"{PLAN_JOBS}?plan={plan_id}&person=person1", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    pension = after.household.person1.jobs[0].pension
    assert pension is not None
    assert pension.age_factor_table == expected_table


def test_patch_jobs_for_absent_partner_returns_422(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    single = repo.get_by_id(plan_id)
    assert single is not None
    single.household.person2 = None
    repo.save(plan_id, single)

    response = client.patch(
        f"{PLAN_JOBS}?plan={plan_id}&person=person2",
        data={
            "jobs[0].annual_income": "1000",
            "jobs[0].start_kind": "now",
            "jobs[0].end_kind": "none",
        },
    )

    assert response.status_code == 422


def test_editor_jobs_get_renders_section(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_JOBS}?plan={plan_id}")

    assert response.status_code == 200
    assert JOBS_TITLE in response.text
```

- [ ] **Step 2: Add scaffolding, then run once to confirm a logical failure**

Add the route constants (Step 3), section title (Step 3), a `JobsForm` stub whose `apply_to` returns the plan unchanged, and no-op `editor_jobs`/`patch_jobs` routes that resolve the plan and return `Response(status_code=200)` without persisting. This gives the tests real endpoints to hit so they fail on behavior, not imports.

Run: `uv run pytest packages/web/tests/test_jobs_editor.py -v`
Expected: the persistence tests fail **logically** — `AssertionError` (no job persisted / jobs not cleared) — and `test_editor_jobs_get_renders_section` fails `AssertionError` (title absent from the empty stub template) or passes once the section constant renders. None should be an `ImportError`. If any is structural, complete the scaffolding before implementing the real logic in Steps 3–8.

- [ ] **Step 3: Add route and section constants**

`packages/web/web/routes.py`:

```python
EDITOR_JOBS = "/editor/jobs"
PLAN_JOBS = "/plan/jobs"
```

`packages/web/web/sections.py`:

```python
JOBS_TITLE = "Jobs"
```

- [ ] **Step 4: Add `JobsForm` and `_job_from_row` to `forms.py`**

Add imports at the top of `packages/web/web/forms.py`:

```python
from datetime import date

from core.job import FormulaPension, Job, SabbaticalWindow
from core.streams import PersonId
from domain.statutory.pension import (
    CALSTRS_2_AT_62_AGE_FACTORS,
    age_factors_from_statutory,
)
from starlette.datastructures import FormData

from web import boundaries

JOBS_PREFIX = "jobs"
_TRUE = {"on", "true", "1"}
```

Add the builders (near the bottom of the module):

```python
def _job_from_row(row: list[tuple[str, str]], *, today: date) -> Job:
    pension: dict[str, object] | None = None
    if boundaries.row_scalar(row, "pension_enabled") in _TRUE:
        pension = {
            "service_start": boundaries.row_boundary(
                row, "pension_service_start", today=today
            ),
            "claim": boundaries.row_boundary(row, "pension_claim", today=today),
            "age_factor_table": age_factors_from_statutory(CALSTRS_2_AT_62_AGE_FACTORS),
            "final_comp_averaging_months": int(
                boundaries.row_scalar(row, "pension_averaging_months", "36")
            ),
            "trust_factor": Decimal(boundaries.row_scalar(row, "pension_trust_factor", "1")),
            "benefit_real_growth_rate": Decimal(
                boundaries.row_scalar(row, "pension_growth", "0")
            ),
        }
    sabbaticals = [
        {
            "start": boundaries.row_boundary(sab, "start", today=today),
            "end": boundaries.row_boundary(sab, "end", today=today),
            "remaining_fraction": Decimal(
                boundaries.row_scalar(sab, "remaining_fraction", "0")
            ),
        }
        for sab in boundaries.sub_rows(row, "sabbaticals")
    ]
    return Job.model_validate(
        {
            "label": boundaries.row_scalar(row, "label") or None,
            "annual_income": Decimal(boundaries.row_scalar(row, "annual_income", "0")),
            "annual_tax_deferred": Decimal(
                boundaries.row_scalar(row, "annual_tax_deferred", "0")
            ),
            "annual_raise": Decimal(boundaries.row_scalar(row, "annual_raise", "0")),
            "start": boundaries.row_boundary(row, "start", today=today),
            "end": boundaries.row_boundary(row, "end", today=today),
            "social_security_eligible": boundaries.row_scalar(
                row, "social_security_eligible"
            )
            in _TRUE,
            "sabbaticals": sabbaticals,
            "pension": pension,
        }
    )


class JobsForm:
    def __init__(self, *, person: PersonId, jobs: list[Job]) -> None:
        self.person = person
        self.jobs = jobs

    @classmethod
    def from_form(
        cls, form: FormData, *, person: PersonId, today: date
    ) -> JobsForm:
        rows = boundaries.collect_indexed_rows(form, JOBS_PREFIX)
        return cls(person=person, jobs=[_job_from_row(row, today=today) for row in rows])

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        if data.get(self.person) is None:
            raise ValueError("Cannot edit jobs for a partner who is not on the plan")
        data[self.person]["jobs"] = [job.model_dump() for job in self.jobs]
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})
```

Note: `JobsForm` is a plain class (not a `BaseModel`) because it carries an already-validated `list[Job]`, not flat transport scalars — the flat parsing happens in `_job_from_row` via the shared collectors. `Job.model_validate` accepts the `Boundary` instances returned by `row_boundary`; a required pension/sabbatical boundary submitted as `none` becomes `None` and raises `ValidationError`.

- [ ] **Step 5: Add the `_error_message` helper and job routes to `app.py`**

Add `from datetime import date` to the imports and `JobsForm` to the `web.forms` import. Add a shared error helper next to `_validation_message`:

```python
def _error_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return _validation_message(exc)
    return str(exc)
```

In `_register_editor_routes`, add:

```python
    @web_app.get(routes.EDITOR_JOBS, response_class=HTMLResponse)
    def editor_jobs(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_jobs.html",
            {"plan_id": plan_id, "plan": plan_model},
        )
```

In `_register_patch_routes`, add:

```python
    @web_app.patch(routes.PLAN_JOBS)
    async def patch_jobs(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        form = await request.form()
        try:
            updated = JobsForm.from_form(
                form, person=person, today=date.today()
            ).apply_to(plan_model)
        except (ValidationError, ValueError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)
```

`person` is annotated `str` at the boundary; `JobsForm.from_form`'s `person: PersonId` and the `data.get(self.person)` merge tolerate any string (unknown person → `ValueError` → 422). Add a `# type: ignore[arg-type]` on the `from_form(..., person=person, ...)` call if pyright flags the `str`→`PersonId` narrowing.

- [ ] **Step 6: Create `editor_jobs.html`**

```html
{% import "_boundary.html" as boundary %}
{% set people = [("person1", "You", plan.household.person1)] %}
{% if plan.household.person2 %}{% set people = people + [("person2", "Partner", plan.household.person2)] %}{% endif %}
{% set person_options = people | map("first") | list %}
{% set person_choices = [] %}

{% macro sabbatical_row(prefix, sab, choices) %}
<fieldset class="row sabbatical-row">
  <button type="button" data-remove-row>Remove sabbatical</button>
  <div class="boundary-field">Start {{ boundary.boundary_control(prefix ~ ".start", boundaries.to_form(sab.start) if sab else {"kind": boundaries.KIND_CALENDAR}, choices) }}</div>
  <div class="boundary-field">End {{ boundary.boundary_control(prefix ~ ".end", boundaries.to_form(sab.end) if sab else {"kind": boundaries.KIND_CALENDAR}, choices) }}</div>
  <label>Remaining fraction
    <input type="number" step="0.01" min="0" max="1" name="{{ prefix }}.remaining_fraction" value="{{ sab.remaining_fraction if sab else '0' }}">
  </label>
</fieldset>
{% endmacro %}

{% macro job_row(index, job, choices) %}
<fieldset class="row job-row">
  <button type="button" data-remove-row>Remove job</button>
  <label>Label <input type="text" name="jobs[{{ index }}].label" value="{{ (job.label or '') if job else '' }}"></label>
  <label>Annual income <input type="number" step="0.01" name="jobs[{{ index }}].annual_income" value="{{ job.annual_income if job else '0' }}"></label>
  <label>Annual tax-deferred <input type="number" step="0.01" name="jobs[{{ index }}].annual_tax_deferred" value="{{ job.annual_tax_deferred if job else '0' }}"></label>
  <label>Annual raise <input type="number" step="0.001" name="jobs[{{ index }}].annual_raise" value="{{ job.annual_raise if job else '0' }}"></label>
  <label><input type="checkbox" name="jobs[{{ index }}].social_security_eligible" value="on"{% if (not job) or job.social_security_eligible %} checked{% endif %}> Social Security eligible</label>
  <div class="boundary-field">Start {{ boundary.boundary_control("jobs[" ~ index ~ "].start", boundaries.to_form(job.start) if job else {"kind": boundaries.KIND_NOW}, choices, allow_now=True, allow_none=True, none_label="Plan start") }}</div>
  <div class="boundary-field">End {{ boundary.boundary_control("jobs[" ~ index ~ "].end", boundaries.to_form(job.end) if job else {"kind": boundaries.KIND_NONE}, choices, allow_max_age=True, allow_none=True, none_label="Plan horizon") }}</div>
  <div class="rows" data-prefix="sabbaticals">
    {% if job %}{% for sab in job.sabbaticals %}{{ sabbatical_row("jobs[" ~ index ~ "].sabbaticals[" ~ loop.index0 ~ "]", sab, choices) }}{% endfor %}{% endif %}
    <template class="row-template">{{ sabbatical_row("jobs[" ~ index ~ "].sabbaticals[0]", none, choices) }}</template>
    <button type="button" data-add-row>Add sabbatical</button>
  </div>
  <label><input type="checkbox" name="jobs[{{ index }}].pension_enabled" value="on"{% if job and job.pension %} checked{% endif %}> CalSTRS 2% at 62 pension</label>
  <a href="https://github.com/chriskelly/LifeFinances/issues/197" target="_blank" rel="noopener" title="Vote for a richer pension editor">More pension options (#197)</a>
  <div class="pension-fields">
    <div class="boundary-field">Service start {{ boundary.boundary_control("jobs[" ~ index ~ "].pension_service_start", boundaries.to_form(job.pension.service_start) if (job and job.pension) else {"kind": boundaries.KIND_CALENDAR}, choices, allow_max_age=True) }}</div>
    <div class="boundary-field">Claim {{ boundary.boundary_control("jobs[" ~ index ~ "].pension_claim", boundaries.to_form(job.pension.claim) if (job and job.pension) else {"kind": boundaries.KIND_PERSON_AGE}, choices, allow_max_age=True) }}</div>
    <label>Averaging months <input type="number" name="jobs[{{ index }}].pension_averaging_months" value="{{ job.pension.final_comp_averaging_months if (job and job.pension) else '36' }}"></label>
    <label>Trust factor <input type="number" step="0.01" name="jobs[{{ index }}].pension_trust_factor" value="{{ job.pension.trust_factor if (job and job.pension) else '1' }}"></label>
    <label>Benefit real growth <input type="number" step="0.001" name="jobs[{{ index }}].pension_growth" value="{{ job.pension.benefit_real_growth_rate if (job and job.pension) else '0' }}"></label>
  </div>
</fieldset>
{% endmacro %}

<section class="editor-section">
  <h2>{{ sections.JOBS_TITLE }}</h2>
  {% for pid, plabel, person in people %}
  <form
    hx-patch="{{ routes.PLAN_JOBS }}?plan={{ plan_id }}&person={{ pid }}"
    hx-trigger="input changed delay:750ms, change delay:750ms"
    hx-swap="none"
  >
    <h3>{{ plabel }}</h3>
    <div class="rows" data-prefix="jobs">
      {% for job in person.jobs %}{{ job_row(loop.index0, job, people) }}{% endfor %}
      <template class="row-template">{{ job_row(0, none, people) }}</template>
      <button type="button" data-add-row>Add job</button>
    </div>
  </form>
  {% endfor %}
</section>
```

Note: `boundary_control` takes `people` (the `(pid, label, person)` tuples) as its `people` arg; it only reads the first two positional items per tuple in its `for pid, label in people` loop — Jinja unpacks the first two and ignores the third, so passing the 3-tuple list is fine.

- [ ] **Step 7: Wait — fix the boundary macro unpacking**

The macro's `{% for pid, label in people %}` will raise if `people` rows are 3-tuples. Change the macro loop in `_boundary.html` to tolerate extra items:

```html
    {% for person in people %}
      <option value="{{ person[0] }}"{% if current.person == person[0] %} selected{% endif %}>{{ person[1] }}</option>
    {% endfor %}
```

Re-run the Task 4 macro tests (`_render` passes 2-tuples, still valid): `uv run pytest packages/web/tests/test_boundary_macro.py -v` → PASS.

- [ ] **Step 8: Include the jobs partial in `index.html`**

In `packages/web/web/templates/index.html`, add after the household include:

```html
    {% include "editor_jobs.html" %}
```

- [ ] **Step 9: Run the jobs tests + web suite**

Run: `uv run pytest packages/web/tests/test_jobs_editor.py packages/web/tests/test_app.py -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/sections.py packages/web/web/forms.py packages/web/web/app.py packages/web/web/templates/editor_jobs.html packages/web/web/templates/_boundary.html packages/web/web/templates/index.html packages/web/tests/test_jobs_editor.py
git commit -m "feat(web): add jobs editor with sabbaticals and CalSTRS pension preset"
```

---

### Task 6: Social Security section (claim age + XML earnings upload)

Per-person claim-age control plus a multipart XML upload that replaces that person's `earnings_record` via the existing `parse_social_security_statement_xml`. Earnings shown as a read-only summary.

**Files:**
- Modify: `packages/web/web/routes.py` (add `EDITOR_SOCIAL_SECURITY`, `PLAN_SOCIAL_SECURITY`, `PLAN_SS_EARNINGS`)
- Modify: `packages/web/web/sections.py` (add `SOCIAL_SECURITY_TITLE`)
- Modify: `packages/web/web/forms.py` (add `SocialSecurityForm`, claim/file constants)
- Modify: `packages/web/web/app.py` (editor GET, claim-age PATCH, XML upload POST)
- Create: `packages/web/web/templates/editor_social_security.html`
- Modify: `packages/web/web/templates/index.html` (include the partial)
- Test: `packages/web/tests/test_social_security_editor.py`

**Interfaces:**
- Consumes: `domain.social_security.earnings.parse_social_security_statement_xml`; `core.social_security.PersonSocialSecurityConfig` (bounds enforced on `claim_age_months`).
- Produces: `CLAIM_AGE_YEARS="claim_age_years"`, `CLAIM_AGE_MONTHS="claim_age_months"`, `SS_EARNINGS_FILE="statement"`; `SocialSecurityForm(person: PersonId, claim_age_years: int, claim_age_months: int = 0)` with `apply_to(plan)`; routes `EDITOR_SOCIAL_SECURITY="/editor/social-security"`, `PLAN_SOCIAL_SECURITY="/plan/social-security"`, `PLAN_SS_EARNINGS="/plan/social-security/earnings"`.

- [ ] **Step 1: Write failing tests**

Create `packages/web/tests/test_social_security_editor.py`:

```python
from decimal import Decimal

from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from core.social_security import AnnualEarnings
from fastapi.testclient import TestClient
from web.forms import CLAIM_AGE_MONTHS, CLAIM_AGE_YEARS, SS_EARNINGS_FILE
from web.routes import (
    EDITOR_SOCIAL_SECURITY,
    PLAN_SOCIAL_SECURITY,
    PLAN_SS_EARNINGS,
)
from web.sections import SOCIAL_SECURITY_TITLE

def _statement_xml(years: list[int]) -> str:
    rows = "\n".join(
        f'    <osss:Earnings startYear="{year}" endYear="{year}">'
        f"<osss:FicaEarnings>50000</osss:FicaEarnings></osss:Earnings>"
        for year in years
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<osss:OnlineSocialSecurityStatementData '
        'xmlns:osss="http://ssa.gov/osss/schemas/2.0">\n'
        "  <osss:EarningsRecord>\n"
        f"{rows}\n"
        "  </osss:EarningsRecord>\n"
        "</osss:OnlineSocialSecurityStatementData>\n"
    )


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_claim_age_persists_total_months_and_keeps_earnings(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    kept_year = 2019
    seeded.household.person1.social_security.earnings_record = [
        AnnualEarnings(year=kept_year, fica_earnings=Decimal("40000"))
    ]
    repo.save(plan_id, seeded)
    claim_years = 65
    claim_months = 6

    response = client.patch(
        f"{PLAN_SOCIAL_SECURITY}?plan={plan_id}&person=person1",
        data={CLAIM_AGE_YEARS: str(claim_years), CLAIM_AGE_MONTHS: str(claim_months)},
    )

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    config = after.household.person1.social_security
    assert config.claim_age_months == claim_years * 12 + claim_months
    assert config.earnings_record[0].year == kept_year


def test_upload_statement_replaces_earnings_and_triggers_refresh(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_years = [2020, 2023]

    response = client.post(
        f"{PLAN_SS_EARNINGS}?plan={plan_id}&person=person1",
        files={
            SS_EARNINGS_FILE: (
                "statement.xml",
                _statement_xml(expected_years),
                "text/xml",
            )
        },
    )

    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "planUpdated"
    after = repo.get_by_id(plan_id)
    assert after is not None
    years = [e.year for e in after.household.person1.social_security.earnings_record]
    assert years == expected_years


def test_upload_invalid_xml_returns_422_without_changing_earnings(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    original = repo.get_by_id(plan_id)
    assert original is not None
    original_record = original.household.person1.social_security.earnings_record

    response = client.post(
        f"{PLAN_SS_EARNINGS}?plan={plan_id}&person=person1",
        files={SS_EARNINGS_FILE: ("bad.xml", "<not-valid", "text/xml")},
    )

    assert response.status_code == 422
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.household.person1.social_security.earnings_record == original_record


def test_editor_social_security_get_renders_section(
    client: TestClient, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_SOCIAL_SECURITY}?plan={plan_id}")

    assert response.status_code == 200
    assert SOCIAL_SECURITY_TITLE in response.text
```

- [ ] **Step 2: Add scaffolding, then run once to confirm a logical failure**

Add the route constants + section title (Step 3), form constants + a `SocialSecurityForm` stub whose `apply_to` returns the plan unchanged (Step 4), and no-op `editor_social_security`/`patch_social_security`/`upload_ss_earnings` routes that resolve the plan and return a `200` without persisting.

Run: `uv run pytest packages/web/tests/test_social_security_editor.py -v`
Expected: the claim-age and upload tests fail **logically** — `AssertionError` (claim months / earnings unchanged, or missing `HX-Trigger` header) — not `ImportError`. If any failure is structural, complete the scaffolding first, then implement the real logic in Steps 3–7.

- [ ] **Step 3: Add route and section constants**

`packages/web/web/routes.py`:

```python
EDITOR_SOCIAL_SECURITY = "/editor/social-security"
PLAN_SOCIAL_SECURITY = "/plan/social-security"
PLAN_SS_EARNINGS = "/plan/social-security/earnings"
```

`packages/web/web/sections.py`:

```python
SOCIAL_SECURITY_TITLE = "Social Security"
```

- [ ] **Step 4: Add `SocialSecurityForm` and constants to `forms.py`**

```python
CLAIM_AGE_YEARS = "claim_age_years"
CLAIM_AGE_MONTHS = "claim_age_months"
SS_EARNINGS_FILE = "statement"


class SocialSecurityForm(BaseModel):
    """Flat transport DTO. Bounds live on core.social_security."""

    person: PersonId
    claim_age_years: int
    claim_age_months: int = 0

    def apply_to(self, plan: Plan) -> Plan:
        data = plan.household.model_dump()
        if data.get(self.person) is None:
            raise ValueError(
                "Cannot edit Social Security for a partner who is not on the plan"
            )
        data[self.person]["social_security"]["claim_age_months"] = (
            self.claim_age_years * 12 + self.claim_age_months
        )
        household = Household.model_validate(data)
        return plan.model_copy(update={"household": household})
```

- [ ] **Step 5: Add SS routes to `app.py`**

Add imports:

```python
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from domain.social_security.earnings import parse_social_security_statement_xml
from web.forms import AppSettingsForm, HouseholdForm, JobsForm, PortfolioForm, SocialSecurityForm
```

Add a helper to build the SS-partial response (used by upload success/failure) near the other helpers:

```python
def _ss_partial(
    request: Request,
    *,
    plan_id: int,
    plan_model: Plan,
    error: str | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "editor_social_security.html",
        {"plan_id": plan_id, "plan": plan_model, "ss_error": error},
        status_code=status_code,
        headers=headers,
    )
```

In `_register_editor_routes`:

```python
    @web_app.get(routes.EDITOR_SOCIAL_SECURITY, response_class=HTMLResponse)
    def editor_social_security(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return _ss_partial(request, plan_id=plan_id, plan_model=plan_model)
```

In `_register_patch_routes`:

```python
    @web_app.patch(routes.PLAN_SOCIAL_SECURITY)
    def patch_social_security(
        repo: RepoDep,
        claim_age_years: Annotated[int, Form()],
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
        claim_age_months: Annotated[int, Form()] = 0,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        try:
            updated = SocialSecurityForm(
                person=person,  # type: ignore[arg-type]
                claim_age_years=claim_age_years,
                claim_age_months=claim_age_months,
            ).apply_to(plan_model)
        except (ValidationError, ValueError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)

    @web_app.post(routes.PLAN_SS_EARNINGS)
    async def upload_ss_earnings(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
        person: Annotated[str, Query()] = "person1",
        statement: Annotated[UploadFile, File()] = ...,  # noqa: B008
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        raw = (await statement.read()).decode("utf-8", errors="replace")
        try:
            earnings = parse_social_security_statement_xml(raw)
            data = plan_model.household.model_dump()
            if data.get(person) is None:
                raise ValueError("No partner on the plan for this upload")
            data[person]["social_security"]["earnings_record"] = [
                e.model_dump() for e in earnings
            ]
            household = Household.model_validate(data)
            updated = plan_model.model_copy(update={"household": household})
        except (ValidationError, ValueError) as exc:
            return _ss_partial(
                request,
                plan_id=plan_id,
                plan_model=plan_model,
                error=_error_message(exc),
                status_code=422,
            )
        repo.save(plan_id, updated)
        return _ss_partial(
            request,
            plan_id=plan_id,
            plan_model=updated,
            headers={"HX-Trigger": "planUpdated"},
        )
```

`Household` is already imported in `forms.py`; add `from core.models import Household, Plan` to `app.py`'s imports if not present (currently `app.py` imports `AppSettings, Plan` — add `Household`).

- [ ] **Step 6: Create `editor_social_security.html`**

```html
{% set people = [("person1", "You", plan.household.person1)] %}
{% if plan.household.person2 %}{% set people = people + [("person2", "Partner", plan.household.person2)] %}{% endif %}
<section class="editor-section" id="editor-social-security">
  <h2>{{ sections.SOCIAL_SECURITY_TITLE }}</h2>
  {% if ss_error %}<div class="form-error" role="alert">{{ ss_error }}</div>{% endif %}
  {% for pid, plabel, person in people %}
  <div class="ss-person">
    <h3>{{ plabel }}</h3>
    <form
      hx-patch="{{ routes.PLAN_SOCIAL_SECURITY }}?plan={{ plan_id }}&person={{ pid }}"
      hx-trigger="input changed delay:750ms"
      hx-swap="none"
    >
      <label>Claim age (years)
        <input type="number" name="{{ forms.CLAIM_AGE_YEARS }}" value="{{ person.social_security.claim_age_months // 12 }}">
      </label>
      <label>+ months
        <input type="number" min="0" max="11" name="{{ forms.CLAIM_AGE_MONTHS }}" value="{{ person.social_security.claim_age_months % 12 }}">
      </label>
    </form>
    <form
      hx-post="{{ routes.PLAN_SS_EARNINGS }}?plan={{ plan_id }}&person={{ pid }}"
      hx-target="#editor-social-security"
      hx-swap="outerHTML"
      hx-encoding="multipart/form-data"
    >
      <label>Upload ss.gov statement XML
        <input type="file" name="{{ forms.SS_EARNINGS_FILE }}" accept=".xml,text/xml,application/xml">
      </label>
      <button type="submit">Import earnings</button>
    </form>
    {% set record = person.social_security.earnings_record %}
    <p class="ss-earnings-summary">
      {% if record %}{{ record | length }} years imported ({{ record[0].year }}–{{ record[-1].year }}){% else %}No earnings imported yet{% endif %}
    </p>
  </div>
  {% endfor %}
</section>
```

- [ ] **Step 7: Include the SS partial in `index.html`**

```html
    {% include "editor_social_security.html" %}
```

- [ ] **Step 8: Run the SS tests + web suite**

Run: `uv run pytest packages/web/tests/test_social_security_editor.py packages/web/tests/test_app.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/sections.py packages/web/web/forms.py packages/web/web/app.py packages/web/web/templates/editor_social_security.html packages/web/web/templates/index.html packages/web/tests/test_social_security_editor.py
git commit -m "feat(web): add Social Security claim-age editor and XML earnings upload"
```

---

### Task 7: Manual income streams section

Editor for `plan.manual_income_streams`: add/edit/remove streams with label, monthly amount, nominal flag, annual growth, and start/end boundaries. Single full-list debounced form.

**Files:**
- Modify: `packages/web/web/routes.py` (add `EDITOR_MANUAL_INCOME`, `PLAN_MANUAL_INCOME`)
- Modify: `packages/web/web/sections.py` (add `MANUAL_INCOME_TITLE`)
- Modify: `packages/web/web/forms.py` (add `ManualIncomeForm`, `_stream_from_row`, `STREAMS_PREFIX`)
- Modify: `packages/web/web/app.py` (editor GET, PATCH)
- Create: `packages/web/web/templates/editor_manual_income.html`
- Modify: `packages/web/web/templates/index.html` (include the partial)
- Test: `packages/web/tests/test_manual_income_editor.py`

**Interfaces:**
- Consumes: `core.streams.TimedStream`; `web.boundaries.*`.
- Produces: `STREAMS_PREFIX="streams"`; `ManualIncomeForm(streams: list[TimedStream])` with `from_form(form, *, today)` and `apply_to(plan)`; routes `EDITOR_MANUAL_INCOME="/editor/manual-income"`, `PLAN_MANUAL_INCOME="/plan/manual-income"`.

- [ ] **Step 1: Write failing tests**

Create `packages/web/tests/test_manual_income_editor.py`:

```python
from decimal import Decimal

from core.repository import PlanRepository
from core.settings_repository import SettingsRepository
from core.streams import TimedStream
from fastapi.testclient import TestClient
from web.routes import EDITOR_MANUAL_INCOME, PLAN_MANUAL_INCOME
from web.sections import MANUAL_INCOME_TITLE


def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id


def test_patch_manual_income_adds_stream(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    expected_label = "Rental"
    expected_amount = "2500"
    data = {
        "streams[0].label": expected_label,
        "streams[0].monthly_amount": expected_amount,
        "streams[0].annual_growth_rate": "0",
        "streams[0].start_kind": "now",
        "streams[0].end_kind": "none",
    }

    response = client.patch(f"{PLAN_MANUAL_INCOME}?plan={plan_id}", data=data)

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    streams = after.manual_income_streams
    assert [s.label for s in streams] == [expected_label]
    assert streams[0].monthly_amount == Decimal(expected_amount)


def test_patch_manual_income_empty_clears_streams(
    client: TestClient, repo: PlanRepository, db_path
) -> None:
    plan_id = _bootstrap_plan(db_path)
    seeded = repo.get_by_id(plan_id)
    assert seeded is not None
    seeded.manual_income_streams = [TimedStream(monthly_amount=Decimal("100"))]
    repo.save(plan_id, seeded)

    response = client.patch(f"{PLAN_MANUAL_INCOME}?plan={plan_id}", data={})

    assert response.status_code == 200
    after = repo.get_by_id(plan_id)
    assert after is not None
    assert after.manual_income_streams == []


def test_editor_manual_income_get_renders_section(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{EDITOR_MANUAL_INCOME}?plan={plan_id}")

    assert response.status_code == 200
    assert MANUAL_INCOME_TITLE in response.text
```

- [ ] **Step 2: Add scaffolding, then run once to confirm a logical failure**

Add the route constants + section title (Step 3), a `ManualIncomeForm` stub whose `apply_to` returns the plan unchanged (Step 4), and no-op `editor_manual_income`/`patch_manual_income` routes that resolve the plan and return a `200` without persisting.

Run: `uv run pytest packages/web/tests/test_manual_income_editor.py -v`
Expected: the persistence tests fail **logically** — `AssertionError` (no stream persisted / streams not cleared) — not `ImportError`. If any failure is structural, complete the scaffolding first, then implement the real logic in Steps 3–6.

- [ ] **Step 3: Add route and section constants**

`packages/web/web/routes.py`:

```python
EDITOR_MANUAL_INCOME = "/editor/manual-income"
PLAN_MANUAL_INCOME = "/plan/manual-income"
```

`packages/web/web/sections.py`:

```python
MANUAL_INCOME_TITLE = "Manual Income"
```

- [ ] **Step 4: Add `ManualIncomeForm` to `forms.py`**

Add `from core.streams import PersonId, TimedStream` (extend the existing `core.streams` import) and:

```python
STREAMS_PREFIX = "streams"


def _stream_from_row(row: list[tuple[str, str]], *, today: date) -> TimedStream:
    return TimedStream.model_validate(
        {
            "label": boundaries.row_scalar(row, "label") or None,
            "monthly_amount": Decimal(boundaries.row_scalar(row, "monthly_amount", "0")),
            "start": boundaries.row_boundary(row, "start", today=today),
            "end": boundaries.row_boundary(row, "end", today=today),
            "is_nominal": boundaries.row_scalar(row, "is_nominal") in _TRUE,
            "annual_growth_rate": Decimal(
                boundaries.row_scalar(row, "annual_growth_rate", "0")
            ),
        }
    )


class ManualIncomeForm:
    def __init__(self, *, streams: list[TimedStream]) -> None:
        self.streams = streams

    @classmethod
    def from_form(cls, form: FormData, *, today: date) -> ManualIncomeForm:
        rows = boundaries.collect_indexed_rows(form, STREAMS_PREFIX)
        return cls(streams=[_stream_from_row(row, today=today) for row in rows])

    def apply_to(self, plan: Plan) -> Plan:
        return plan.model_copy(update={"manual_income_streams": self.streams})
```

- [ ] **Step 5: Add manual-income routes to `app.py`**

Add `ManualIncomeForm` to the `web.forms` import. In `_register_editor_routes`:

```python
    @web_app.get(routes.EDITOR_MANUAL_INCOME, response_class=HTMLResponse)
    def editor_manual_income(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> HTMLResponse:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        return templates.TemplateResponse(
            request,
            "editor_manual_income.html",
            {"plan_id": plan_id, "plan": plan_model},
        )
```

In `_register_patch_routes`:

```python
    @web_app.patch(routes.PLAN_MANUAL_INCOME)
    async def patch_manual_income(
        request: Request,
        repo: RepoDep,
        plan: Annotated[int | None, Query()] = None,
    ) -> Response:
        plan_id, plan_model = require_plan(plan, plan_repo=repo)
        form = await request.form()
        try:
            updated = ManualIncomeForm.from_form(form, today=date.today()).apply_to(
                plan_model
            )
        except (ValidationError, ValueError) as exc:
            return HTMLResponse(_error_message(exc), status_code=422)
        repo.save(plan_id, updated)
        return Response(status_code=200)
```

- [ ] **Step 6: Create `editor_manual_income.html`**

```html
{% import "_boundary.html" as boundary %}
{% set people = [("person1", "You")] %}
{% if plan.household.person2 %}{% set people = people + [("person2", "Partner")] %}{% endif %}

{% macro stream_row(index, stream, choices) %}
<fieldset class="row stream-row">
  <button type="button" data-remove-row>Remove</button>
  <label>Label <input type="text" name="streams[{{ index }}].label" value="{{ (stream.label or '') if stream else '' }}"></label>
  <label>Monthly amount <input type="number" step="0.01" name="streams[{{ index }}].monthly_amount" value="{{ stream.monthly_amount if stream else '0' }}"></label>
  <label><input type="checkbox" name="streams[{{ index }}].is_nominal" value="on"{% if stream and stream.is_nominal %} checked{% endif %}> Nominal (not inflation-adjusted)</label>
  <label>Annual growth <input type="number" step="0.001" name="streams[{{ index }}].annual_growth_rate" value="{{ stream.annual_growth_rate if stream else '0' }}"></label>
  <div class="boundary-field">Start {{ boundary.boundary_control("streams[" ~ index ~ "].start", boundaries.to_form(stream.start) if stream else {"kind": boundaries.KIND_NONE}, choices, allow_now=True, allow_none=True, allow_max_age=True, none_label="Plan start") }}</div>
  <div class="boundary-field">End {{ boundary.boundary_control("streams[" ~ index ~ "].end", boundaries.to_form(stream.end) if stream else {"kind": boundaries.KIND_NONE}, choices, allow_now=True, allow_none=True, allow_max_age=True, none_label="Plan horizon") }}</div>
</fieldset>
{% endmacro %}

<section class="editor-section">
  <h2>{{ sections.MANUAL_INCOME_TITLE }}</h2>
  <form
    hx-patch="{{ routes.PLAN_MANUAL_INCOME }}?plan={{ plan_id }}"
    hx-trigger="input changed delay:750ms, change delay:750ms"
    hx-swap="none"
  >
    <div class="rows" data-prefix="streams">
      {% for stream in plan.manual_income_streams %}{{ stream_row(loop.index0, stream, people) }}{% endfor %}
      <template class="row-template">{{ stream_row(0, none, people) }}</template>
      <button type="button" data-add-row>Add income stream</button>
    </div>
  </form>
</section>
```

- [ ] **Step 7: Include the manual-income partial in `index.html`**

```html
    {% include "editor_manual_income.html" %}
```

- [ ] **Step 8: Run the manual-income tests + web suite**

Run: `uv run pytest packages/web/tests/test_manual_income_editor.py packages/web/tests/test_app.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/sections.py packages/web/web/forms.py packages/web/web/app.py packages/web/web/templates/editor_manual_income.html packages/web/web/templates/index.html packages/web/tests/test_manual_income_editor.py
git commit -m "feat(web): add manual income streams editor"
```

---

### Task 8: Integration polish, styling, and full verification

Ensure boundary parts don't flash before JS runs, confirm all four sections render on the home page, run the full `make`, and update the rebuild index exit criteria.

**Files:**
- Modify: `packages/web/web/static/style.css` (hide `[hidden]` boundary/pension parts pre-JS)
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (tick Phase 4c exit criteria)
- Verify: `.gitignore` already contains `social-security-statement.xml`
- Test: `packages/web/tests/test_app.py` (assert all sections present on home)

- [ ] **Step 1: Write a failing home-page integration test**

Add to `packages/web/tests/test_app.py` (import the new titles at the top):

```python
from web.sections import (
    JOBS_TITLE,
    MANUAL_INCOME_TITLE,
    SOCIAL_SECURITY_TITLE,
)


def test_home_shows_all_income_sections(client: TestClient, db_path) -> None:
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert JOBS_TITLE in response.text
    assert SOCIAL_SECURITY_TITLE in response.text
    assert MANUAL_INCOME_TITLE in response.text
```

- [ ] **Step 2: Run to verify it fails or passes**

Run: `uv run pytest packages/web/tests/test_app.py::test_home_shows_all_income_sections -v`
Expected: PASS if all includes from Tasks 5–7 are present. If it FAILS, the missing `{% include %}` line for that section was not added to `index.html` — add it and re-run.

- [ ] **Step 3: Hide boundary/pension parts before JS runs**

The `hidden` attribute set by `editor_lists.js` handles post-load state, but the `.pension-fields` block has no `hidden` attribute and shows even when the pension checkbox is off. Add CSS to `packages/web/web/static/style.css` and a small JS toggle. First the CSS:

```css
.boundary-part[hidden] {
  display: none;
}

.pension-fields {
  display: none;
}

.job-row:has(input[name$=".pension_enabled"]:checked) .pension-fields {
  display: block;
}
```

The `:has()` selector shows the pension fields only when that row's checkbox is checked — no JS needed. (`:has()` is supported in all current evergreen browsers; this is a local desktop app.)

- [ ] **Step 4: Verify the personal statement stays gitignored**

Run: `git check-ignore social-security-statement.xml`
Expected: prints `social-security-statement.xml` (already ignored). If it prints nothing, add the entry under the "LifeFinances Specific" block in `.gitignore`:

```
# Personal SSA statement downloads (never commit)
social-security-statement.xml
```

- [ ] **Step 5: Run the full quality gate**

Run: `make`
Expected: ruff check + ruff format check + pyright + full pytest all PASS. Fix any lint/type findings in the files touched this phase (do not disable rules). Common items: unused imports, `type: ignore` placement, and `ruff format` normalization of the new templates' companion Python.

- [ ] **Step 6: Tick Phase 4c exit criteria in the rebuild index**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, change each Phase 4c exit-criteria checkbox from `[ ]` to `[x]` (jobs editor, SS editor + XML, manual income, household tax + explicit filing status, `PersonMaxAgeBoundary` + Now stamping, demographic PATCH preserves nested data, pension tooltip → #197, form-DTO decision documented, personal XML gitignored, `make` passes).

- [ ] **Step 7: Commit**

```bash
git add packages/web/web/static/style.css packages/web/tests/test_app.py docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "feat(web): finalize Phase 4c income editor integration and styling"
```

---

## Self-Review (author checklist — completed while writing)

**1. Spec coverage:**

| Spec item | Task |
| --------- | ---- |
| `PersonMaxAgeBoundary` + timeline resolution | Task 1 |
| Household `apply_to` preserves jobs/SS/tax | Task 2 |
| Household tax fields; explicit Single/MFJ filing status | Task 2 |
| Shared boundary parse/`to_form`/list collectors; DTO decision | Task 3 |
| Boundary UI building block (macro) + list add/remove JS | Task 4 |
| Jobs add/edit/remove; sabbaticals; CalSTRS preset + #197 tooltip | Task 5 |
| SS claim age; XML upload → `earnings_record`; read-only summary | Task 6 |
| Manual income streams editor | Task 7 |
| UI/storage boundary mapping (Now stamps calendar; max-age symbolic) | Tasks 3–4 (parse) + 5/7 (controls) |
| Error handling (422 on apply; SS upload re-renders partial) | Tasks 5–7 |
| Personal SSA XML gitignored; synthetic fixture only | Tasks 6, 8 |
| `make` passes | Task 8 |

**2. Placeholder scan:** No `TODO`/`TBD`/"add validation"/"similar to Task N" — every code step carries complete code.

**3. Type/name consistency:** `boundaries.row_boundary`, `collect_indexed_rows`, `sub_rows`, `row_scalar`, `to_form`, and `KIND_*` names are defined in Task 3 and referenced identically in Tasks 4–7. `JobsForm.from_form`/`apply_to`, `SocialSecurityForm.apply_to`, `ManualIncomeForm.from_form`/`apply_to`, and route constants (`PLAN_JOBS`, `PLAN_SOCIAL_SECURITY`, `PLAN_SS_EARNINGS`, `PLAN_MANUAL_INCOME`) are consistent across their definition and use. Field prefixes (`jobs`, `sabbaticals`, `streams`) match between templates (`name="jobs[i].…"`) and collectors (`collect_indexed_rows(form, "jobs")`).

**4. TDD loop compliance (AGENTS.md testing policy §120–126):** No task checklists a structural-failure run. Each task writes its test(s), adds minimal scaffolding (union member without the resolver / stub module / stub macro / no-op routes returning `200` without persisting), then checklists a single run that must show a **logical** failure (`AssertionError`/`TypeError`/`NotImplementedError`) — never an `ImportError`/`TemplateNotFound` — before real logic goes in. Tests bind shared literals once and reference them in both arrange and assert (`age_years`, `age_months`, `expected_years`, row labels/fractions) and pull the CalSTRS table, section titles, and filing-status values from source instead of copying them. The section GET-renders and home-aggregate tests are intentional integration smoke tests, not trivial-wiring tests.

## PR sizing note

Per the spec, prefer one PR. If the diff exceeds rebuild-index guidance (~2000 lines), split at the Task 5/6 boundary: **4c-1** = Tasks 1–5 (core boundary, household, shared helpers/macro, jobs); **4c-2** = Tasks 6–8 (Social Security, manual income, integration). Each split leaves `main` green because every task ends on passing tests.

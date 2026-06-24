# Phase 2c — Domain Social Security Implementation Plan

**Status:** Complete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build deterministic, monthly Social Security domain projections from per-person claim ages, SSA historical FICA earnings, and Phase 2b SS-covered job-income projections.

**Architecture:** Per-person Social Security config lives in `core` because it is persisted on `Plan`; one household-level trust factor lives directly on `Household`. Statutory Social Security tables live in `domain/statutory` as versioned source data, while `domain/social_security` owns XML parsing, earnings indexing/capping, PIA math, monthly claim multipliers, spousal alternatives, and `SocialSecurityProjection`.

**Tech Stack:** Python 3.14, Pydantic v2, `Decimal` money math, stdlib XML parsing, pytest, uv workspace. Spec: `docs/superpowers/specs/2026-06-23-phase-2c-domain-social-security-design.md`.

**Conventions for every task:**

- Follow TDD: write the behavior test, scaffold to a *logical* red (`NotImplementedError`, wrong return, or missing validation), confirm the failure is logical, implement, confirm green.
- Run commands from the repository root: `/Users/chris/Projects/life-finances-workspace/LifeFInances`.
- Single test command: `uv run pytest <path>::<test_name> -v`.
- Package-level test command: `uv run pytest packages/core/tests packages/domain/tests -v`.
- Full verification command: `make`.
- Bind expected values to variables and reference those variables in both arrange and assert when a value appears in both.
- Import constants from production modules in tests instead of copying literals, except where the test intentionally pins a public statutory contract and says so in a comment.
- Commit after each task. The pre-commit hook runs `make`; do not skip it.

---

## File Structure

`packages/core/`

- `core/social_security.py` *(new)* — `AnnualEarnings`, `PersonSocialSecurityConfig`, and Social Security config constants.
- `core/models.py` *(modify)* — add `PersonHousehold.social_security` and `Household.social_security_trust_factor`.
- `core/defaults.py` *(modify)* — default plans inherit the new model defaults.
- `tests/test_social_security.py` *(new)* — core SS config validation and repository round-trip.

`packages/domain/`

- `domain/statutory/__init__.py` *(new)* — exports statutory Social Security table helpers.
- `domain/statutory/social_security.py` *(new)* — source tables, source metadata, and stdlib log-linear extrapolation.
- `domain/social_security/__init__.py` *(new)* — `PersonSocialSecurity`, `SocialSecurityProjection`, `project_social_security()`.
- `domain/social_security/benefits.py` *(new)* — AIME, PIA, claim-age multiplier.
- `domain/social_security/earnings.py` *(new)* — SSA XML parser, future-earnings grouping, capping/indexing pipeline.
- `tests/test_social_security.py` *(new)* — parser, statutory helpers, benefits, projection, and integration tests.
- `OVERVIEW.md` *(modify)* — Social Security port status.

`docs/superpowers/plans/`

- `2026-06-12-rebuild-index.md` *(modify at phase completion)* — mark Phase 2c complete and point active phase to Phase 2d planning.

---

## Task 1: Core Social Security Config

**Files:**

- Create: `packages/core/core/social_security.py`
- Modify: `packages/core/core/models.py`
- Test: `packages/core/tests/test_social_security.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/core/tests/test_social_security.py
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from core.defaults import default_plan
from core.models import Household, PersonHousehold, Plan
from core.repository import PlanRepository
from core.social_security import (
    AnnualEarnings,
    FULL_RETIREMENT_AGE_MONTHS,
    MAX_CLAIM_AGE_MONTHS,
    MIN_CLAIM_AGE_MONTHS,
    PersonSocialSecurityConfig,
)


def test_default_plan_has_social_security_defaults() -> None:
    plan = default_plan()

    assert plan.household.person1.social_security.claim_age_months == (
        FULL_RETIREMENT_AGE_MONTHS
    )
    assert plan.household.person2.social_security.claim_age_months == (
        FULL_RETIREMENT_AGE_MONTHS
    )
    assert plan.household.social_security_trust_factor == Decimal("1")


def test_claim_age_must_be_between_62_and_70() -> None:
    too_early = MIN_CLAIM_AGE_MONTHS - 1
    too_late = MAX_CLAIM_AGE_MONTHS + 1

    with pytest.raises(ValidationError):
        PersonSocialSecurityConfig(claim_age_months=too_early)

    with pytest.raises(ValidationError):
        PersonSocialSecurityConfig(claim_age_months=too_late)


def test_household_trust_factor_must_be_between_zero_and_one() -> None:
    base = default_plan().household
    too_high = Decimal("1.01")

    with pytest.raises(ValidationError):
        Household(
            person1=base.person1,
            person2=base.person2,
            social_security_trust_factor=too_high,
        )


def test_social_security_config_round_trips_through_repository(
    repo: PlanRepository,
) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_claim_age = MIN_CLAIM_AGE_MONTHS
    expected_trust = Decimal("0.76")
    expected_earnings = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200")),
        AnnualEarnings(year=2024, fica_earnings=Decimal("52700")),
    ]

    updated_plan = Plan(
        name=plan.name,
        household=Household(
            person1=PersonHousehold(
                birth_month=plan.household.person1.birth_month,
                birth_year=plan.household.person1.birth_year,
                max_age_years=plan.household.person1.max_age_years,
                jobs=plan.household.person1.jobs,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=expected_claim_age,
                    earnings_record=expected_earnings,
                ),
            ),
            person2=plan.household.person2,
            social_security_trust_factor=expected_trust,
        ),
        portfolio=plan.portfolio,
        manual_income_streams=plan.manual_income_streams,
    )

    repo.save(plan_id, updated_plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.household.person1.social_security.claim_age_months == (
        expected_claim_age
    )
    assert loaded.household.person1.social_security.earnings_record == (
        expected_earnings
    )
    assert loaded.household.social_security_trust_factor == expected_trust
```

- [ ] **Step 2: Scaffold to a logical red**

Create `packages/core/core/social_security.py` with structure but no validation bounds so the bounds tests fail logically:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

MIN_CLAIM_AGE_MONTHS = 62 * 12
FULL_RETIREMENT_AGE_MONTHS = 67 * 12
MAX_CLAIM_AGE_MONTHS = 70 * 12


class AnnualEarnings(BaseModel):
    """One SSA historical annual FICA earnings row."""

    year: int
    fica_earnings: Decimal = Field(ge=0)


class PersonSocialSecurityConfig(BaseModel):
    """Per-person Social Security calculation inputs."""

    claim_age_months: int = FULL_RETIREMENT_AGE_MONTHS
    earnings_record: list[AnnualEarnings] = Field(default_factory=list)
```

Modify `packages/core/core/models.py` imports and models:

```python
from core.social_security import PersonSocialSecurityConfig
```

```python
class PersonHousehold(BaseModel):
    birth_month: int = Field(ge=1, le=12)
    birth_year: int
    max_age_years: int = Field(default=100, ge=1)
    jobs: list[Job] = Field(default_factory=list)
    social_security: PersonSocialSecurityConfig = Field(
        default_factory=PersonSocialSecurityConfig
    )
```

```python
class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold
    social_security_trust_factor: Decimal = Decimal(1)
```

- [ ] **Step 3: Run tests to verify logical failures**

Run: `uv run pytest packages/core/tests/test_social_security.py -v`

Expected: FAIL with `DID NOT RAISE ValidationError` for the claim-age and trust-factor tests. Import errors mean the scaffold is incomplete and must be fixed before implementation.

- [ ] **Step 4: Implement validation bounds**

Replace `PersonSocialSecurityConfig.claim_age_months` in `packages/core/core/social_security.py`:

```python
class PersonSocialSecurityConfig(BaseModel):
    """Per-person Social Security calculation inputs."""

    claim_age_months: int = Field(
        default=FULL_RETIREMENT_AGE_MONTHS,
        ge=MIN_CLAIM_AGE_MONTHS,
        le=MAX_CLAIM_AGE_MONTHS,
    )
    earnings_record: list[AnnualEarnings] = Field(default_factory=list)
```

Replace `Household.social_security_trust_factor` in `packages/core/core/models.py`:

```python
class Household(BaseModel):
    person1: PersonHousehold
    person2: PersonHousehold
    social_security_trust_factor: Decimal = Field(default=Decimal(1), ge=0, le=1)
```

Keep the existing `Household._validate_sabbatical_windows()` validator below these fields.

- [ ] **Step 5: Run tests to verify green**

Run: `uv run pytest packages/core/tests/test_social_security.py packages/core/tests/test_repository.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/core/core/social_security.py packages/core/core/models.py packages/core/tests/test_social_security.py
git commit -m "feat(core): add Social Security plan config"
```

---

## Task 2: Statutory Social Security Tables

**Files:**

- Create: `packages/domain/domain/statutory/__init__.py`
- Create: `packages/domain/domain/statutory/social_security.py`
- Test: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Write the failing tests**

```python
# packages/domain/tests/test_social_security.py
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from domain.statutory.social_security import (
    AWI_INDEX_BY_YEAR,
    CURRENT_BEND_POINTS,
    LAST_REVIEWED_YEAR,
    PIA_RATES,
    SS_MAX_EARNINGS_BY_YEAR,
    STALENESS_GRACE_YEARS,
    is_statutory_data_stale,
    log_linear_extrapolate,
    statutory_value_for_year,
)


def test_statutory_tables_sanity_checks() -> None:
    pinned_taxable_max = Decimal("176100")
    # Contract test: 2025 SSA taxable maximum is intentionally pinned as a sanity check.
    assert statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, 2025) == (
        pinned_taxable_max
    )
    assert all(isinstance(value, Decimal) for _, value in AWI_INDEX_BY_YEAR)
    assert CURRENT_BEND_POINTS[0] < CURRENT_BEND_POINTS[1]
    assert PIA_RATES[0] > PIA_RATES[1]
    assert PIA_RATES[1] > PIA_RATES[2]


def test_statutory_data_is_fresh_within_grace_window() -> None:
    last_fresh_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS - 1

    assert is_statutory_data_stale(last_fresh_year) is False


def test_statutory_data_is_stale_past_grace_window() -> None:
    first_stale_year = LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS

    assert is_statutory_data_stale(first_stale_year) is True


def test_statutory_data_is_not_stale_today() -> None:
    # Intentional real-calendar reminder: when this fails, verify the SSA tables
    # against their source URLs, refresh any changed values, and bump
    # LAST_REVIEWED_YEAR.
    assert is_statutory_data_stale(date.today().year) is False, (
        "Social Security statutory data is overdue for review; "
        "verify against source URLs and bump LAST_REVIEWED_YEAR."
    )


def test_log_linear_extrapolate_extends_two_year_growth() -> None:
    first_year = 2000
    second_year = 2001
    first_value = Decimal("100")
    second_value = Decimal("121")
    requested_year = 2002
    source_rows = [(first_year, first_value), (second_year, second_value)]

    result = log_linear_extrapolate(source_rows, requested_year)

    expected = second_value * (second_value / first_value)
    assert float(result) == pytest.approx(float(expected), rel=0.0001)
```

- [ ] **Step 2: Scaffold to a logical red**

Create empty package files and a helper that raises `NotImplementedError`:

```python
# packages/domain/domain/statutory/__init__.py
"""Versioned statutory tables used by domain calculations."""
```

```python
# packages/domain/domain/statutory/social_security.py
from __future__ import annotations

from decimal import Decimal

LAST_REVIEWED_YEAR = 2026
STALENESS_GRACE_YEARS = 2

SS_MAX_EARNINGS_BY_YEAR: tuple[tuple[int, Decimal], ...] = ()
AWI_INDEX_BY_YEAR: tuple[tuple[int, Decimal], ...] = ()
CURRENT_BEND_POINTS: tuple[Decimal, Decimal] = (Decimal("0"), Decimal("0"))
PIA_RATES: tuple[Decimal, Decimal, Decimal] = (
    Decimal("0"),
    Decimal("0"),
    Decimal("0"),
)


def is_statutory_data_stale(current_year: int) -> bool:
    raise NotImplementedError("staleness check is not implemented yet")


def log_linear_extrapolate(
    rows: tuple[tuple[int, Decimal], ...] | list[tuple[int, Decimal]],
    year: int,
) -> Decimal:
    raise NotImplementedError("log-linear extrapolation is not implemented yet")


def statutory_value_for_year(
    rows: tuple[tuple[int, Decimal], ...],
    year: int,
) -> Decimal:
    raise NotImplementedError("statutory lookup is not implemented yet")
```

- [ ] **Step 3: Run tests to verify logical failures**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_log_linear_extrapolate_extends_two_year_growth packages/domain/tests/test_social_security.py::test_statutory_data_is_stale_past_grace_window -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement tables and helpers**

Replace `packages/domain/domain/statutory/social_security.py`:

```python
from __future__ import annotations

import math
from decimal import Decimal

# Update procedure: once a year, verify each value below against its source URL,
# refresh any that changed, then set LAST_REVIEWED_YEAR to the current year.
# `is_statutory_data_stale` turns this into a soft CI reminder (see below).
LAST_REVIEWED_YEAR = 2026
STALENESS_GRACE_YEARS = 2

# Append-only historical records: each year's row is permanent. Add a new row
# each year; never edit prior rows.
SOURCE_NOTES = {
    "taxable_max": "SSA maximum taxable earnings (append-only history): https://www.ssa.gov/benefits/retirement/planner/maxtax.html",
    "awi_index": "SSA indexing factors (append-only history): https://www.ssa.gov/cgi-bin/awiFactors.cgi",
    "current_bend_points": "SSA bend points (single current set, replaced yearly): https://www.ssa.gov/oact/cola/bendpoints.html",
    "pia_rates": "SSA PIA formula (single current set): https://www.ssa.gov/oact/cola/piaformula.html",
}

SS_MAX_EARNINGS_BY_YEAR: tuple[tuple[int, Decimal], ...] = (
    (2002, Decimal("84900")),
    (2003, Decimal("87000")),
    (2004, Decimal("87900")),
    (2005, Decimal("90000")),
    (2006, Decimal("94200")),
    (2007, Decimal("97500")),
    (2008, Decimal("102000")),
    (2009, Decimal("106800")),
    (2010, Decimal("106800")),
    (2011, Decimal("106800")),
    (2012, Decimal("110100")),
    (2013, Decimal("113700")),
    (2014, Decimal("117000")),
    (2015, Decimal("118500")),
    (2016, Decimal("118500")),
    (2017, Decimal("127200")),
    (2018, Decimal("128400")),
    (2019, Decimal("132900")),
    (2020, Decimal("137700")),
    (2021, Decimal("142800")),
    (2022, Decimal("147000")),
    (2023, Decimal("160200")),
    (2024, Decimal("168600")),
    (2025, Decimal("176100")),
    (2026, Decimal("184500")),
)

AWI_INDEX_BY_YEAR: tuple[tuple[int, Decimal], ...] = (
    (2003, Decimal("1.9557287")),
    (2004, Decimal("1.8688502")),
    (2005, Decimal("1.8028823")),
    (2006, Decimal("1.7236577")),
    (2007, Decimal("1.6488308")),
    (2008, Decimal("1.6117539")),
    (2009, Decimal("1.6364325")),
    (2010, Decimal("1.5986484")),
    (2011, Decimal("1.5500792")),
    (2012, Decimal("1.5031428")),
    (2013, Decimal("1.4841731")),
    (2014, Decimal("1.4332965")),
    (2015, Decimal("1.3851081")),
    (2016, Decimal("1.3696311")),
    (2017, Decimal("1.3239129")),
    (2018, Decimal("1.2776063")),
    (2019, Decimal("1.2314568")),
    (2020, Decimal("1.1976178")),
    (2021, Decimal("1.0998221")),
    (2022, Decimal("1.0443086")),
    (2023, Decimal("1.0000000")),
    (2024, Decimal("1.0000000")),
)

# Single current sets, not historical records: replace these in place each year.
CURRENT_BEND_POINTS: tuple[Decimal, Decimal] = (Decimal("1286"), Decimal("7749"))
PIA_RATES: tuple[Decimal, Decimal, Decimal] = (
    Decimal("0.90"),
    Decimal("0.32"),
    Decimal("0.15"),
)


def is_statutory_data_stale(current_year: int) -> bool:
    """Whether statutory data is overdue for its annual review.

    Soft reminder: stale only once `current_year` reaches
    `LAST_REVIEWED_YEAR + STALENESS_GRACE_YEARS`, so a new calendar year alone
    does not break CI while values are still close enough (real-dollar bend
    points barely move year to year).
    """
    return current_year - LAST_REVIEWED_YEAR >= STALENESS_GRACE_YEARS


def log_linear_extrapolate(
    rows: tuple[tuple[int, Decimal], ...] | list[tuple[int, Decimal]],
    year: int,
) -> Decimal:
    """Estimate `value(year)` from `(year, value)` rows using log-linear fit."""
    if not rows:
        raise ValueError("cannot extrapolate an empty statutory table")
    for source_year, value in rows:
        if source_year == year:
            return value
    x_values = [float(source_year) for source_year, _ in rows]
    y_values = [math.log(float(value)) for _, value in rows]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    numerator = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values, strict=True)
    )
    denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
    if denominator == 0:
        return rows[0][1]
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return Decimal(str(math.exp(intercept + slope * float(year))))


def statutory_value_for_year(
    rows: tuple[tuple[int, Decimal], ...],
    year: int,
) -> Decimal:
    """Return exact statutory value when available, otherwise extrapolate."""
    return log_linear_extrapolate(rows, year)
```

- [ ] **Step 5: Run tests to verify green**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS for the statutory, staleness, and extrapolation tests.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/statutory packages/domain/tests/test_social_security.py
git commit -m "feat(domain): add Social Security statutory tables"
```

---

## Task 3: SSA Statement XML Parser

**Files:**

- Create: `packages/domain/domain/social_security/earnings.py`
- Modify: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Add parser tests**

Append to `packages/domain/tests/test_social_security.py`:

```python
from core.social_security import AnnualEarnings
from domain.social_security.earnings import parse_social_security_statement_xml


def test_parse_social_security_statement_xml_extracts_fica_earnings() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0">
  <osss:EarningsRecord>
    <osss:Earnings startYear="2023" endYear="2023">
      <osss:FicaEarnings>160200</osss:FicaEarnings>
      <osss:MedicareEarnings>219491</osss:MedicareEarnings>
    </osss:Earnings>
    <osss:Earnings startYear="2025" endYear="2025">
      <osss:FicaEarnings>-1</osss:FicaEarnings>
      <osss:MedicareEarnings>-1</osss:MedicareEarnings>
    </osss:Earnings>
  </osss:EarningsRecord>
</osss:OnlineSocialSecurityStatementData>
"""
    expected = [AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))]

    earnings = parse_social_security_statement_xml(xml_text)

    assert earnings == expected


def test_parse_social_security_statement_xml_rejects_multi_year_rows() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0">
  <osss:EarningsRecord>
    <osss:Earnings startYear="2020" endYear="2021">
      <osss:FicaEarnings>1000</osss:FicaEarnings>
    </osss:Earnings>
  </osss:EarningsRecord>
</osss:OnlineSocialSecurityStatementData>
"""

    with pytest.raises(ValueError, match="multi-year"):
        parse_social_security_statement_xml(xml_text)


def test_parse_social_security_statement_xml_rejects_missing_record() -> None:
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<osss:OnlineSocialSecurityStatementData xmlns:osss="http://ssa.gov/osss/schemas/2.0" />
"""

    with pytest.raises(ValueError, match="EarningsRecord"):
        parse_social_security_statement_xml(xml_text)
```

- [ ] **Step 2: Scaffold parser to a logical red**

Create `packages/domain/domain/social_security/earnings.py`:

```python
from __future__ import annotations

from core.social_security import AnnualEarnings


def parse_social_security_statement_xml(xml_text: str) -> list[AnnualEarnings]:
    raise NotImplementedError("SSA XML parsing is not implemented yet")
```

Create `packages/domain/domain/social_security/__init__.py`:

```python
"""Social Security domain projection."""
```

- [ ] **Step 3: Run parser test to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_parse_social_security_statement_xml_extracts_fica_earnings -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement parser**

Replace `packages/domain/domain/social_security/earnings.py`:

```python
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from core.social_security import AnnualEarnings

_NAMESPACE = {"osss": "http://ssa.gov/osss/schemas/2.0"}


def _required_text(element: ElementTree.Element, path: str, year: int) -> str:
    child = element.find(path, _NAMESPACE)
    if child is None or child.text is None:
        raise ValueError(f"missing {path} for SSA earnings year {year}")
    return child.text.strip()


def parse_social_security_statement_xml(xml_text: str) -> list[AnnualEarnings]:
    """Parse SSA statement XML into annual capped FICA earnings."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("invalid SSA statement XML") from exc

    record = root.find("osss:EarningsRecord", _NAMESPACE)
    if record is None:
        raise ValueError("SSA statement XML is missing EarningsRecord")

    earnings: list[AnnualEarnings] = []
    for row in record.findall("osss:Earnings", _NAMESPACE):
        start_year_raw = row.attrib.get("startYear")
        end_year_raw = row.attrib.get("endYear")
        if start_year_raw is None or end_year_raw is None:
            raise ValueError("SSA earnings row is missing startYear or endYear")
        start_year = int(start_year_raw)
        end_year = int(end_year_raw)
        if start_year != end_year:
            raise ValueError(
                f"SSA earnings row is multi-year: {start_year}-{end_year}"
            )
        fica_text = _required_text(row, "osss:FicaEarnings", start_year)
        try:
            fica_earnings = Decimal(fica_text)
        except InvalidOperation as exc:
            raise ValueError(
                f"malformed FicaEarnings for SSA earnings year {start_year}"
            ) from exc
        if fica_earnings == Decimal("-1"):
            continue
        earnings.append(AnnualEarnings(year=start_year, fica_earnings=fica_earnings))
    return earnings
```

- [ ] **Step 5: Run parser against the provided SSA XML demo file**

This is a local smoke check against `social-security-statement (1).xml`. The XML
file contains personal statement data and must remain untracked; do **not** add
it to git.

Run:

```bash
uv run python - <<'PY'
from decimal import Decimal
from pathlib import Path

from domain.social_security.earnings import parse_social_security_statement_xml

xml_path = Path("social-security-statement (1).xml")
earnings = parse_social_security_statement_xml(xml_path.read_text())

assert len(earnings) == 13
assert earnings[0].year == 2012
assert earnings[0].fica_earnings == Decimal("12872")
assert earnings[-1].year == 2024
assert earnings[-1].fica_earnings == Decimal("52700")
assert all(row.year != 2025 for row in earnings)

print(f"Parsed {len(earnings)} SSA FICA earnings rows from {xml_path}")
PY
```

Expected: PASS and output `Parsed 13 SSA FICA earnings rows from social-security-statement (1).xml`.

- [ ] **Step 6: Run parser tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS for statutory and parser tests.

- [ ] **Step 7: Commit**

```bash
git add packages/domain/domain/social_security packages/domain/tests/test_social_security.py
git commit -m "feat(domain): parse SSA statement earnings"
```

---

## Task 4: AIME, PIA, and Claim-Age Benefits

**Files:**

- Create: `packages/domain/domain/social_security/benefits.py`
- Modify: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Add benefit-math tests**

Append to `packages/domain/tests/test_social_security.py`:

```python
from core.social_security import FULL_RETIREMENT_AGE_MONTHS
from domain.social_security.benefits import (
    calculate_aime,
    calculate_pia,
    claim_age_multiplier,
)


def test_calculate_aime_uses_highest_35_years_with_implicit_zeroes() -> None:
    earning_years = 10
    annual_earnings = [Decimal("42000")] * earning_years

    aime = calculate_aime(annual_earnings)

    expected = sum(annual_earnings) / Decimal(35 * 12)
    assert aime == expected


def test_calculate_pia_uses_standard_bend_point_formula() -> None:
    aime = Decimal("9000")

    pia = calculate_pia(aime)

    first_bend, second_bend = CURRENT_BEND_POINTS
    rate1, rate2, rate3 = PIA_RATES
    expected = (
        first_bend * rate1
        + (second_bend - first_bend) * rate2
        + (aime - second_bend) * rate3
    ).quantize(Decimal("0.01"))
    assert pia == expected


def test_claim_age_multiplier_uses_monthly_early_and_delayed_rules() -> None:
    fra_multiplier = Decimal("1")
    earliest_claim_age = 62 * 12
    delayed_claim_age = 70 * 12

    early = claim_age_multiplier(earliest_claim_age)
    fra = claim_age_multiplier(FULL_RETIREMENT_AGE_MONTHS)
    delayed = claim_age_multiplier(delayed_claim_age)

    first_36_months = Decimal(36) * Decimal(5) / Decimal(900)
    remaining_24_months = Decimal(24) * Decimal(5) / Decimal(1200)
    expected_early = Decimal("1") - first_36_months - remaining_24_months
    expected_delayed = Decimal("1") + Decimal(36) * Decimal(2) / Decimal(300)
    assert early == expected_early
    assert fra == fra_multiplier
    assert delayed == expected_delayed
```

- [ ] **Step 2: Scaffold to a logical red**

Create `packages/domain/domain/social_security/benefits.py`:

```python
from __future__ import annotations

from decimal import Decimal


def calculate_aime(indexed_annual_earnings: list[Decimal]) -> Decimal:
    raise NotImplementedError("AIME calculation is not implemented yet")


def calculate_pia(aime: Decimal) -> Decimal:
    raise NotImplementedError("PIA calculation is not implemented yet")


def claim_age_multiplier(claim_age_months: int) -> Decimal:
    raise NotImplementedError("claim-age multiplier is not implemented yet")
```

- [ ] **Step 3: Run benefit test to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_calculate_aime_uses_highest_35_years_with_implicit_zeroes -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement benefits**

Replace `packages/domain/domain/social_security/benefits.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.social_security import FULL_RETIREMENT_AGE_MONTHS
from domain.statutory.social_security import CURRENT_BEND_POINTS, PIA_RATES

_CENTS = Decimal("0.01")


def calculate_aime(indexed_annual_earnings: list[Decimal]) -> Decimal:
    """Average indexed monthly earnings from highest 35 annual earnings years."""
    top_years = sorted(indexed_annual_earnings, reverse=True)[:35]
    if len(top_years) < 35:
        top_years = [*top_years, *([Decimal("0")] * (35 - len(top_years)))]
    return sum(top_years) / Decimal(35 * 12)


def calculate_pia(aime: Decimal) -> Decimal:
    """Primary Insurance Amount using the standard 90/32/15 formula."""
    first_bend, second_bend = CURRENT_BEND_POINTS
    rate1, rate2, rate3 = PIA_RATES
    first_slice = min(aime, first_bend)
    second_slice = min(max(aime - first_bend, Decimal("0")), second_bend - first_bend)
    third_slice = max(aime - second_bend, Decimal("0"))
    return (
        first_slice * rate1 + second_slice * rate2 + third_slice * rate3
    ).quantize(_CENTS)


def claim_age_multiplier(claim_age_months: int) -> Decimal:
    """Monthly early/delayed retirement multiplier relative to FRA 67."""
    if claim_age_months < FULL_RETIREMENT_AGE_MONTHS:
        months_early = FULL_RETIREMENT_AGE_MONTHS - claim_age_months
        first_36 = min(months_early, 36)
        additional = max(months_early - 36, 0)
        reduction = (
            Decimal(first_36) * Decimal(5) / Decimal(900)
            + Decimal(additional) * Decimal(5) / Decimal(1200)
        )
        return Decimal("1") - reduction
    months_delayed = claim_age_months - FULL_RETIREMENT_AGE_MONTHS
    return Decimal("1") + Decimal(months_delayed) * Decimal(2) / Decimal(300)
```

- [ ] **Step 5: Run benefit tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS for statutory, parser, and benefit tests.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/social_security/benefits.py packages/domain/tests/test_social_security.py
git commit -m "feat(domain): calculate Social Security benefits"
```

---

## Task 5: Real-Aware Earnings Pipeline

**Files:**

- Modify: `packages/domain/domain/social_security/earnings.py`
- Modify: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Add earnings-pipeline tests**

Append to `packages/domain/tests/test_social_security.py`:

```python
from datetime import date

from core.defaults import default_plan
from core.timeline import Timeline
from domain.social_security.earnings import (
    group_monthly_earnings_by_year,
    indexed_annual_earnings,
)


def test_group_monthly_earnings_by_year_uses_timeline_calendar_months() -> None:
    plan = default_plan()
    timeline = Timeline(plan, today=date(2026, 11, 1))
    year1_month11 = Decimal("100")
    year1_month12 = Decimal("200")
    year2_month1 = Decimal("300")
    monthly = [year1_month11, year1_month12, year2_month1]

    grouped = group_monthly_earnings_by_year(monthly, timeline)

    assert grouped == {2026: year1_month11 + year1_month12, 2027: year2_month1}


def test_indexed_annual_earnings_indexes_history_but_not_future_real_income() -> None:
    historical_year = 2023
    historical_earning = Decimal("1000")
    future_year = 2026
    historical = [AnnualEarnings(year=historical_year, fica_earnings=historical_earning)]
    future = {future_year: Decimal("2000")}

    earnings = indexed_annual_earnings(
        historical_earnings=historical,
        future_real_earnings_by_year=future,
        today_year=2026,
    )

    historical_index = statutory_value_for_year(AWI_INDEX_BY_YEAR, historical_year)
    expected_history = historical_earning * historical_index
    assert expected_history in earnings
    assert future[future_year] in earnings
```

- [ ] **Step 2: Scaffold to a logical red**

Append stubs to `packages/domain/domain/social_security/earnings.py`:

```python
from core.timeline import Timeline


def group_monthly_earnings_by_year(
    monthly_earnings: list[Decimal],
    timeline: Timeline,
) -> dict[int, Decimal]:
    raise NotImplementedError("future earnings grouping is not implemented yet")


def indexed_annual_earnings(
    *,
    historical_earnings: list[AnnualEarnings],
    future_real_earnings_by_year: dict[int, Decimal],
    today_year: int,
) -> list[Decimal]:
    raise NotImplementedError("earnings indexing is not implemented yet")
```

- [ ] **Step 3: Run grouping test to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_group_monthly_earnings_by_year_uses_timeline_calendar_months -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement grouping and real-aware indexing**

Add imports to `packages/domain/domain/social_security/earnings.py`:

```python
from domain.statutory.social_security import (
    AWI_INDEX_BY_YEAR,
    SS_MAX_EARNINGS_BY_YEAR,
    statutory_value_for_year,
)
```

Replace the stubs:

```python
def group_monthly_earnings_by_year(
    monthly_earnings: list[Decimal],
    timeline: Timeline,
) -> dict[int, Decimal]:
    """Group monthly real earnings by calendar year.

    Index 0 is the current calendar month. Partial first and final years include
    only months present in the simulation horizon.
    """
    grouped: dict[int, Decimal] = {}
    for month_index, earnings in enumerate(monthly_earnings):
        boundary = timeline.month_boundary(month_index)
        grouped[boundary.year] = grouped.get(boundary.year, Decimal("0")) + earnings
    return grouped


def _indexed_taxable_max(year: int) -> Decimal:
    nominal_max = statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, year)
    index = statutory_value_for_year(AWI_INDEX_BY_YEAR, year)
    return nominal_max * index


def indexed_annual_earnings(
    *,
    historical_earnings: list[AnnualEarnings],
    future_real_earnings_by_year: dict[int, Decimal],
    today_year: int,
) -> list[Decimal]:
    """Return annual earnings in today's-dollar basis for AIME.

    Historical earnings are nominal and indexed. Future job-income projections
    are already real dollars, so they are capped in the calculation basis but
    not indexed again.
    """
    values: list[Decimal] = []
    for row in historical_earnings:
        capped_nominal = min(
            row.fica_earnings,
            statutory_value_for_year(SS_MAX_EARNINGS_BY_YEAR, row.year),
        )
        index = statutory_value_for_year(AWI_INDEX_BY_YEAR, row.year)
        values.append(capped_nominal * index)
    for year, earnings in future_real_earnings_by_year.items():
        if year < today_year:
            continue
        values.append(min(earnings, _indexed_taxable_max(year)))
    return values
```

- [ ] **Step 5: Run earnings tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS for statutory, parser, benefits, and earnings tests.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/social_security/earnings.py packages/domain/tests/test_social_security.py
git commit -m "feat(domain): build Social Security earnings pipeline"
```

---

## Task 6: Social Security Projection and Own Benefits

**Files:**

- Modify: `packages/domain/domain/social_security/__init__.py`
- Modify: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Add projection tests for own benefits and shape**

Append to `packages/domain/tests/test_social_security.py`:

```python
from core.models import Household, PersonHousehold, Plan, Portfolio
from core.social_security import PersonSocialSecurityConfig
from domain.job_income import JobIncomeProjection, PersonJobIncome
from domain.social_security import project_social_security


def _zero_job_income(horizon: int) -> JobIncomeProjection:
    zeroes = [Decimal("0.00")] * horizon
    person = PersonJobIncome(gross=zeroes, ss_covered_gross=zeroes, tax_deferred=zeroes)
    return JobIncomeProjection(
        person1=person,
        person2=person,
        total_gross=zeroes,
        total_ss_covered_gross=zeroes,
        total_tax_deferred=zeroes,
    )


def _ss_plan(
    *,
    person1_claim_age_months: int = FULL_RETIREMENT_AGE_MONTHS,
    person2_claim_age_months: int = FULL_RETIREMENT_AGE_MONTHS,
    trust_factor: Decimal = Decimal("1"),
) -> Plan:
    return Plan(
        name="SS Test Plan",
        household=Household(
            person1=PersonHousehold(
                birth_month=1,
                birth_year=1960,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=person1_claim_age_months,
                    earnings_record=[
                        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
                    ],
                ),
            ),
            person2=PersonHousehold(
                birth_month=1,
                birth_year=1962,
                social_security=PersonSocialSecurityConfig(
                    claim_age_months=person2_claim_age_months,
                ),
            ),
            social_security_trust_factor=trust_factor,
        ),
        portfolio=Portfolio(current_savings_balance=Decimal("0")),
    )


def test_project_social_security_returns_horizon_length_series() -> None:
    plan = _ss_plan()
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)

    projection = project_social_security(plan, timeline, job_income)

    assert len(projection.person1.max_benefit) == timeline.horizon_months
    assert len(projection.person2.max_benefit) == timeline.horizon_months
    assert len(projection.total) == timeline.horizon_months


def test_project_social_security_starts_own_benefit_at_claim_month() -> None:
    claim_age = 67 * 12
    plan = _ss_plan(person1_claim_age_months=claim_age)
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)
    claim_index = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age)
    )

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person1.own_benefit[claim_index - 1] == Decimal("0.00")
    assert projection.person1.own_benefit[claim_index] > Decimal("0.00")
```

Add import near existing stream imports:

```python
from core.streams import PersonAgeBoundary, PersonId
```

- [ ] **Step 2: Scaffold projection to a logical red**

Replace `packages/domain/domain/social_security/__init__.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.models import Plan
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection
from pydantic import BaseModel, computed_field


class PersonSocialSecurity(BaseModel):
    own_benefit: list[Decimal]
    spousal_alternative: list[Decimal]
    max_benefit: list[Decimal]

    @computed_field
    @property
    def spousal_top_up(self) -> list[Decimal]:
        return [
            benefit - own
            for own, benefit in zip(self.own_benefit, self.max_benefit, strict=True)
        ]


class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity
    total: list[Decimal]


def project_social_security(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> SocialSecurityProjection:
    raise NotImplementedError("Social Security projection is not implemented yet")
```

- [ ] **Step 3: Run projection test to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_project_social_security_returns_horizon_length_series -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement own-benefit projection with zero spousal alternatives**

Replace `packages/domain/domain/social_security/__init__.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.models import PersonHousehold, Plan
from core.streams import PersonAgeBoundary
from core.timeline import Timeline
from domain.job_income import JobIncomeProjection
from domain.social_security.benefits import (
    calculate_aime,
    calculate_pia,
    claim_age_multiplier,
)
from domain.social_security.earnings import (
    group_monthly_earnings_by_year,
    indexed_annual_earnings,
)
from pydantic import BaseModel, computed_field

_CENTS = Decimal("0.01")


class PersonSocialSecurity(BaseModel):
    """Projected Social Security for one person."""

    own_benefit: list[Decimal]
    spousal_alternative: list[Decimal]
    max_benefit: list[Decimal]

    @computed_field
    @property
    def spousal_top_up(self) -> list[Decimal]:
        return [
            benefit - own
            for own, benefit in zip(self.own_benefit, self.max_benefit, strict=True)
        ]


class SocialSecurityProjection(BaseModel):
    person1: PersonSocialSecurity
    person2: PersonSocialSecurity
    total: list[Decimal]


class _PersonInputs(BaseModel):
    pia: Decimal
    effective_pia: Decimal
    claim_multiplier: Decimal
    claim_start_index: int


def _person_inputs(
    *,
    person: PersonHousehold,
    person_id: PersonId,
    timeline: Timeline,
    future_ss_covered: list[Decimal],
    trust_factor: Decimal,
) -> _PersonInputs:
    future_by_year = group_monthly_earnings_by_year(future_ss_covered, timeline)
    earnings = indexed_annual_earnings(
        historical_earnings=person.social_security.earnings_record,
        future_real_earnings_by_year=future_by_year,
        today_year=timeline.today.year,
    )
    pia = calculate_pia(calculate_aime(earnings)) if earnings else Decimal("0.00")
    effective_pia = (pia * trust_factor).quantize(_CENTS)
    claim_multiplier = claim_age_multiplier(person.social_security.claim_age_months)
    claim_start_index = timeline.index_of(
        PersonAgeBoundary(
            person=person_id, age_months=person.social_security.claim_age_months
        )
    )
    return _PersonInputs(
        pia=pia,
        effective_pia=effective_pia,
        claim_multiplier=claim_multiplier,
        claim_start_index=claim_start_index,
    )


def _own_series(inputs: _PersonInputs, horizon: int) -> list[Decimal]:
    series = [Decimal("0.00")] * horizon
    monthly = (inputs.effective_pia * inputs.claim_multiplier).quantize(_CENTS)
    low = max(inputs.claim_start_index, 0)
    for month_index in range(low, horizon):
        series[month_index] = monthly
    return series


def _person_projection(
    own_benefit: list[Decimal],
    spousal_alternative: list[Decimal],
) -> PersonSocialSecurity:
    max_benefit = [
        max(own, spousal)
        for own, spousal in zip(own_benefit, spousal_alternative, strict=True)
    ]
    return PersonSocialSecurity(
        own_benefit=own_benefit,
        spousal_alternative=spousal_alternative,
        max_benefit=max_benefit,
    )


def project_social_security(
    plan: Plan,
    timeline: Timeline,
    job_income: JobIncomeProjection,
) -> SocialSecurityProjection:
    horizon = timeline.horizon_months
    trust_factor = plan.household.social_security_trust_factor
    person1_inputs = _person_inputs(
        person=plan.household.person1,
        person_id="person1",
        timeline=timeline,
        future_ss_covered=job_income.person1.ss_covered_gross,
        trust_factor=trust_factor,
    )
    person2_inputs = _person_inputs(
        person=plan.household.person2,
        person_id="person2",
        timeline=timeline,
        future_ss_covered=job_income.person2.ss_covered_gross,
        trust_factor=trust_factor,
    )
    person1 = _person_projection(_own_series(person1_inputs, horizon), [Decimal("0.00")] * horizon)
    person2 = _person_projection(_own_series(person2_inputs, horizon), [Decimal("0.00")] * horizon)
    return SocialSecurityProjection(
        person1=person1,
        person2=person2,
        total=[
            a + b
            for a, b in zip(person1.max_benefit, person2.max_benefit, strict=True)
        ],
    )
```

- [ ] **Step 5: Run projection tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS for all current domain Social Security tests.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/social_security/__init__.py packages/domain/tests/test_social_security.py
git commit -m "feat(domain): project Social Security own benefits"
```

---

## Task 7: Spousal Alternatives and Computed Top-Up

**Files:**

- Modify: `packages/domain/domain/social_security/__init__.py`
- Modify: `packages/domain/tests/test_social_security.py`

- [ ] **Step 1: Add spousal tests**

Append to `packages/domain/tests/test_social_security.py`:

```python
def test_spousal_alternative_starts_after_both_people_claim() -> None:
    person1_claim = 67 * 12
    person2_claim = 70 * 12
    plan = _ss_plan(
        person1_claim_age_months=person1_claim,
        person2_claim_age_months=person2_claim,
    )
    plan.household.person2.social_security.earnings_record = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)
    person1_claim_index = timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=person1_claim)
    )
    person2_claim_index = timeline.index_of(
        PersonAgeBoundary(person="person2", age_months=person2_claim)
    )

    projection = project_social_security(plan, timeline, job_income)

    assert projection.person1.spousal_alternative[person1_claim_index] == (
        Decimal("0.00")
    )
    assert projection.person1.spousal_alternative[person2_claim_index] > (
        Decimal("0.00")
    )


def test_spousal_top_up_is_max_benefit_minus_own_benefit() -> None:
    plan = _ss_plan()
    plan.household.person2.social_security.earnings_record = [
        AnnualEarnings(year=2023, fica_earnings=Decimal("160200"))
    ]
    timeline = Timeline(plan, today=date(2026, 1, 1))
    job_income = _zero_job_income(timeline.horizon_months)

    projection = project_social_security(plan, timeline, job_income)

    for own, max_benefit, top_up in zip(
        projection.person1.own_benefit,
        projection.person1.max_benefit,
        projection.person1.spousal_top_up,
        strict=True,
    ):
        assert top_up == max_benefit - own
```

- [ ] **Step 2: Run spousal test to verify logical failure**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_spousal_alternative_starts_after_both_people_claim -v`

Expected: FAIL because `spousal_alternative` stays zero after both claim.

- [ ] **Step 3: Implement spousal alternative series**

Add helper to `packages/domain/domain/social_security/__init__.py` below `_own_series`:

```python
def _spousal_series(
    *,
    receiver_inputs: _PersonInputs,
    spouse_inputs: _PersonInputs,
    horizon: int,
) -> list[Decimal]:
    SPOUSAL_RATIO = Decimal("0.5")
    series = _zeroes(horizon)
    start_index = max(receiver_inputs.claim_start_index, spouse_inputs.claim_start_index)
    monthly = (
        spouse_inputs.effective_pia
        * SPOUSAL_RATIO
        * receiver_inputs.claim_multiplier
    ).quantize(_CENTS)
    low = max(start_index, 0)
    for month_index in range(low, horizon):
        series[month_index] = monthly
    return series
```

Replace the projection creation in `project_social_security()`:

```python
    person1_own = _own_series(person1_inputs, horizon)
    person2_own = _own_series(person2_inputs, horizon)
    person1_spousal = _spousal_series(
        receiver_inputs=person1_inputs,
        spouse_inputs=person2_inputs,
        horizon=horizon,
    )
    person2_spousal = _spousal_series(
        receiver_inputs=person2_inputs,
        spouse_inputs=person1_inputs,
        horizon=horizon,
    )
    person1 = _person_projection(person1_own, person1_spousal)
    person2 = _person_projection(person2_own, person2_spousal)
```

- [ ] **Step 4: Run spousal tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_spousal_alternative_starts_after_both_people_claim packages/domain/tests/test_social_security.py::test_spousal_top_up_is_max_benefit_minus_own_benefit -v`

Expected: PASS.

- [ ] **Step 5: Run full domain SS tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add packages/domain/domain/social_security/__init__.py packages/domain/tests/test_social_security.py
git commit -m "feat(domain): add Social Security spousal alternatives"
```

---

## Task 8: Job-Income Integration and Trust Factor Behavior

**Files:**

- Modify: `packages/domain/tests/test_social_security.py`
- No production file changes expected if Tasks 5-7 are correct.

- [ ] **Step 1: Add integration tests**

Append to `packages/domain/tests/test_social_security.py`:

```python
from core.job import Job, SabbaticalWindow
from core.streams import CalendarMonthBoundary
from domain.job_income import project_job_income


def test_sabbatical_reduced_ss_covered_income_flows_into_projection() -> None:
    annual_income = Decimal("120000")
    claim_age_months=67 * 12
    break_start = CalendarMonthBoundary(year=2026, month=1)
    break_end = CalendarMonthBoundary(year=2026, month=12)
    person_with_break = PersonHousehold(
        birth_month=1,
        birth_year=1990,
        social_security=PersonSocialSecurityConfig(claim_age_months=claim_age_months),
        jobs=[
            Job(
                annual_income=annual_income,
                social_security_eligible=True,
                sabbaticals=[
                    SabbaticalWindow(
                        start=break_start,
                        end=break_end,
                        remaining_fraction=Decimal("0"),
                    )
                ],
            )
        ],
    )
    person_without_break = PersonHousehold(
        birth_month=1,
        birth_year=1990,
        social_security=PersonSocialSecurityConfig(claim_age_months=claim_age_months),
        jobs=[Job(annual_income=annual_income, social_security_eligible=True)],
    )
    base = default_plan()
    plan_with_break = Plan(
        name="SS Sabbatical",
        household=Household(person1=person_with_break, person2=base.household.person2),
        portfolio=base.portfolio,
    )
    plan_without_break = Plan(
        name="SS No Sabbatical",
        household=Household(
            person1=person_without_break, person2=base.household.person2
        ),
        portfolio=base.portfolio,
    )
    timeline_with_break = Timeline(plan_with_break, today=date(2026, 1, 1))
    timeline_without_break = Timeline(plan_without_break, today=date(2026, 1, 1))

    projection_with_break = project_social_security(
        plan_with_break,
        timeline_with_break,
        project_job_income(plan_with_break, timeline_with_break),
    )
    projection_without_break = project_social_security(
        plan_without_break,
        timeline_without_break,
        project_job_income(plan_without_break, timeline_without_break),
    )

    claim_index = timeline_with_break.index_of(
        PersonAgeBoundary(person="person1", age_months=claim_age_months)
    )
    assert projection_with_break.person1.own_benefit[claim_index] < (
        projection_without_break.person1.own_benefit[claim_index]
    )


def test_household_trust_factor_scales_projected_benefits() -> None:
    full_trust = Decimal("1")
    reduced_trust = Decimal("0.75")
    full_plan = _ss_plan(trust_factor=full_trust)
    reduced_plan = _ss_plan(trust_factor=reduced_trust)
    full_timeline = Timeline(full_plan, today=date(2026, 1, 1))
    reduced_timeline = Timeline(reduced_plan, today=date(2026, 1, 1))
    full_projection = project_social_security(
        full_plan, full_timeline, _zero_job_income(full_timeline.horizon_months)
    )
    reduced_projection = project_social_security(
        reduced_plan,
        reduced_timeline,
        _zero_job_income(reduced_timeline.horizon_months),
    )
    claim_index = full_timeline.index_of(
        PersonAgeBoundary(person="person1", age_months=67 * 12)
    )

    assert reduced_projection.person1.max_benefit[claim_index] == (
        full_projection.person1.max_benefit[claim_index] * reduced_trust
    ).quantize(Decimal("0.01"))
```

- [ ] **Step 2: Run integration tests**

Run: `uv run pytest packages/domain/tests/test_social_security.py::test_sabbatical_reduced_ss_covered_income_flows_into_projection packages/domain/tests/test_social_security.py::test_household_trust_factor_scales_projected_benefits -v`

Expected: PASS. If either test fails, inspect whether Task 5 is excluding future earnings before `today_year`, whether Task 6 uses job-income `ss_covered_gross`, and whether Task 6 applies trust to `effective_pia`.

- [ ] **Step 3: Run all Social Security tests**

Run: `uv run pytest packages/core/tests/test_social_security.py packages/domain/tests/test_social_security.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add packages/domain/tests/test_social_security.py
git commit -m "test(domain): cover Social Security job-income integration"
```

---

## Task 9: Documentation, Index, and Final Verification

**Files:**

- Modify: `packages/domain/OVERVIEW.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Modify: `docs/superpowers/plans/2026-06-12-phase-2c-domain-social-security.md`

- [ ] **Step 1: Update domain overview**

In `packages/domain/OVERVIEW.md`, change the Social Security row:

```markdown
| `social_security.py` | `domain/social_security/` | 2c | done |
```

- [ ] **Step 2: Update the rebuild index after implementation completes**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, update the active phase table:

```markdown
| **Current phase** | Phase 2d — plan |
| **Active plan** | *(to write)* `2026-06-12-phase-2d-domain-pension-taxes.md` |
| **Next action** | Write Phase 2d plan before coding |
```

In the Phase 2c exit criteria, change each checkbox to `[x]`.

Add Phase 2c to the completed plans table:

```markdown
| Phase 2c | `2026-06-12-phase-2c-domain-social-security.md` | complete |
```

- [ ] **Step 3: Mark this plan complete**

At the top of this file, add the status line after the title:

```markdown
**Status:** Complete
```

- [ ] **Step 4: Run full verification**

Run: `make`

Expected: PASS for lint, type checking, and tests.

- [ ] **Step 5: Commit**

```bash
git add packages/domain/OVERVIEW.md docs/superpowers/plans/2026-06-12-rebuild-index.md docs/superpowers/plans/2026-06-12-phase-2c-domain-social-security.md
git commit -m "docs(domain): complete Phase 2c Social Security"
```

---

## Self-Review Checklist

**Spec coverage:**

- Config models: Task 1.
- SSA XML parser: Task 3.
- Statutory tables under `domain/statutory`: Task 2.
- Real-aware earnings pipeline: Task 5.
- AIME/PIA standard formula and no WEP path: Task 4.
- Monthly claim-age formula: Task 4.
- Household-level trust factor applied to effective PIA: Tasks 1, 6, and 8.
- Spousal alternatives and computed `spousal_top_up`: Task 7.
- Projection consumes Phase 2b `JobIncomeProjection`: Tasks 6 and 8.
- Sabbatical-reduced SS-covered earnings flow through: Task 8.
- `packages/domain/OVERVIEW.md` and rebuild index updates: Task 9.
- Final `make`: Task 9.

**Type consistency:**

- Core config names: `AnnualEarnings`, `PersonSocialSecurityConfig`.
- Household trust field: `Household.social_security_trust_factor`.
- Domain output names: `PersonSocialSecurity`, `SocialSecurityProjection`.
- Public parser: `parse_social_security_statement_xml(xml_text: str) -> list[AnnualEarnings]`.
- Public projection: `project_social_security(plan: Plan, timeline: Timeline, job_income: JobIncomeProjection) -> SocialSecurityProjection`.

**Implementation order:**

Tasks are ordered so every imported symbol is scaffolded before tests rely on implemented behavior. Each task leaves the repository in a committable state with focused tests.
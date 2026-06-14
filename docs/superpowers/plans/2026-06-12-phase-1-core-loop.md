# Phase 1 — Core Loop (Minimal E2E) Implementation Plan

**status:** complete

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the edit → persist → simulate → refresh loop: `Plan` model + SQLite repository, simulation stub, FastAPI split-pane with Household and Current Savings editor sections, debounced HTMX auto-results.

**Architecture:** [Phase 1 design spec](../specs/2026-06-12-phase-1-core-loop-design.md). Scrollable split-pane shell; **section-scoped** `PATCH` routes bind flat HTML fields to Pydantic form DTOs (no manual merge); `GET /results` runs deterministic stub. Empty DB auto-creates "Default Plan" on first visit.

**Tech Stack:** Python 3.14+, Pydantic, SQLite, FastAPI, Jinja2, HTMX (CDN), uvicorn, pytest, ruff, pyright

**Testing:** Follow root `AGENTS.md` testing policy — test our logic only; no Pydantic validation tests; inject `today` / `ran_at` for time-dependent code; import constants from source. **Do not run pytest to observe structural failures** (`ImportError`, etc.) — add scaffolding until the first run fails on logic (`AssertionError`, `NotImplementedError`), then implement.

**Shared test support:** Blank-schema DB setup lives in `core.db_bootstrap.materialize_blank_db`. Cross-package fixtures (`db_path`, `repo`) live in repo-root `conftest.py`. Package `conftest.py` files add only package-specific fixtures (e.g. web `client`).

---

## File structure (Phase 1 end state)

```
conftest.py                  # shared pytest fixtures: db_path, repo
packages/core/
├── core/
│   ├── models.py
│   ├── defaults.py
│   ├── db_bootstrap.py      # materialize_blank_db() — shared by tests (and init_db later)
│   └── repository.py
└── tests/
    ├── test_db_bootstrap.py
    ├── test_defaults.py
    └── test_repository.py

packages/simulation/
├── simulation/
│   ├── result.py
│   ├── horizon.py
│   └── stub.py
└── tests/
    ├── test_horizon.py
    └── test_stub.py

packages/web/
├── web/
│   ├── app.py
│   ├── dependencies.py
│   ├── routes.py            # path constants — used by app, templates, tests
│   ├── sections.py          # editor section titles — used by templates, tests
│   ├── forms.py             # per-section Pydantic form DTOs + flat field-name constants
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── editor_household.html
│   │   ├── editor_portfolio.html
│   │   ├── results_stub.html
│   │   └── error.html
│   └── static/
│       └── style.css
├── AGENTS.md
└── tests/
    ├── conftest.py
    └── test_app.py
```

---

### Task 1: Core defaults and Plan models

**Files:**

- Create: `packages/core/core/defaults.py`
- Create: `packages/core/core/models.py`
- Modify: `packages/core/core/__init__.py`
- Create: `packages/core/tests/test_defaults.py`

- [ ] **Step 1: Write failing test for `default_plan()` factory**

Create `packages/core/tests/test_defaults.py`:

```python
from decimal import Decimal

from core.defaults import (
    DEFAULT_PERSON1_BIRTH_YEAR,
    DEFAULT_PERSON2_BIRTH_YEAR,
    DEFAULT_PLAN_NAME,
    DEFAULT_SAVINGS_BALANCE,
    default_plan,
)


def test_default_plan_wires_module_constants() -> None:
    plan = default_plan()

    assert plan.name == DEFAULT_PLAN_NAME
    assert plan.household.person1.birth_year == DEFAULT_PERSON1_BIRTH_YEAR
    assert plan.household.person2.birth_year == DEFAULT_PERSON2_BIRTH_YEAR
    assert plan.portfolio.current_savings_balance == DEFAULT_SAVINGS_BALANCE
```

- [ ] **Step 2: Add minimal scaffolding (models + stub factory)**

Create `packages/core/core/models.py`:

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


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
```

Create `packages/core/core/defaults.py`:

```python
from __future__ import annotations

from decimal import Decimal

from core.models import Household, PersonHousehold, Plan, Portfolio

DEFAULT_PLAN_NAME = "Default Plan"
DEFAULT_BIRTH_MONTH = 1
DEFAULT_PERSON1_BIRTH_YEAR = 1970
DEFAULT_PERSON2_BIRTH_YEAR = 1972
DEFAULT_MAX_AGE_YEARS = 100
DEFAULT_SAVINGS_BALANCE = Decimal("500000")


def default_plan() -> Plan:
    raise NotImplementedError
```

Update `packages/core/core/__init__.py` to export `Plan`, `default_plan`.

- [ ] **Step 3: Run test — expect logical failure**

Run: `uv run pytest packages/core/tests/test_defaults.py -v`

Expected: FAIL with `NotImplementedError` (not a structural/import error).

- [ ] **Step 4: Implement `default_plan()`**

```python
def default_plan() -> Plan:
    person = lambda birth_year: PersonHousehold(
        birth_month=DEFAULT_BIRTH_MONTH,
        birth_year=birth_year,
        max_age_years=DEFAULT_MAX_AGE_YEARS,
    )
    return Plan(
        name=DEFAULT_PLAN_NAME,
        household=Household(person1=person(DEFAULT_PERSON1_BIRTH_YEAR), person2=person(DEFAULT_PERSON2_BIRTH_YEAR)),
        portfolio=Portfolio(current_savings_balance=DEFAULT_SAVINGS_BALANCE),
    )
```

- [ ] **Step 5: Run test — expect pass**

Run: `uv run pytest packages/core/tests/test_defaults.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/
git commit -m "feat(core): add Plan model and default plan factory"
```

---

### Task 2: Blank DB bootstrap helper + shared fixtures + PlanRepository

**Files:**
- Create: `packages/core/core/db_bootstrap.py`
- Create: `conftest.py` (repo root)
- Create: `packages/core/core/repository.py`
- Create: `packages/core/tests/test_db_bootstrap.py`
- Create: `packages/core/tests/test_repository.py`

- [ ] **Step 1: Write failing test for `materialize_blank_db`**

Create `packages/core/tests/test_db_bootstrap.py`:

```python
import sqlite3
from pathlib import Path

from core.db_bootstrap import materialize_blank_db


def test_materialize_blank_db_creates_plans_table(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "data.db"

    result = materialize_blank_db(db_path)

    assert result == db_path
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conn.close()
    assert "plans" in tables
```

- [ ] **Step 2: Add minimal scaffolding**

Create `packages/core/core/db_bootstrap.py`:

```python
from __future__ import annotations

from pathlib import Path

from core.paths import default_blank_db_path


def materialize_blank_db(db_path: Path) -> Path:
    raise NotImplementedError
```

- [ ] **Step 3: Run test — expect logical failure**

Run: `uv run pytest packages/core/tests/test_db_bootstrap.py -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement `materialize_blank_db`**

```python
def materialize_blank_db(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(default_blank_db_path().read_bytes())
    return db_path
```

- [ ] **Step 5: Run test — expect pass**

Run: `uv run pytest packages/core/tests/test_db_bootstrap.py -v`

Expected: PASS

- [ ] **Step 6: Add shared pytest fixtures**

Create repo-root `conftest.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest

from core.db_bootstrap import materialize_blank_db
from core.repository import PlanRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return materialize_blank_db(tmp_path / "data.db")


@pytest.fixture
def repo(db_path: Path) -> PlanRepository:
    return PlanRepository(db_path=db_path)
```

Pytest discovers this file for all tests under `packages/*/tests/` (walks up to repo root). Do **not** duplicate these fixtures in package conftest files.

- [ ] **Step 7: Write repository tests and add repository scaffolding**

Create `packages/core/tests/test_repository.py`:

```python
from __future__ import annotations

import sqlite3
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME, DEFAULT_SAVINGS_BALANCE
from core.repository import PlanRepository


def test_get_or_create_default_inserts_when_no_plans(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1
    assert plan.name == DEFAULT_PLAN_NAME
    assert plan.portfolio.current_savings_balance == DEFAULT_SAVINGS_BALANCE


def test_save_and_get_by_id_round_trip_preserves_balance(repo: PlanRepository) -> None:
    plan_id, plan = repo.get_or_create_default()
    expected_balance = Decimal("750000")

    plan.portfolio.current_savings_balance = expected_balance
    repo.save(plan_id, plan)
    loaded = repo.get_by_id(plan_id)

    assert loaded is not None
    assert loaded.portfolio.current_savings_balance == expected_balance


def test_get_or_create_default_returns_existing_without_insert(repo: PlanRepository) -> None:
    first_id, _ = repo.get_or_create_default()
    second_id, _ = repo.get_or_create_default()

    assert second_id == first_id
    conn = sqlite3.connect(repo.db_path)
    try:
        count = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    finally:
        conn.close()
    assert count == 1
```

Create `packages/core/core/repository.py` (stub methods):

```python
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from core.defaults import default_plan
from core.models import Plan
from core.paths import default_db_path


@dataclass
class PlanRepository:
    db_path: Path

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def get_by_id(self, plan_id: int) -> Plan | None:
        raise NotImplementedError

    def save(self, plan_id: int, plan: Plan) -> None:
        raise NotImplementedError

    def get_or_create_default(self) -> tuple[int, Plan]:
        raise NotImplementedError
```

- [ ] **Step 8: Run repository tests — expect logical failure**

Run: `uv run pytest packages/core/tests/test_repository.py -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 9: Implement repository**

```python
    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_by_id(self, plan_id: int) -> Plan | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT data FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        try:
            return Plan.model_validate_json(row[0])
        except ValidationError:
            return None

    def save(self, plan_id: int, plan: Plan) -> None:
        payload = plan.model_dump_json()
        conn = self._connect()
        try:
            conn.execute(
                """
                UPDATE plans
                SET name = ?, data = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (plan.name, payload, plan_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_or_create_default(self) -> tuple[int, Plan]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT id, data FROM plans ORDER BY id LIMIT 1").fetchone()
            if row is not None:
                plan = Plan.model_validate_json(row[1])
                return row[0], plan
            plan = default_plan()
            payload = plan.model_dump_json()
            cur = conn.execute(
                """
                INSERT INTO plans (name, data)
                VALUES (?, ?)
                """,
                (plan.name, payload),
            )
            conn.commit()
            return int(cur.lastrowid), plan
        finally:
            conn.close()
```

Export `PlanRepository` from `core/__init__.py`.

- [ ] **Step 10: Run tests — expect pass**

Run: `uv run pytest packages/core/tests/test_db_bootstrap.py packages/core/tests/test_repository.py -v`

Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add conftest.py packages/core/
git commit -m "feat(core): add blank DB bootstrap, shared fixtures, and PlanRepository"
```

---

### Task 3: Simulation horizon and stub

**Files:**

- Create: `packages/simulation/simulation/result.py`
- Create: `packages/simulation/simulation/horizon.py`
- Create: `packages/simulation/simulation/stub.py`
- Create: `packages/simulation/tests/test_horizon.py`
- Create: `packages/simulation/tests/test_stub.py`
- Modify: `packages/simulation/simulation/__init__.py`

- [ ] **Step 1: Write failing horizon test**

Create `packages/simulation/tests/test_horizon.py`:

```python
from datetime import date

from core.defaults import default_plan
from simulation.horizon import horizon_months, person_end_date


def test_horizon_months_uses_later_person_end_date() -> None:
    fixed_today = date(2026, 6, 13)
    plan = default_plan()
    person1 = plan.household.person1
    person2 = plan.household.person2
    later_end_offset_years = 5
    person2.birth_year = person1.birth_year + later_end_offset_years

    result = horizon_months(plan, today=fixed_today)

    person1_end = person_end_date(person1)
    person2_end = person_end_date(person2)
    later_end = max(person1_end, person2_end)
    expected = (later_end.year - fixed_today.year) * 12 + (later_end.month - fixed_today.month)

    assert person2_end == later_end
    assert result == expected
```

- [ ] **Step 2: Add horizon scaffolding**

Create `packages/simulation/simulation/horizon.py`:

```python
from __future__ import annotations

from datetime import date

from core.models import PersonHousehold, Plan


def person_end_date(person: PersonHousehold) -> date:
    raise NotImplementedError


def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    raise NotImplementedError
```

- [ ] **Step 3: Run test — expect logical failure**

Run: `uv run pytest packages/simulation/tests/test_horizon.py -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 4: Implement horizon helpers**

Add to `packages/simulation/simulation/horizon.py`:

```python
from core.models import PersonHousehold, Plan


def person_end_date(person: PersonHousehold) -> date:
    return date(person.birth_year + person.max_age_years, person.birth_month, 1)


def horizon_months(plan: Plan, *, today: date | None = None) -> int:
    today = today or date.today()
    household = plan.household
    end = max(person_end_date(household.person1), person_end_date(household.person2))
    return (end.year - today.year) * 12 + (end.month - today.month)
```

Export `person_end_date` and `horizon_months` from `simulation/__init__.py`. Tests import `person_end_date` for expected values — one source of truth for end-date math.

- [ ] **Step 5: Run horizon test — expect pass**

Run: `uv run pytest packages/simulation/tests/test_horizon.py -v`

Expected: PASS

- [ ] **Step 6: Write stub tests and add stub scaffolding**

Create `packages/simulation/simulation/result.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

STUB_VERSION = "phase1"


class SimulationResult(BaseModel):
    ran_at: datetime
    horizon_months: int
    echo: dict[str, Any]
    stub_version: str = STUB_VERSION
```

Create `packages/simulation/tests/test_stub.py`:

```python
from datetime import date, datetime
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME, default_plan
from simulation.result import STUB_VERSION
from simulation.stub import run_simulation


def test_run_simulation_echo_reflects_plan_balance() -> None:
    fixed_today = date(2026, 6, 13)
    fixed_ran_at = datetime(2026, 6, 13, 12, 0, 0)
    expected_balance = Decimal("123456")
    plan = default_plan()
    plan.portfolio.current_savings_balance = expected_balance

    result = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)

    assert result.echo["balance"] == expected_balance
    assert result.echo["plan_name"] == DEFAULT_PLAN_NAME
    assert result.stub_version == STUB_VERSION


def test_run_simulation_is_deterministic_for_fixed_clock() -> None:
    fixed_today = date(2026, 6, 13)
    fixed_ran_at = datetime(2026, 6, 13, 12, 0, 0)
    plan = default_plan()

    first = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)
    second = run_simulation(plan, today=fixed_today, ran_at=fixed_ran_at)

    assert first == second
```

Create `packages/simulation/simulation/stub.py`:

```python
from __future__ import annotations

from datetime import date, datetime

from core.models import Plan

from simulation.result import SimulationResult


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
) -> SimulationResult:
    raise NotImplementedError
```

- [ ] **Step 7: Run stub tests — expect logical failure**

Run: `uv run pytest packages/simulation/tests/test_stub.py -v`

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 8: Implement stub**

```python
from core.models import PersonHousehold

from simulation.horizon import horizon_months


def age_years(person: PersonHousehold, *, today: date) -> int:
    birthday_not_yet = (today.month, today.day) < (person.birth_month, 1)
    return today.year - person.birth_year - (1 if birthday_not_yet else 0)


def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
    today: date | None = None,
    ran_at: datetime | None = None,
) -> SimulationResult:
    today = today or date.today()
    ran_at = ran_at or datetime.now()
    _ = percentiles  # reserved for future API
    household = plan.household
    return SimulationResult(
        ran_at=ran_at,
        horizon_months=horizon_months(plan, today=today),
        echo={
            "balance": plan.portfolio.current_savings_balance,
            "person1_age_years": age_years(household.person1, today=today),
            "person2_age_years": age_years(household.person2, today=today),
            "plan_name": plan.name,
        },
    )
```

Export `run_simulation`, `SimulationResult` from `simulation/__init__.py`.

- [ ] **Step 9: Run simulation tests — expect pass**

Run: `uv run pytest packages/simulation/tests/ -v`

Expected: PASS (horizon + stub)

- [ ] **Step 10: Commit**

```bash
git add packages/simulation/
git commit -m "feat(simulation): add horizon helper and phase1 stub"
```

---

### Task 4: Web package dependencies

**Files:**

- Modify: `packages/web/pyproject.toml`

- [ ] **Step 1: Add runtime and test dependencies**

Run from repo root:

```bash
uv add uvicorn python-multipart httpx --package life-finances-web
```

Expected: `packages/web/pyproject.toml` lists `uvicorn`, `python-multipart`, `httpx`.

- [ ] **Step 2: Sync and verify imports**

Run:

```bash
uv sync
uv run python -c "from fastapi.testclient import TestClient; import uvicorn; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add packages/web/pyproject.toml uv.lock pyproject.toml
git commit -m "chore(web): add uvicorn, multipart, and httpx dependencies"
```

---

### Task 5: Web route constants, templates, and static CSS

**Files:**
- Create: `packages/web/web/routes.py`
- Create: `packages/web/web/sections.py`
- Create: `packages/web/web/forms.py`
- Create: `packages/web/web/templates/base.html`
- Create: `packages/web/web/templates/index.html`
- Create: `packages/web/web/templates/editor_household.html`
- Create: `packages/web/web/templates/editor_portfolio.html`
- Create: `packages/web/web/templates/results_stub.html`
- Create: `packages/web/web/templates/error.html`
- Create: `packages/web/web/static/style.css`

- [ ] **Step 1: Define importable route and UI constants**

Create `packages/web/web/routes.py`:

```python
HOME = "/"
EDITOR_HOUSEHOLD = "/editor/household"
EDITOR_PORTFOLIO = "/editor/portfolio"
PLAN_HOUSEHOLD = "/plan/household"
PLAN_PORTFOLIO = "/plan/portfolio"
RESULTS = "/results"
STATIC = "/static"
```

Create `packages/web/web/sections.py`:

```python
HOUSEHOLD_TITLE = "Household"
PORTFOLIO_TITLE = "Current Savings Portfolio"
```

Create `packages/web/web/forms.py` — **one flat Pydantic DTO per editor section**. HTML `name` attributes match DTO field names exactly; FastAPI binds via `Form()` (no dot-notation, no manual merge):

```python
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from core.models import Household, PersonHousehold, Plan

# Field-name constants for templates/tests — must match DTO field names
PERSON1_BIRTH_MONTH = "person1_birth_month"
PERSON1_BIRTH_YEAR = "person1_birth_year"
PERSON1_MAX_AGE_YEARS = "person1_max_age_years"
PERSON2_BIRTH_MONTH = "person2_birth_month"
PERSON2_BIRTH_YEAR = "person2_birth_year"
PERSON2_MAX_AGE_YEARS = "person2_max_age_years"
CURRENT_SAVINGS_BALANCE = "current_savings_balance"


class HouseholdForm(BaseModel):
    person1_birth_month: int = Field(ge=1, le=12)
    person1_birth_year: int
    person1_max_age_years: int = Field(ge=1)
    person2_birth_month: int = Field(ge=1, le=12)
    person2_birth_year: int
    person2_max_age_years: int = Field(ge=1)

    def apply_to(self, plan: Plan) -> Plan:
        household = Household(
            person1=PersonHousehold(
                birth_month=self.person1_birth_month,
                birth_year=self.person1_birth_year,
                max_age_years=self.person1_max_age_years,
            ),
            person2=PersonHousehold(
                birth_month=self.person2_birth_month,
                birth_year=self.person2_birth_year,
                max_age_years=self.person2_max_age_years,
            ),
        )
        return plan.model_copy(update={"household": household})


class PortfolioForm(BaseModel):
    current_savings_balance: Decimal = Field(ge=0)

    def apply_to(self, plan: Plan) -> Plan:
        portfolio = plan.portfolio.model_copy(
            update={"current_savings_balance": self.current_savings_balance}
        )
        return plan.model_copy(update={"portfolio": portfolio})
```

App route decorators, HTMX attributes, templates, and tests **must** import from these modules — no duplicated path/title/field strings.

- [ ] **Step 2: Create base template**

`packages/web/web/templates/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}LifeFinances{% endblock %}</title>
  <link rel="stylesheet" href="{{ routes.STATIC }}/style.css">
  <script src="https://unpkg.com/htmx.org@2.0.4"></script>
</head>
<body>
  {% block body %}{% endblock %}
</body>
</html>
```

- [ ] **Step 3: Create editor partials**

Each section is its **own** `<form>` with `hx-patch` pointed at the matching section route (HTMX sends only that section's fields).

`editor_household.html` — heading `{{ sections.HOUSEHOLD_TITLE }}`; flat `name="{{ forms.PERSON1_BIRTH_MONTH }}"` etc. (expose `forms` module as Jinja global alongside `routes` / `sections`):

- `person1_birth_month`, `person1_birth_year`, `person1_max_age_years`
- `person2_birth_month`, `person2_birth_year`, `person2_max_age_years`
- Labels: "You" / "Partner"
- Form: `hx-patch="{{ routes.PLAN_HOUSEHOLD }}"`

`editor_portfolio.html` — heading `{{ sections.PORTFOLIO_TITLE }}`:

- `name="{{ forms.CURRENT_SAVINGS_BALANCE }}"`
- Form: `hx-patch="{{ routes.PLAN_PORTFOLIO }}"`
- Helper paragraph per design spec (investment accounts only)

- [ ] **Step 4: Create results and error partials**

`results_stub.html` — display `result.ran_at`, `result.horizon_months`, echo fields, stub disclaimer.

`error.html` — single `{{ message }}` for DB missing / validation errors.

- [ ] **Step 5: Create index shell**

`index.html` extends base:

- Header: "LifeFinances" + static "Default Plan"
- Grid: left column stacks both editor partials (each partial brings its own `<form>`)
- Each form: `hx-trigger="change delay:750ms from:input,select" hx-swap="none"`
- Right column: `<div id="results-panel" hx-get="{{ routes.RESULTS }}" hx-trigger="planUpdated from:body" hx-swap="innerHTML">` with initial include of results partial
- Script on `htmx:afterRequest` for successful PATCH to either section form: dispatch `planUpdated` on `document.body`

In `create_app`, register Jinja globals:

```python
from web import forms, routes, sections

templates.env.globals["routes"] = routes
templates.env.globals["sections"] = sections
templates.env.globals["forms"] = forms
```

- [ ] **Step 6: Create minimal CSS**

`style.css`: CSS grid ~40/60 split, system font, section headings, form spacing. Wireframe quality is fine.

- [ ] **Step 7: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/sections.py packages/web/web/forms.py packages/web/web/templates packages/web/web/static
git commit -m "feat(web): add route constants, templates, and static CSS"
```

---

### Task 6: FastAPI app and routes

**Files:**

- Create: `packages/web/web/dependencies.py`
- Create: `packages/web/web/app.py`
- Create: `packages/web/tests/conftest.py` *(web-only fixtures; `db_path` / `repo` come from repo-root `conftest.py`)*
- Create: `packages/web/tests/test_app.py`
- Modify: `packages/web/web/__init__.py`

- [ ] **Step 1: Write web tests, conftest, and app scaffolding**

Create `packages/web/tests/conftest.py`:

```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from web.app import create_app


@pytest.fixture
def client(db_path) -> TestClient:
    app = create_app(db_path=db_path)
    return TestClient(app)
```

Do **not** redefine `db_path` or `repo` here — inherited from repo-root `conftest.py`.

Create `packages/web/tests/test_app.py`:

```python
from decimal import Decimal

from core.defaults import DEFAULT_PLAN_NAME
from web.forms import CURRENT_SAVINGS_BALANCE
from web.routes import HOME, PLAN_PORTFOLIO, RESULTS
from web.sections import HOUSEHOLD_TITLE, PORTFOLIO_TITLE


def test_home_shows_both_editor_sections(client) -> None:
    response = client.get(HOME)

    assert response.status_code == 200
    assert HOUSEHOLD_TITLE in response.text
    assert PORTFOLIO_TITLE in response.text


def test_home_auto_creates_default_plan(client, repo) -> None:
    client.get(HOME)

    plan_id, plan = repo.get_or_create_default()

    assert plan_id == 1  # intentionally pinned: first row in empty DB
    assert plan.name == DEFAULT_PLAN_NAME


def test_patch_portfolio_persists_balance_change(client, repo) -> None:
    client.get(HOME)
    expected_balance = Decimal("750000")

    response = client.patch(
        PLAN_PORTFOLIO,
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    _, plan = repo.get_or_create_default()
    assert plan.portfolio.current_savings_balance == expected_balance


def test_results_echoes_updated_balance(client) -> None:
    expected_balance = Decimal("750000")
    client.get(HOME)
    client.patch(PLAN_PORTFOLIO, data={CURRENT_SAVINGS_BALANCE: str(expected_balance)})

    response = client.get(RESULTS)

    assert response.status_code == 200
    assert str(expected_balance) in response.text
```

Create `packages/web/web/dependencies.py`:

```python
from __future__ import annotations

from pathlib import Path

from core.repository import PlanRepository


def get_repository(db_path: Path) -> PlanRepository:
    return PlanRepository(db_path=db_path)
```

Create `packages/web/web/app.py` (routes not wired yet):

```python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI


def create_app(*, db_path: Path | None = None) -> FastAPI:
    app = FastAPI()
    app.state.db_path = db_path
    return app
```

- [ ] **Step 2: Run tests — expect logical failure**

Run: `uv run pytest packages/web/tests/test_app.py -v`

Expected: FAIL on behavior — e.g. `404`, missing section titles, or failed assertions (not `ImportError` / `ModuleNotFoundError`).

- [ ] **Step 3: Implement full app**

Key implementation notes:

- `create_app(db_path=...)` stores `db_path` on `app.state.db_path`
- Mount `StaticFiles` at `routes.STATIC` from `web/static`
- Configure Jinja2 `Environment` with loader pointing at `web/templates`; register `routes`, `sections`, `form_fields` as globals (see Task 5)
- Route handlers use imported constants:

```python
from web.routes import EDITOR_HOUSEHOLD, EDITOR_PORTFOLIO, HOME, PLAN_HOUSEHOLD, PLAN_PORTFOLIO, RESULTS

@app.get(HOME)
@app.get(EDITOR_HOUSEHOLD)
@app.get(EDITOR_PORTFOLIO)
@app.patch(PLAN_HOUSEHOLD)
@app.patch(PLAN_PORTFOLIO)
@app.get(RESULTS)
```

- `GET HOME`: if DB file missing → render `error.html` with init_db message; else `repo.get_or_create_default()`, render `index.html` with plan + initial stub results
- `PATCH PLAN_HOUSEHOLD` / `PATCH PLAN_PORTFOLIO`: load plan id 1; bind flat `Form()` fields into `HouseholdForm` / `PortfolioForm` (one `Annotated[..., Form()]` param per DTO field, or a small dependency that constructs the DTO); call `form.apply_to(plan)`; save; return 200
- `GET RESULTS`: load plan, run stub, render `results_stub.html`

**No `_merge_form()`.** Pydantic handles validation and typing; each new Phase 4 section adds a form DTO + PATCH route + template form — not merge-table entries.

Example portfolio handler sketch:

```python
@app.patch(PLAN_PORTFOLIO)
def patch_portfolio(
    current_savings_balance: Annotated[Decimal, Form()],
    repo: PlanRepository = Depends(get_repo),
) -> Response:
    plan_id, plan = repo.get_or_create_default()
    updated = PortfolioForm(current_savings_balance=current_savings_balance).apply_to(plan)
    repo.save(plan_id, updated)
    return Response(status_code=200)
```

- [ ] **Step 4: Run web tests — expect pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/web/
git commit -m "feat(web): add split-pane app with HTMX save and stub results"
```

---

### Task 7: Web AGENTS.md and manual smoke check

**Files:**

- Create: `packages/web/AGENTS.md`

- [ ] **Step 1: Write package AGENTS.md**

Document:

- Dev server: `uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000` (note: use `web.app:app` factory — if using `create_app`, expose module-level `app = create_app()` at bottom of `app.py`)
- Template layout conventions
- HTMX debounce pattern (`planUpdated` event)
- Dependency: requires `scripts/init_db.py` first

- [ ] **Step 2: Manual smoke**

Run:

```bash
uv run python scripts/init_db.py
uv run uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` — confirm both sections visible, editing balance updates results panel after debounce.

- [ ] **Step 3: Commit**

```bash
git add packages/web/AGENTS.md
git commit -m "docs(web): add AGENTS.md with dev server instructions"
```

---

### Task 8: Documentation updates

**Files:**

- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Modify: `docs/superpowers/specs/2026-06-12-life-finances-rebuild-design.md`

- [ ] **Step 1: Update rebuild index active phase**

Set active phase table:

```markdown
| **Current phase** | Phase 1 — execute |
| **Active plan** | `[2026-06-12-phase-1-core-loop.md](2026-06-12-phase-1-core-loop.md)` |
| **Next action** | Execute Phase 1 plan; mark complete when exit criteria met |
```

Update Phase 1 summary row: **two editor sections** (Household + Current Savings Portfolio); note base spending is output not input.

- [ ] **Step 2: Add spending-model note to architecture spec §8 Phase 1**

Under Phase 1 bullet, add: "Base spending is simulation output; only extra essential/discretionary spending are user inputs (Phase 4)."

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/
git commit -m "docs: activate Phase 1 plan and clarify spending model"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/chris/Projects/life-finances-workspace/LifeFInances
make
```

Expected: ruff + pyright + pytest all pass.

- [ ] **Step 2: Verify exit criteria**

Checklist from [Phase 1 design spec](../specs/2026-06-12-phase-1-core-loop-design.md) §10 — all items satisfied.

- [ ] **Step 3: Mark plan complete**

Set this file header: `**status:** complete`

Update rebuild index: Phase 1 → complete in Completed plans table; set next action to write Phase 2a plan.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/
git commit -m "docs: mark Phase 1 complete in rebuild index"
```

---

## Plan self-review


| Spec requirement                      | Task                                                  |
| ------------------------------------- | ----------------------------------------------------- |
| Plan model + repository               | Tasks 1–2                                             |
| Shared test DB bootstrap + fixtures   | Task 2 (`materialize_blank_db`, root `conftest.py`)   |
| Auto-create default plan              | Task 2 + Task 6                                       |
| Two editor sections                   | Task 5–6                                              |
| Debounced HTMX save + results refresh | Task 5–6                                              |
| Simulation stub (deterministic)       | Task 3                                                |
| Minimal results placeholder           | Task 5–6                                              |
| pytest core + simulation + web        | Tasks 1–3, 6                                          |
| AGENTS.md testing policy              | Root AGENTS.md (this session)                         |
| No Pydantic-only tests                | No `test_models.py`; factory/repo/stub/app logic only |


No placeholders remain. Time-dependent code uses injected `today` / `ran_at` in tests.
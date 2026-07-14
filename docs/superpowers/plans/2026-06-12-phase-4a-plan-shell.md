# Phase 4a — Plan Shell & Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Named multi-plan CRUD in the header, URL `?plan=` active-plan resolution with a user-marked default for `/`, and an EOD API key field in settings mirroring FRED.

**Architecture:** Active plan is always `?plan={id}`. `/` without `plan` redirects to `AppSettings.default_plan_id`. `PlanRepository` gains list/create/duplicate/rename/delete; web orchestrates default reassignment on delete. Header is a single plan menu (layout B). Full page reload on switch/create/duplicate/delete. Editor PATCH/results thread the same query param via URL + `hx-vals`.

**Tech Stack:** Python 3.14+, uv, FastAPI, Jinja2, HTMX, Pydantic v2, SQLite, pytest.

**Design spec:** `docs/superpowers/specs/2026-07-14-phase-4a-plan-shell-design.md`

**Branch:** `docs/phase-4a-plan-shell` (rename to `feat/phase-4a-plan-shell` when implementation starts if preferred).

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| Modify: `scripts/create_blank_db.py` | Add `default_plan_id` to `app_settings` schema |
| Regenerate: `data/data.db.blank` | Via `uv run python scripts/create_blank_db.py` |
| Modify: `packages/core/core/models.py` | `AppSettings.default_plan_id` |
| Modify: `packages/core/core/settings_repository.py` | Persist/load `default_plan_id`; migrate column on older DBs |
| Modify: `packages/core/tests/test_settings_repository.py` | Round-trip + column ensure |
| Create: `packages/core/core/plan_names.py` | Collision-safe display names (`Untitled Plan`, `… (copy)`) |
| Create: `packages/core/tests/test_plan_names.py` | Name helper behavior |
| Modify: `packages/core/core/repository.py` | `PlanSummary`, `list`, `create`, `duplicate`, `rename`, `delete`, bootstrap |
| Create: `packages/core/tests/test_plan_lifecycle.py` | CRUD + last-plan + default handoff helpers as needed |
| Modify: `packages/web/web/routes.py` | Plan query / management route constants |
| Modify: `packages/web/web/dependencies.py` | `resolve_active_plan`, bootstrap helpers |
| Modify: `packages/web/web/app.py` | Redirect `/`, thread `plan`, plan POST routes |
| Modify: `packages/web/web/forms.py` | EOD key fields + `PLAN_NAME` on forms |
| Modify: `packages/web/web/sections.py` | EOD placeholder / clear-button label constants |
| Modify: `packages/web/web/templates/index.html` | Plan menu header; pass `plan_id` into partials |
| Create: `packages/web/web/templates/plan_menu.html` | Header menu partial |
| Modify: `packages/web/web/templates/editor_*.html` | Carry `plan` on HTMX requests |
| Modify: `packages/web/web/templates/editor_settings.html` | EOD key UI |
| Modify: `packages/web/web/static/style.css` | Minimal plan-menu styles |
| Modify: `packages/web/tests/test_app.py` | Redirects, multi-plan saves, EOD, management actions |
| Modify: `packages/web/AGENTS.md` | Document `?plan=` + header menu |
| Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` | Active plan → 4a; link design/plan |

---

## Testing policy (AGENTS.md §108–139)

Apply on **every** task that adds or changes tests:

1. **Our logic only** — do **not** add tests that only exercise Pydantic field defaults, trivial getters, FastAPI/`Query`/`Form` binding, or HTMX attribute presence. In scope for 4a: settings persistence + column migrate, name-collision helpers, repository CRUD rules (last-plan delete, rename blank reject, duplicate deep-copy), URL default redirect / 404 / orphan default rewrite, PATCH save targeting the queried plan, plan-management redirects + default reassignment, EOD set/clear (same contract as FRED).
2. **Avoid fragile values** — if a literal appears in both arrange/act and assert, bind it once (`expected_name = …`) and reference that variable.
3. **Pull constants from source** — import `DEFAULT_PLAN_NAME`, `UNTITLED_PLAN_BASE`, `HOME`, `PLAN_*` routes, `EOD_API_KEY` / `CLEAR_EOD_API_KEY` / `PLAN_NAME`, and any UI placeholder/button label constants from production modules. Inline a literal only to pin an intentional contract; comment that it is pinned.
4. **TDD flow** — write the failing test → add minimal scaffolding until the failure is **logical** (`AssertionError`, `NotImplementedError`, `ValueError`, `KeyError`, HTTP status assert) → implement → green. **Do not** checklist a separate “structural failure” (`ImportError` / `AttributeError`) pytest run as its own step; fix scaffolding in the same red cycle until the failure is logical.
5. **Shape** — one logical behavior per test; name tests after behavior; keep arrange / act / assert visually distinct.

**Out of scope as standalone tests:** `AppSettings.default_plan_id` defaulting to `None` via Pydantic alone; menu CSS; pure template rendering without a behavior under test.

---

### Task 1: `default_plan_id` on settings + blank schema

**Files:**
- Modify: `scripts/create_blank_db.py`
- Regenerate: `data/data.db.blank`
- Modify: `packages/core/core/models.py`
- Modify: `packages/core/core/settings_repository.py`
- Modify: `packages/core/tests/test_settings_repository.py`

- [ ] **Step 1: Write the failing tests**

Extend `packages/core/tests/test_settings_repository.py`:

```python
def test_settings_repository_round_trips_default_plan_id(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)
    expected_plan_id = 3

    repo.save(AppSettings(default_plan_id=expected_plan_id))
    loaded = repo.get()

    assert loaded.default_plan_id == expected_plan_id


def test_settings_repository_adds_default_plan_id_column_on_older_settings_table(
    tmp_path,
) -> None:
    db_path = tmp_path / "old_settings.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                fred_api_key TEXT,
                eod_api_key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO app_settings (id) VALUES (1);
            """
        )
        conn.commit()
    finally:
        conn.close()

    repo = SettingsRepository(db_path=db_path)
    expected_plan_id = 7
    repo.save(AppSettings(default_plan_id=expected_plan_id))

    assert repo.get().default_plan_id == expected_plan_id
```

Update `test_settings_repository_round_trips_api_keys` to still pass with the new field defaulting to `None`.

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/core/tests/test_settings_repository.py::test_settings_repository_round_trips_default_plan_id packages/core/tests/test_settings_repository.py::test_settings_repository_adds_default_plan_id_column_on_older_settings_table -v`

Expected: **logical** failure (e.g. `TypeError` / `ValidationError` / assert on missing field). If the failure is structural (`ImportError`, `AttributeError`), add minimal scaffolding (`default_plan_id: int | None = None` stub without persistence) and re-run in this same step until logical — do not treat structural as a separate checklist item.

- [ ] **Step 3: Implement**

In `AppSettings`:

```python
class AppSettings(BaseModel):
    fred_api_key: str | None = None
    eod_api_key: str | None = None
    default_plan_id: int | None = None
    # existing blank-key validator unchanged (do not apply to default_plan_id)
```

In `scripts/create_blank_db.py` `app_settings` table, add `default_plan_id INTEGER`.

In `settings_repository.py`:
- Include `default_plan_id` in `APP_SETTINGS_SCHEMA` (for fresh `CREATE TABLE IF NOT EXISTS` — note this does **not** alter existing tables).
- Add `_ensure_columns(conn)` that reads `PRAGMA table_info(app_settings)` and runs `ALTER TABLE app_settings ADD COLUMN default_plan_id INTEGER` when missing.
- Call `_ensure_columns` from `_ensure_settings_row`.
- SELECT/UPDATE include `default_plan_id`.

Regenerate blank DB:

```bash
uv run python scripts/create_blank_db.py
```

- [ ] **Step 4: Re-run tests — expect pass**

Run: `uv run pytest packages/core/tests/test_settings_repository.py -v`

- [ ] **Step 5: Commit**

```bash
git add scripts/create_blank_db.py data/data.db.blank \
  packages/core/core/models.py packages/core/core/settings_repository.py \
  packages/core/tests/test_settings_repository.py
git commit -m "$(cat <<'EOF'
feat(core): persist AppSettings.default_plan_id

Enable a user-marked home plan for Phase 4a URL resolution.
EOF
)"
```

---

### Task 2: Plan name helpers

**Files:**
- Create: `packages/core/core/plan_names.py`
- Create: `packages/core/tests/test_plan_names.py`

- [ ] **Step 1: Write the failing tests**

```python
from core.plan_names import (
    UNTITLED_PLAN_BASE,
    copy_plan_name,
    next_available_name,
    untitled_plan_name,
)


def test_next_available_name_returns_base_when_unused():
    base = UNTITLED_PLAN_BASE

    assert next_available_name(base=base, existing=[]) == base


def test_next_available_name_suffixes_on_collision():
    base = UNTITLED_PLAN_BASE
    existing = [base, f"{base} 2"]

    assert next_available_name(base=base, existing=existing) == f"{base} 3"


def test_copy_plan_name_uses_copy_suffix_then_numbers():
    original = "My Plan"
    first = copy_plan_name(original_name=original, existing=[original])

    assert first == f"{original} (copy)"

    second = copy_plan_name(
        original_name=original,
        existing=[original, first],
    )

    assert second == f"{original} (copy) 2"


def test_untitled_plan_name_delegates_to_next_available():
    existing = [UNTITLED_PLAN_BASE]

    assert untitled_plan_name(existing=existing) == f"{UNTITLED_PLAN_BASE} 2"
```

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/core/tests/test_plan_names.py -v`

Expected: logical failure after scaffolding (`NotImplementedError` / assert). Do not checklist structural failure separately. Scaffold first if needed:

```python
UNTITLED_PLAN_BASE = "Untitled Plan"  # pinned: default New-plan label in design §5

def next_available_name(*, base: str, existing: list[str]) -> str:
    raise NotImplementedError

def untitled_plan_name(*, existing: list[str]) -> str:
    raise NotImplementedError

def copy_plan_name(*, original_name: str, existing: list[str]) -> str:
    raise NotImplementedError
```

- [ ] **Step 3: Implement `plan_names.py`**

```python
from __future__ import annotations

UNTITLED_PLAN_BASE = "Untitled Plan"


def next_available_name(*, base: str, existing: list[str]) -> str:
    taken = set(existing)
    if base not in taken:
        return base
    n = 2
    while f"{base} {n}" in taken:
        n += 1
    return f"{base} {n}"


def untitled_plan_name(*, existing: list[str]) -> str:
    return next_available_name(base=UNTITLED_PLAN_BASE, existing=existing)


def copy_plan_name(*, original_name: str, existing: list[str]) -> str:
    return next_available_name(base=f"{original_name} (copy)", existing=existing)
```

- [ ] **Step 4: Tests pass**

Run: `uv run pytest packages/core/tests/test_plan_names.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/plan_names.py packages/core/tests/test_plan_names.py
git commit -m "$(cat <<'EOF'
feat(core): add collision-safe plan display names

Support Untitled Plan / copy naming for Phase 4a create and duplicate.
EOF
)"
```

---

### Task 3: `PlanRepository` list / create / bootstrap default

**Files:**
- Modify: `packages/core/core/repository.py`
- Create: `packages/core/tests/test_plan_lifecycle.py`
- Modify: `packages/core/tests/test_repository.py` only if bootstrap signature changes require it

- [ ] **Step 1: Write failing tests**

Create `packages/core/tests/test_plan_lifecycle.py`:

```python
from __future__ import annotations

from core.defaults import DEFAULT_PLAN_NAME
from core.models import AppSettings
from core.plan_names import UNTITLED_PLAN_BASE
from core.repository import PlanRepository, PlanSummary
from core.settings_repository import SettingsRepository


def test_list_returns_summaries_ordered_by_id(repo: PlanRepository) -> None:
    first_name = "Alpha"
    second_name = "Beta"
    first_id, first = repo.create(name=first_name)
    second_id, second = repo.create(name=second_name)

    summaries = repo.list()

    assert summaries == [
        PlanSummary(id=first_id, name=first.name),
        PlanSummary(id=second_id, name=second.name),
    ]
    assert first.name == first_name
    assert second.name == second_name


def test_create_inserts_blank_default_plan_with_given_name(
    repo: PlanRepository,
) -> None:
    expected_name = UNTITLED_PLAN_BASE
    plan_id, plan = repo.create(name=expected_name)

    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name
    assert plan.name == expected_name


def test_ensure_bootstrap_creates_plan_and_sets_default_when_empty(
    db_path,
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)

    plan_id, plan = plans.ensure_bootstrap(settings_repo=settings)

    assert plan_id >= 1
    assert settings.get().default_plan_id == plan_id
    assert plans.get_by_id(plan_id) is not None
    assert plan.name == DEFAULT_PLAN_NAME


def test_ensure_bootstrap_is_idempotent_when_plans_exist(db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    second_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    assert second_id == first_id
    assert len(plans.list()) == 1
```

Keep `get_or_create_default` working for existing tests **or** update those tests in this task to call `ensure_bootstrap`. Prefer: implement `ensure_bootstrap` and make `get_or_create_default` call it with a `SettingsRepository(self.db_path)` for backward compatibility during the phase, then migrate call sites in web tasks.

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/core/tests/test_plan_lifecycle.py -v`

Expected: logical failure after scaffolding (`NotImplementedError` / `AttributeError` fixed in-scaffold → assert). No separate structural checklist step.

- [ ] **Step 3: Implement**

In `repository.py`:

```python
@dataclass(frozen=True)
class PlanSummary:
    id: int
    name: str


def list(self) -> list[PlanSummary]:
    ...

def create(self, *, name: str) -> tuple[int, Plan]:
    plan = default_plan().model_copy(update={"name": name})
    # INSERT; return id, plan

def ensure_bootstrap(
    self, *, settings_repo: SettingsRepository
) -> tuple[int, Plan]:
    # If any plan exists:
    #   resolve default_plan_id (if missing/orphan → lowest id, save settings)
    #   return that plan
    # Else:
    #   create(name=DEFAULT_PLAN_NAME), set settings.default_plan_id, return
```

`get_or_create_default` may delegate to `ensure_bootstrap` for compatibility.

- [ ] **Step 4: Tests pass**

Run: `uv run pytest packages/core/tests/test_plan_lifecycle.py packages/core/tests/test_repository.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/repository.py packages/core/tests/test_plan_lifecycle.py
git commit -m "$(cat <<'EOF'
feat(core): add plan list/create and settings-aware bootstrap

Foundation for multi-plan shell resolution and default marking.
EOF
)"
```

---

### Task 4: duplicate / rename / delete

**Files:**
- Modify: `packages/core/core/repository.py`
- Modify: `packages/core/tests/test_plan_lifecycle.py`

- [ ] **Step 1: Write failing tests**

Append to `test_plan_lifecycle.py`:

```python
from decimal import Decimal

import pytest
from core.plan_names import copy_plan_name


def test_duplicate_copies_json_and_assigns_copy_name(repo: PlanRepository) -> None:
    source_name = "Base"
    source_id, source = repo.create(name=source_name)
    expected_balance = Decimal("123456")
    source.portfolio.current_savings_balance = expected_balance
    repo.save(source_id, source)
    expected_copy_name = copy_plan_name(
        original_name=source_name, existing=[source_name]
    )

    new_id, duplicated = repo.duplicate(source_id)

    assert new_id != source_id
    assert duplicated.name == expected_copy_name
    assert duplicated.portfolio.current_savings_balance == expected_balance
    reloaded_source = repo.get_by_id(source_id)
    assert reloaded_source is not None
    assert reloaded_source.portfolio.current_savings_balance == expected_balance


def test_rename_updates_column_and_json(repo: PlanRepository) -> None:
    plan_id, _ = repo.create(name="Old")
    expected_name = "New Name"

    repo.rename(plan_id, name=expected_name)

    loaded = repo.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name
    assert repo.list()[0].name == expected_name


def test_rename_rejects_blank_name(repo: PlanRepository) -> None:
    plan_id, _ = repo.create(name="Keep")
    with pytest.raises(ValueError, match="name"):
        repo.rename(plan_id, name="   ")


def test_delete_removes_plan(repo: PlanRepository) -> None:
    keep_id, _ = repo.create(name="Keep")
    drop_id, _ = repo.create(name="Drop")

    repo.delete(drop_id)

    assert repo.get_by_id(drop_id) is None
    assert [s.id for s in repo.list()] == [keep_id]


def test_delete_refuses_last_plan(repo: PlanRepository) -> None:
    only_id, _ = repo.create(name="Only")
    with pytest.raises(ValueError, match="last"):
        repo.delete(only_id)
    assert len(repo.list()) == 1
```

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/core/tests/test_plan_lifecycle.py -v`

Expected: logical failure (`AttributeError`/`NotImplementedError` after scaffolding → assert). No separate structural checklist step.

- [ ] **Step 3: Implement**

```python
def duplicate(self, plan_id: int) -> tuple[int, Plan]:
    source = self.get_by_id(plan_id)
    if source is None:
        raise KeyError(plan_id)
    existing = [s.name for s in self.list()]
    name = copy_plan_name(original_name=source.name, existing=existing)
    cloned = source.model_copy(deep=True, update={"name": name})
    return self._insert(cloned)  # shared insert helper with create

def rename(self, plan_id: int, *, name: str) -> Plan:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("name must be non-empty")
    plan = self.get_by_id(plan_id)
    if plan is None:
        raise KeyError(plan_id)
    updated = plan.model_copy(update={"name": cleaned})
    self.save(plan_id, updated)
    return updated

def delete(self, plan_id: int) -> None:
    if len(self.list()) <= 1:
        raise ValueError("cannot delete the last plan")
    # DELETE FROM plans WHERE id = ?
```

Default reassignment stays in the **web** layer (Task 6) using `SettingsRepository` after delete — keeps `PlanRepository` free of settings writes except `ensure_bootstrap`.

- [ ] **Step 4: Tests pass**

Run: `uv run pytest packages/core/tests/test_plan_lifecycle.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/core/core/repository.py packages/core/tests/test_plan_lifecycle.py
git commit -m "$(cat <<'EOF'
feat(core): add plan duplicate, rename, and delete

Complete PlanRepository lifecycle for the Phase 4a header menu.
EOF
)"
```

---

### Task 5: Active-plan resolution dependency + home redirect

**Files:**
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/dependencies.py`
- Modify: `packages/web/web/app.py`
- Modify: `packages/web/tests/test_app.py`

- [ ] **Step 1: Write failing tests**

Add to `test_app.py` (use `follow_redirects=False` where asserting redirect):

```python
def test_home_without_plan_redirects_to_default(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    response = client.get(HOME, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == f"{HOME}?plan={plan_id}"


def test_home_with_unknown_plan_returns_404(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.ensure_bootstrap(settings_repo=settings)

    response = client.get(f"{HOME}?plan=999999")

    assert response.status_code == 404


def test_home_with_plan_serves_shell(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, plan = plans.ensure_bootstrap(settings_repo=settings)

    response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert plan.name in response.text
```

Update existing tests that `GET HOME` expecting auto-create: either follow redirects (default) and assert plan exists, or hit `/?plan=1` after bootstrap. Prefer adjusting helpers:

```python
def _bootstrap_plan(db_path) -> int:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    return plan_id
```

For tests that previously relied on `GET HOME` creating the plan, use `_bootstrap_plan` + `/?plan={id}` **or** `client.get(HOME)` with redirects followed.

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/web/tests/test_app.py::test_home_without_plan_redirects_to_default packages/web/tests/test_app.py::test_home_with_unknown_plan_returns_404 -v`

Expected: logical failure (wrong status / missing redirect). Scaffold route stubs if structural; do not checklist structural separately.

- [ ] **Step 3: Implement resolution**

`routes.py` — keep `HOME = "/"`; add helpers later for management paths.

`dependencies.py` (or `app.py` helpers):

```python
def resolve_default_plan_id(
    *, plan_repo: PlanRepository, settings_repo: SettingsRepository
) -> int:
    plan_repo.ensure_bootstrap(settings_repo=settings_repo)
    settings = settings_repo.get()
    summaries = plan_repo.list()
    ids = {s.id for s in summaries}
    default_id = settings.default_plan_id
    if default_id in ids:
        return default_id
    fallback = min(ids)
    settings_repo.save(settings.model_copy(update={"default_plan_id": fallback}))
    return fallback


def require_plan(
    plan_id: int,
    *,
    plan_repo: PlanRepository,
) -> tuple[int, Plan]:
    plan = plan_repo.get_by_id(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan_id, plan
```

Home route:

```python
@web_app.get(HOME)
def home(request: Request, repo: RepoDep, plan: Annotated[int | None, Query()] = None):
    # missing db → error page (unchanged)
    settings_repo = get_settings_repo(request)
    if plan is None:
        default_id = resolve_default_plan_id(plan_repo=repo, settings_repo=settings_repo)
        return RedirectResponse(url=f"{HOME}?plan={default_id}", status_code=302)
    plan_id, plan_model = require_plan(plan, plan_repo=repo)
    settings = settings_repo.get()
    # run_simulation + TemplateResponse with plan_id, plan, settings, summaries=repo.list()
```

- [ ] **Step 4: Fix / update existing home tests; all targeted tests pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/dependencies.py \
  packages/web/web/app.py packages/web/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat(web): resolve active plan from ?plan= with default redirect

Make URL the source of truth for which plan the shell loads.
EOF
)"
```

---

### Task 6: Thread `plan` through editors, PATCH, results

**Files:**
- Modify: `packages/web/web/app.py`
- Modify: `packages/web/web/templates/index.html`
- Modify: `packages/web/web/templates/editor_household.html`
- Modify: `packages/web/web/templates/editor_portfolio.html`
- Modify: `packages/web/web/templates/editor_settings.html` (plan vals only; EOD in Task 8)
- Modify: `packages/web/tests/test_app.py`

- [ ] **Step 1: Write failing multi-plan save test**

```python
def test_patch_portfolio_updates_only_queried_plan(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    a_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    b_id, _ = plans.create(name="Other")
    expected_balance = Decimal("750000")

    response = client.patch(
        f"{PLAN_PORTFOLIO}?plan={b_id}",
        data={CURRENT_SAVINGS_BALANCE: str(expected_balance)},
    )

    assert response.status_code == 200
    plan_a = plans.get_by_id(a_id)
    plan_b = plans.get_by_id(b_id)
    assert plan_a is not None and plan_b is not None
    assert plan_b.portfolio.current_savings_balance == expected_balance
    assert plan_a.portfolio.current_savings_balance != expected_balance
```

Also require `plan` on PATCH/results (missing → 422 from FastAPI or explicit 404 — pick **422** for missing required query via `plan: Annotated[int, Query()]`).

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/web/tests/test_app.py::test_patch_portfolio_updates_only_queried_plan -v`

Expected: assert failure (still saving the wrong plan) — logical, not structural.

- [ ] **Step 3: Implement**

Every plan-scoped route takes `plan: Annotated[int, Query()]` and uses `require_plan`.

Templates — append query on HTMX URLs and/or use:

```html
hx-patch="{{ routes.PLAN_PORTFOLIO }}?plan={{ plan_id }}"
```

Results panel:

```html
hx-get="{{ routes.RESULTS }}?plan={{ plan_id }}"
```

Pass `plan_id` into `index.html` context and into included partials (`{% include ... %}` shares context).

Update existing PATCH tests to include `?plan=` after bootstrap.

- [ ] **Step 4: Full web tests pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/app.py packages/web/web/templates \
  packages/web/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat(web): thread plan query through editors and results

Ensure saves and simulation always target the URL-selected plan.
EOF
)"
```

---

### Task 7: Plan management routes + header menu UI

**Files:**
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/app.py`
- Create: `packages/web/web/templates/plan_menu.html`
- Modify: `packages/web/web/templates/index.html`
- Modify: `packages/web/web/static/style.css`
- Modify: `packages/web/tests/test_app.py`

- [ ] **Step 1: Write failing tests for management actions**

```python
from web.forms import PLAN_NAME
from web.routes import (
    HOME,
    PLAN_CREATE,
    PLAN_DELETE,
    PLAN_DUPLICATE,
    PLAN_RENAME,
    PLAN_SET_DEFAULT,
)


def test_create_plan_redirects_to_new_plan(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plans.ensure_bootstrap(settings_repo=settings)

    response = client.post(PLAN_CREATE, follow_redirects=False)

    assert response.status_code == 302
    new_summaries = plans.list()
    assert len(new_summaries) == 2
    new_id = max(s.id for s in new_summaries)
    assert response.headers["location"] == f"{HOME}?plan={new_id}"


def test_duplicate_plan_redirects_to_copy(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    source_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    response = client.post(
        PLAN_DUPLICATE.format(plan_id=source_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert len(plans.list()) == 2


def test_rename_plan_updates_name(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    plan_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    expected_name = "Renamed"

    response = client.post(
        PLAN_RENAME.format(plan_id=plan_id),
        data={PLAN_NAME: expected_name},
        follow_redirects=False,
    )

    assert response.status_code == 302
    loaded = plans.get_by_id(plan_id)
    assert loaded is not None
    assert loaded.name == expected_name


def test_set_default_updates_settings(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings)
    second_name = "Second"
    second_id, _ = plans.create(name=second_name)

    response = client.post(
        PLAN_SET_DEFAULT.format(plan_id=second_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert settings.get().default_plan_id == second_id
    assert first_id != second_id


def test_delete_plan_reassigns_default_when_needed(
    client: TestClient, db_path
) -> None:
    plans = PlanRepository(db_path=db_path)
    settings_repo = SettingsRepository(db_path=db_path)
    first_id, _ = plans.ensure_bootstrap(settings_repo=settings_repo)
    second_name = "Second"
    second_id, _ = plans.create(name=second_name)
    settings_repo.save(
        settings_repo.get().model_copy(update={"default_plan_id": second_id})
    )

    response = client.post(
        PLAN_DELETE.format(plan_id=second_id),
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert plans.get_by_id(second_id) is None
    assert settings_repo.get().default_plan_id == first_id
    assert response.headers["location"] == f"{HOME}?plan={first_id}"


def test_delete_last_plan_rejected(client: TestClient, db_path) -> None:
    plans = PlanRepository(db_path=db_path)
    settings = SettingsRepository(db_path=db_path)
    only_id, _ = plans.ensure_bootstrap(settings_repo=settings)

    response = client.post(PLAN_DELETE.format(plan_id=only_id))

    assert response.status_code == 400
    assert len(plans.list()) == 1
```

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/web/tests/test_app.py -k "create_plan or duplicate_plan or rename_plan or set_default or delete_plan" -v`

Expected: logical failure (404/assert). Scaffold `PLAN_NAME` + route constants if structural; same step.

- [ ] **Step 3: Implement routes + handlers + menu**

`routes.py`:

```python
PLAN_CREATE = "/plans"
PLAN_DUPLICATE = "/plans/{plan_id}/duplicate"
PLAN_RENAME = "/plans/{plan_id}/rename"
PLAN_DELETE = "/plans/{plan_id}/delete"
PLAN_SET_DEFAULT = "/plans/{plan_id}/set-default"
```

Handlers: POST → mutate → `RedirectResponse(f"{HOME}?plan=…")`.

On delete of default: set `default_plan_id` to `min(remaining ids)` before redirect. On delete of active non-default: redirect to current default.

In `forms.py` add `PLAN_NAME = "name"` and use it in the rename form `name="{{ forms.PLAN_NAME }}"`.

`plan_menu.html` — `<details>` menu:
- links to `/?plan={id}` for each summary
- forms POST to create/duplicate/rename/delete/set-default
- Delete button `disabled` when `summaries|length == 1`
- Set default hidden/disabled when `plan_id == settings.default_plan_id`
- Rename via `<dialog>` or prompt + form

Minimal CSS for dropdown positioning under `.plan-menu`.

Replace hardcoded `Default Plan` span in `index.html` with `{% include "plan_menu.html" %}`.

- [ ] **Step 4: Tests pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/routes.py packages/web/web/app.py \
  packages/web/web/forms.py packages/web/web/templates \
  packages/web/web/static/style.css packages/web/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat(web): add header plan menu and management routes

Create, duplicate, rename, delete, and set-default from the shell header.
EOF
)"
```

---

### Task 8: EOD API key settings UI

**Files:**
- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/sections.py` (EOD placeholder / clear-button label constants)
- Modify: `packages/web/web/templates/editor_settings.html`
- Modify: `packages/web/web/app.py` (`patch_settings` form params)
- Modify: `packages/web/tests/test_app.py`

- [ ] **Step 1: Write failing tests** (mirror FRED; pull UI strings from `sections`)

Add to `sections.py` (used by template + tests):

```python
EOD_API_KEY_SET_PLACEHOLDER = "EOD API key is set"
CLEAR_EOD_API_KEY_LABEL = "Clear stored EOD API key"
```

(Optionally add matching FRED constants in a follow-up; do not rewrite FRED tests in this task unless needed for consistency.)

```python
from web.forms import CLEAR_EOD_API_KEY, EOD_API_KEY
from web.routes import HOME, PLAN_SETTINGS
from web.sections import CLEAR_EOD_API_KEY_LABEL, EOD_API_KEY_SET_PLACEHOLDER


def test_patch_settings_persists_eod_api_key(client: TestClient, db_path) -> None:
    expected_key = "eod-ui-key"
    plan_id = _bootstrap_plan(db_path)

    response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
        data={EOD_API_KEY: expected_key},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().eod_api_key == expected_key


def test_clear_eod_settings_patch_removes_existing_key(
    client: TestClient, db_path
) -> None:
    key_to_clear = "clear-me"
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key=key_to_clear))
    plan_id = _bootstrap_plan(db_path)

    response = client.patch(
        f"{PLAN_SETTINGS}?plan={plan_id}",
        data={CLEAR_EOD_API_KEY: "true"},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().eod_api_key is None


def test_settings_section_never_echoes_stored_eod_key(
    client: TestClient, db_path
) -> None:
    secret_key = "eod-secret-value"
    SettingsRepository(db_path=db_path).save(AppSettings(eod_api_key=secret_key))
    plan_id = _bootstrap_plan(db_path)

    response = client.get(f"{HOME}?plan={plan_id}")

    assert response.status_code == 200
    assert secret_key not in response.text
    assert EOD_API_KEY_SET_PLACEHOLDER in response.text
    assert CLEAR_EOD_API_KEY_LABEL in response.text
```

- [ ] **Step 2: Run once — confirm logical failure**

Run: `uv run pytest packages/web/tests/test_app.py -k eod -v`

Expected: logical failure (key not persisted / placeholder missing). Scaffold form/section constants if structural; same step.

- [ ] **Step 3: Implement**

Extend `AppSettingsForm`:

```python
EOD_API_KEY = "eod_api_key"
CLEAR_EOD_API_KEY = "clear_eod_api_key"

class AppSettingsForm(BaseModel):
    fred_api_key: str | None = None
    clear_fred_api_key: bool = False
    eod_api_key: str | None = None
    clear_eod_api_key: bool = False

    def apply_to(self, settings: AppSettings) -> AppSettings:
        updated = settings
        if self.clear_fred_api_key:
            updated = updated.model_copy(update={"fred_api_key": None})
        elif self.fred_api_key and self.fred_api_key.strip():
            updated = updated.model_copy(
                update={"fred_api_key": self.fred_api_key.strip()}
            )
        if self.clear_eod_api_key:
            updated = updated.model_copy(update={"eod_api_key": None})
        elif self.eod_api_key and self.eod_api_key.strip():
            updated = updated.model_copy(
                update={"eod_api_key": self.eod_api_key.strip()}
            )
        return updated
```

Mirror FRED markup for EOD in `editor_settings.html`, using `{{ sections.EOD_API_KEY_SET_PLACEHOLDER }}` and `{{ sections.CLEAR_EOD_API_KEY_LABEL }}`. Wire `patch_settings` Form params.

Remove the “Deferred to Phase 4” comment on `AppSettingsForm`.

- [ ] **Step 4: Tests pass**

Run: `uv run pytest packages/web/tests/test_app.py -v`

- [ ] **Step 5: Commit**

```bash
git add packages/web/web/forms.py packages/web/web/sections.py \
  packages/web/web/templates/editor_settings.html \
  packages/web/web/app.py packages/web/tests/test_app.py
git commit -m "$(cat <<'EOF'
feat(web): add EOD API key set/clear in settings editor

Mirror the FRED key UX so live S&P refresh is configurable in-app.
EOF
)"
```

---

### Task 9: Docs + index + full `make`

**Files:**
- Modify: `packages/web/AGENTS.md`
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`

- [ ] **Step 1: Update `packages/web/AGENTS.md`**

Document:
- Active plan is `?plan={id}`; `/` redirects to the marked default
- Header plan menu actions
- Forms must include `plan` on PATCH/results HTMX URLs
- Settings hold FRED + EOD keys (never in plan JSON)

- [ ] **Step 2: Update rebuild index**

- Active phase: Phase 4a — in progress / plan written
- Link design spec under Phase 4a
- Point **Active plan** at `2026-06-12-phase-4a-plan-shell.md`
- Leave exit criteria unchecked until implementation finishes

- [ ] **Step 3: Run full verification**

```bash
make
```

Expected: lint + tests pass.

- [ ] **Step 4: Commit**

```bash
git add packages/web/AGENTS.md docs/superpowers/plans/2026-06-12-rebuild-index.md
git commit -m "$(cat <<'EOF'
docs: record Phase 4a plan shell guidance and index status

Document ?plan= resolution for agents and point the rebuild index at the plan.
EOF
)"
```

---

## Spec coverage checklist

| Spec section | Task(s) |
| ------------ | ------- |
| §3 Active plan / redirect / 404 | 5, 6 |
| §4 Repository CRUD + bootstrap | 2, 3, 4 |
| §4 `default_plan_id` schema | 1 |
| §5 Header menu B | 7 |
| §6 EOD settings | 8 |
| §7 Edge cases (last delete, orphan default) | 3, 4, 5, 7 |
| §8 Tests | 1–8 |
| §9 Boundaries | all (core owns data; web owns routes) |
| §10 Exit criteria | verified in Task 9 `make` + manual smoke |

---

## Manual smoke (after Task 9)

```bash
uv run python scripts/init_db.py
uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

1. Open `/` → lands on `/?plan=1` (or default)
2. New plan → new id in URL; menu lists both
3. Duplicate → copy name; edit portfolio on copy only
4. Set default → `/` redirects to that plan
5. Delete non-last → redirects correctly; cannot delete last
6. Set EOD key → placeholder “is set”; clear works; key never echoed

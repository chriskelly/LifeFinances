# Phase 3a+ Networked Market Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add best-effort live FRED `T10YIE` refresh with DB-backed API keys, a gitignored CSV cache, offline vendored fallback, and a minimal in-app settings form.

**Architecture:** `core` owns the persisted singleton `AppSettings` row and repository; `web` owns the local settings form; `simulation.market_data` owns fetch/cache/resolve behavior and receives the API key as an injected value. The network path is opt-in and fail-silent during simulation, while the manual refresh CLI is loud and suitable for diagnostics or maintainer vendored-data updates.

**Tech Stack:** Python 3.14, SQLite, Pydantic, FastAPI + Jinja2 + HTMX, urllib standard library, pytest, ruff, pyright.

---

## Spec And Scope

**Approved spec:** `docs/superpowers/specs/2026-06-28-phase-3a-plus-networked-market-data-design.md`

This phase implements the optional Phase 3a+ scope:

- Official FRED JSON API fetch for `T10YIE`.
- Gitignored cache CSV + sidecar metadata.
- Best-effort `resolve_inflation(..., allow_refresh=True, api_key=...)`.
- Singleton DB-backed `AppSettings` for `fred_api_key` and future `eod_api_key`.
- Minimal masked settings form for entering/clearing the FRED key.
- Manual refresh CLI replacing `scripts/fetch_t10yie_poc.py`.

Out of scope:

- SP500 / EODHD / CAPE presets; Phase 3c will reuse `AppSettings.eod_api_key`.
- Full advanced settings UI; this phase adds only the API-key form.
- Per-run bootstrapped inflation paths.

---

## File Structure

Create:

- `packages/core/core/settings_repository.py` — singleton `AppSettings` persistence and idempotent schema creation for older personal DBs.
- `packages/core/tests/test_settings_repository.py` — settings DB tests.
- `packages/simulation/simulation/market_data/fetch.py` — FRED JSON API request and parser.
- `packages/simulation/simulation/market_data/cache.py` — cache paths, CSV write, sidecar metadata, freshness, read-path selection.
- `packages/simulation/tests/market_data/test_fetch.py` — JSON parsing and URL/request behavior through an injected opener.
- `packages/simulation/tests/market_data/test_cache.py` — cache write/read-path/TTL behavior.
- `packages/web/web/templates/editor_settings.html` — masked local settings form.
- `scripts/refresh_market_data.py` — manual cache refresh and vendored update command.
- `tests/test_refresh_market_data.py` — CLI behavior with fake fetcher and temp DB.

Modify:

- `packages/core/core/models.py` — add `AppSettings`.
- `scripts/create_blank_db.py` — add `app_settings` schema to `SCHEMA`.
- `data/data.db.blank` — regenerate from the updated blank schema.
- `packages/web/web/forms.py` — add settings form constants and `AppSettingsForm`.
- `packages/web/web/routes.py` — add editor/settings and patch routes.
- `packages/web/web/sections.py` — add settings title.
- `packages/web/web/app.py` — add settings repository dependency, editor route, patch route, home context.
- `packages/web/web/templates/index.html` — include settings section and treat settings save like a results-refreshing save.
- `packages/web/tests/test_app.py` — settings form tests.
- `packages/simulation/simulation/market_data/inflation.py` — injected refresh and cache fallback.
- `docs/superpowers/plans/2026-06-12-rebuild-index.md` — mark Phase 3a+ complete at the end of implementation.

Delete:

- `scripts/fetch_t10yie_poc.py` — scratch PoC, replaced by `scripts/refresh_market_data.py`. It is currently untracked in this workspace, so deletion may simply remove an untracked file.

---

## Task 1: AppSettings Model, Schema, And Repository

**Files:**

- Modify: `packages/core/core/models.py`
- Create: `packages/core/core/settings_repository.py`
- Create: `packages/core/tests/test_settings_repository.py`
- Modify: `scripts/create_blank_db.py`
- Modify: `data/data.db.blank` (generated)

### Intent

Add a global, non-plan settings store for local API keys. This task should not touch web or simulation. It leaves the repository able to read/write API keys in a temp DB and auto-create the table for older personal DBs.

- [ ] **Step 1: Write the failing AppSettings model test**

Add `packages/core/tests/test_settings_repository.py`:

```python
from __future__ import annotations

import sqlite3

from core.models import AppSettings
from core.settings_repository import SettingsRepository


def test_app_settings_normalizes_blank_keys_to_none() -> None:
    settings = AppSettings(fred_api_key="  ", eod_api_key="")

    assert settings.fred_api_key is None
    assert settings.eod_api_key is None
```

- [ ] **Step 2: Run the model test and verify structural failure**

Run:

```bash
uv run pytest packages/core/tests/test_settings_repository.py::test_app_settings_normalizes_blank_keys_to_none -v
```

Expected: FAIL with `ImportError` for `AppSettings` or `core.settings_repository`. This is structural; add the minimal scaffolding in the next step.

- [ ] **Step 3: Add minimal AppSettings scaffolding**

Modify `packages/core/core/models.py` near the other config models:

```python
class AppSettings(BaseModel):
    fred_api_key: str | None = None
    eod_api_key: str | None = None
```

Create `packages/core/core/settings_repository.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.models import AppSettings
from core.paths import default_db_path


@dataclass
class SettingsRepository:
    db_path: Path

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def get(self) -> AppSettings:
        return AppSettings()

    def save(self, settings: AppSettings) -> None:
        raise NotImplementedError
```

- [ ] **Step 4: Run the model test and verify logical failure**

Run:

```bash
uv run pytest packages/core/tests/test_settings_repository.py::test_app_settings_normalizes_blank_keys_to_none -v
```

Expected: FAIL with an assertion because blank strings are not normalized to `None`.

- [ ] **Step 5: Implement AppSettings normalization**

Modify `packages/core/core/models.py` imports and class:

```python
from pydantic import BaseModel, Field, field_validator, model_validator
```

Add:

```python
class AppSettings(BaseModel):
    fred_api_key: str | None = None
    eod_api_key: str | None = None

    @field_validator("fred_api_key", "eod_api_key", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value
```

- [ ] **Step 6: Run the model test and verify green**

Run:

```bash
uv run pytest packages/core/tests/test_settings_repository.py::test_app_settings_normalizes_blank_keys_to_none -v
```

Expected: PASS.

- [ ] **Step 7: Add repository persistence tests**

Append to `packages/core/tests/test_settings_repository.py`:

```python
def test_settings_repository_returns_defaults_for_blank_db(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)

    settings = repo.get()

    assert settings == AppSettings()


def test_settings_repository_round_trips_api_keys(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)
    expected_fred_key = "fred-test-key"
    expected_eod_key = "eod-test-key"

    repo.save(
        AppSettings(
            fred_api_key=expected_fred_key,
            eod_api_key=expected_eod_key,
        )
    )
    loaded = repo.get()

    assert loaded.fred_api_key == expected_fred_key
    assert loaded.eod_api_key == expected_eod_key


def test_settings_repository_creates_table_for_older_db(tmp_path) -> None:
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    repo = SettingsRepository(db_path=db_path)
    expected_key = "fred-from-old-db"
    repo.save(AppSettings(fred_api_key=expected_key))

    assert repo.get().fred_api_key == expected_key
```

- [ ] **Step 8: Run repository tests and verify logical failure**

Run:

```bash
uv run pytest packages/core/tests/test_settings_repository.py -v
```

Expected: FAIL with `NotImplementedError` or missing-table behavior.

- [ ] **Step 9: Implement schema creation and repository persistence**

Replace `packages/core/core/settings_repository.py` with:

```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.models import AppSettings
from core.paths import default_db_path

APP_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    fred_api_key TEXT,
    eod_api_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class SettingsRepository:
    db_path: Path

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(APP_SETTINGS_SCHEMA)
        conn.execute("INSERT OR IGNORE INTO app_settings (id) VALUES (1)")
        conn.commit()

    def get(self) -> AppSettings:
        conn = self._connect()
        try:
            self._ensure_schema(conn)
            row = conn.execute(
                "SELECT fred_api_key, eod_api_key FROM app_settings WHERE id = 1"
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return AppSettings()
        return AppSettings(fred_api_key=row[0], eod_api_key=row[1])

    def save(self, settings: AppSettings) -> None:
        conn = self._connect()
        try:
            self._ensure_schema(conn)
            conn.execute(
                """
                UPDATE app_settings
                SET fred_api_key = ?, eod_api_key = ?, updated_at = datetime('now')
                WHERE id = 1
                """,
                (settings.fred_api_key, settings.eod_api_key),
            )
            conn.commit()
        finally:
            conn.close()
```

- [ ] **Step 10: Add schema to blank DB generator**

Modify `scripts/create_blank_db.py` `SCHEMA`:

```python
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    fred_api_key TEXT,
    eod_api_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO app_settings (id) VALUES (1);
"""
```

- [ ] **Step 11: Regenerate the blank database**

Run:

```bash
uv run python scripts/create_blank_db.py
```

Expected: prints `Wrote blank schema to .../data/data.db.blank`.

- [ ] **Step 12: Verify the generated blank schema**

Run:

```bash
sqlite3 data/data.db.blank ".schema app_settings"
```

Expected output includes:

```sql
CREATE TABLE app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    fred_api_key TEXT,
    eod_api_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

- [ ] **Step 13: Run focused tests**

Run:

```bash
uv run pytest packages/core/tests/test_settings_repository.py tests/test_init_db.py tests/test_db_inspect.py -v
```

Expected: PASS.

- [ ] **Step 14: Commit**

Run:

```bash
git add packages/core/core/models.py packages/core/core/settings_repository.py packages/core/tests/test_settings_repository.py scripts/create_blank_db.py data/data.db.blank
git commit -m "feat(core): add app settings for local API keys"
```

---

## Task 2: Minimal Settings UI

**Files:**

- Modify: `packages/web/web/forms.py`
- Modify: `packages/web/web/routes.py`
- Modify: `packages/web/web/sections.py`
- Modify: `packages/web/web/app.py`
- Modify: `packages/web/web/templates/index.html`
- Create: `packages/web/web/templates/editor_settings.html`
- Modify: `packages/web/tests/test_app.py`

### Intent

Expose the FRED key in the local UI without echoing the stored value. Saving a blank password field keeps the existing key; checking a clear box removes it.

- [ ] **Step 1: Write failing web tests**

Append to `packages/web/tests/test_app.py` imports:

```python
from core.settings_repository import SettingsRepository
from web.forms import CLEAR_FRED_API_KEY, FRED_API_KEY
from web.routes import PLAN_SETTINGS
from web.sections import SETTINGS_TITLE
```

Append tests:

```python
def test_home_shows_settings_section(client: TestClient) -> None:
    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert SETTINGS_TITLE in response.text


def test_patch_settings_persists_fred_api_key(client: TestClient, db_path) -> None:
    expected_key = "fred-ui-key"
    response: httpx.Response = client.patch(
        PLAN_SETTINGS,
        data={FRED_API_KEY: expected_key},
    )

    assert response.status_code == 200
    loaded = SettingsRepository(db_path=db_path).get()
    assert loaded.fred_api_key == expected_key


def test_settings_section_never_echoes_stored_api_key(
    client: TestClient, db_path
) -> None:
    secret_key = "fred-secret-value"
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key=secret_key))

    response: httpx.Response = client.get(HOME)

    assert response.status_code == 200
    assert secret_key not in response.text
    assert "FRED API key is set" in response.text


def test_blank_settings_patch_keeps_existing_key(
    client: TestClient, db_path
) -> None:
    expected_key = "keep-existing-key"
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key=expected_key))

    response: httpx.Response = client.patch(PLAN_SETTINGS, data={FRED_API_KEY: ""})

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key == expected_key


def test_clear_settings_patch_removes_existing_key(
    client: TestClient, db_path
) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="clear-me"))

    response: httpx.Response = client.patch(
        PLAN_SETTINGS,
        data={FRED_API_KEY: "", CLEAR_FRED_API_KEY: "on"},
    )

    assert response.status_code == 200
    assert SettingsRepository(db_path=db_path).get().fred_api_key is None
```

Also add `AppSettings` import:

```python
from core.models import AppSettings
```

- [ ] **Step 2: Run first UI test and verify structural failure**

Run:

```bash
uv run pytest packages/web/tests/test_app.py::test_home_shows_settings_section -v
```

Expected: FAIL with import errors for constants/routes.

- [ ] **Step 3: Add route, section, and form scaffolding**

Modify `packages/web/web/routes.py`:

```python
EDITOR_SETTINGS = "/editor/settings"
PLAN_SETTINGS = "/plan/settings"
```

Modify `packages/web/web/sections.py`:

```python
SETTINGS_TITLE = "Settings"
```

Modify `packages/web/web/forms.py` imports:

```python
from core.models import AppSettings, Household, PersonHousehold, Plan
```

Add constants and DTO:

```python
FRED_API_KEY = "fred_api_key"
CLEAR_FRED_API_KEY = "clear_fred_api_key"


class AppSettingsForm(BaseModel):
    """Flat transport DTO for local app settings."""

    fred_api_key: str | None = None
    clear_fred_api_key: bool = False

    def apply_to(self, settings: AppSettings) -> AppSettings:
        return settings
```

- [ ] **Step 4: Run settings form test and verify logical failure**

Run:

```bash
uv run pytest packages/web/tests/test_app.py::test_patch_settings_persists_fred_api_key -v
```

Expected: FAIL with 404 for `PLAN_SETTINGS` or assertion that the key was not saved.

- [ ] **Step 5: Implement AppSettingsForm behavior**

Replace `AppSettingsForm.apply_to`:

```python
    def apply_to(self, settings: AppSettings) -> AppSettings:
        if self.clear_fred_api_key:
            return settings.model_copy(update={"fred_api_key": None})

        key = self.fred_api_key.strip() if self.fred_api_key else ""
        if key:
            return settings.model_copy(update={"fred_api_key": key})
        return settings
```

- [ ] **Step 6: Wire settings repository and routes in web app**

Modify imports in `packages/web/web/app.py`:

```python
from core.settings_repository import SettingsRepository
from web.forms import AppSettingsForm, HouseholdForm, PortfolioForm
from web.routes import (
    EDITOR_HOUSEHOLD,
    EDITOR_PORTFOLIO,
    EDITOR_SETTINGS,
    HOME,
    PLAN_HOUSEHOLD,
    PLAN_PORTFOLIO,
    PLAN_SETTINGS,
    RESULTS,
)
```

Add repository helper:

```python
def get_settings_repo(request: Request) -> SettingsRepository:
    return SettingsRepository(db_path=_resolve_db_path(request.app))


SettingsRepoDep = Annotated[SettingsRepository, Depends(get_settings_repo)]
```

In `home`, load settings and pass to template:

```python
        settings = get_settings_repo(request).get()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"plan": plan, "result": result, "settings": settings},
        )
```

Add `EDITOR_SETTINGS` GET:

```python
    @app.get(EDITOR_SETTINGS, response_class=HTMLResponse)
    def editor_settings(
        request: Request,
        settings_repo: SettingsRepoDep,
    ) -> HTMLResponse:
        settings = settings_repo.get()
        return templates.TemplateResponse(
            request,
            "editor_settings.html",
            {"settings": settings},
        )
```

Add `PLAN_SETTINGS` PATCH:

```python
    @app.patch(PLAN_SETTINGS)
    def patch_settings(
        settings_repo: SettingsRepoDep,
        fred_api_key: Annotated[str | None, Form()] = None,
        clear_fred_api_key: Annotated[bool, Form()] = False,
    ) -> Response:
        current = settings_repo.get()
        updated = AppSettingsForm(
            fred_api_key=fred_api_key,
            clear_fred_api_key=clear_fred_api_key,
        ).apply_to(current)
        settings_repo.save(updated)
        return Response(status_code=200)
```

Update `results` only if you need settings for a future simulation call; do not change it in this task because the current stub does not consume inflation.

- [ ] **Step 7: Add settings template**

Create `packages/web/web/templates/editor_settings.html`:

```html
<section class="editor-section">
  <h2>{{ sections.SETTINGS_TITLE }}</h2>
  <form
    hx-patch="{{ routes.PLAN_SETTINGS }}"
    hx-trigger="input changed delay:750ms"
    hx-swap="none"
  >
    <p class="helper-text">
      Optional local-only API keys for live market data. Keys are stored in your
      gitignored SQLite database and are never included in plan data.
    </p>
    <label>
      FRED API key
      <input
        type="password"
        name="{{ forms.FRED_API_KEY }}"
        value=""
        placeholder="{% if settings.fred_api_key %}FRED API key is set{% else %}Paste FRED API key{% endif %}"
        autocomplete="off"
      >
    </label>
    {% if settings.fred_api_key %}
    <label>
      <input type="checkbox" name="{{ forms.CLEAR_FRED_API_KEY }}">
      Clear stored FRED API key
    </label>
    {% endif %}
  </form>
</section>
```

- [ ] **Step 8: Include settings section and save behavior**

Modify `packages/web/web/templates/index.html` to include settings:

```html
    {% include "editor_household.html" %}
    {% include "editor_portfolio.html" %}
    {% include "editor_settings.html" %}
```

Modify the JavaScript `isPlanForm` expression:

```javascript
    const isPlanForm =
      form.tagName === "FORM" &&
      (patchTarget === "{{ routes.PLAN_HOUSEHOLD }}" ||
        patchTarget === "{{ routes.PLAN_PORTFOLIO }}" ||
        patchTarget === "{{ routes.PLAN_SETTINGS }}");
```

- [ ] **Step 9: Run focused web tests**

Run:

```bash
uv run pytest packages/web/tests/test_app.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit**

Run:

```bash
git add packages/web/web/forms.py packages/web/web/routes.py packages/web/web/sections.py packages/web/web/app.py packages/web/web/templates/index.html packages/web/web/templates/editor_settings.html packages/web/tests/test_app.py
git commit -m "feat(web): add local API key settings form"
```

---

## Task 3: FRED JSON API Fetch Client

**Files:**

- Create: `packages/simulation/simulation/market_data/fetch.py`
- Create: `packages/simulation/tests/market_data/test_fetch.py`

### Intent

Parse FRED JSON observations and provide a small request function. Tests remain offline by passing canned JSON and an injected opener.

- [ ] **Step 1: Write parser tests**

Create `packages/simulation/tests/market_data/test_fetch.py`:

```python
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from simulation.market_data.fetch import (
    FRED_T10YIE_SERIES_ID,
    parse_fred_observations,
)


def test_parse_fred_observations_skips_non_numeric_rows() -> None:
    payload = json.dumps(
        {
            "observations": [
                {"date": "2026-01-02", "value": "2.35"},
                {"date": "2026-01-05", "value": "."},
                {"date": "2026-01-06", "value": "2.40"},
            ]
        }
    )

    pairs = parse_fred_observations(payload)

    assert pairs == [
        (date(2026, 1, 2), Decimal("2.35")),
        (date(2026, 1, 6), Decimal("2.40")),
    ]


def test_fred_series_constant_names_t10yie() -> None:
    # Contract test: this is the FRED series tpaw uses for suggested inflation.
    assert FRED_T10YIE_SERIES_ID == "T10YIE"
```

- [ ] **Step 2: Run parser tests and verify structural failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_fetch.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing symbols.

- [ ] **Step 3: Add minimal fetch module scaffolding**

Create `packages/simulation/simulation/market_data/fetch.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

FRED_T10YIE_SERIES_ID = "T10YIE"


def parse_fred_observations(payload: str) -> list[tuple[date, Decimal]]:
    raise NotImplementedError
```

- [ ] **Step 4: Run parser tests and verify logical failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_fetch.py -v
```

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement JSON parser**

Replace `fetch.py`:

```python
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

FRED_T10YIE_SERIES_ID = "T10YIE"
FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"


def parse_fred_observations(payload: str) -> list[tuple[date, Decimal]]:
    data = json.loads(payload)
    pairs: list[tuple[date, Decimal]] = []
    for row in data.get("observations", []):
        try:
            pairs.append((date.fromisoformat(row["date"]), Decimal(row["value"])))
        except (KeyError, ValueError, ArithmeticError):
            continue
    return pairs
```

- [ ] **Step 6: Run parser tests and verify green**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_fetch.py -v
```

Expected: PASS.

- [ ] **Step 7: Add request construction test with injected opener**

Append to `test_fetch.py`:

```python
from urllib.request import Request

from simulation.market_data.fetch import fred_observations


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._body.encode("utf-8")


def test_fred_observations_builds_official_json_api_request() -> None:
    captured: dict[str, object] = {}
    expected_key = "fred-request-key"
    observation_start = date(2026, 1, 1)
    payload = json.dumps({"observations": [{"date": "2026-01-02", "value": "2.35"}]})

    def opener(request: Request, timeout: float):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return _FakeResponse(payload)

    pairs = fred_observations(
        api_key=expected_key,
        observation_start=observation_start,
        timeout_seconds=7.5,
        opener=opener,
    )

    assert pairs == [(date(2026, 1, 2), Decimal("2.35"))]
    assert "series_id=T10YIE" in str(captured["url"])
    assert f"api_key={expected_key}" in str(captured["url"])
    assert "file_type=json" in str(captured["url"])
    assert f"observation_start={observation_start.isoformat()}" in str(captured["url"])
    assert captured["timeout"] == 7.5
```

- [ ] **Step 8: Run request test and verify structural failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_fetch.py::test_fred_observations_builds_official_json_api_request -v
```

Expected: FAIL with missing `fred_observations`.

- [ ] **Step 9: Implement request function**

Extend `fetch.py`:

```python
import urllib.parse
import urllib.request
from collections.abc import Callable

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

UrlOpener = Callable[[urllib.request.Request, float], object]


def _default_opener(request: urllib.request.Request, timeout: float):
    return urllib.request.urlopen(request, timeout=timeout)


def fred_observations(
    *,
    api_key: str,
    observation_start: date | None,
    timeout_seconds: float = 10.0,
    opener: UrlOpener = _default_opener,
) -> list[tuple[date, Decimal]]:
    query = {
        "api_key": api_key,
        "series_id": FRED_T10YIE_SERIES_ID,
        "file_type": "json",
    }
    if observation_start is not None:
        query["observation_start"] = observation_start.isoformat()
    url = f"{FRED_OBSERVATIONS_URL}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    with opener(request, timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    return parse_fred_observations(payload)
```

If pyright rejects the opener protocol because the context manager return is too loose, replace `UrlOpener` with a small `Protocol` in the implementation phase.

- [ ] **Step 10: Run focused tests**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_fetch.py -v
```

Expected: PASS.

- [ ] **Step 11: Commit**

Run:

```bash
git add packages/simulation/simulation/market_data/fetch.py packages/simulation/tests/market_data/test_fetch.py
git commit -m "feat(simulation): add FRED T10YIE fetch client"
```

---

## Task 4: Market Data Cache

**Files:**

- Create: `packages/simulation/simulation/market_data/cache.py`
- Create: `packages/simulation/tests/market_data/test_cache.py`

### Intent

Create the canonical on-disk cache as CSV plus sidecar metadata. The cache uses the same CSV shape as the vendored T10YIE file.

- [ ] **Step 1: Write cache write/read-path tests**

Create `packages/simulation/tests/market_data/test_cache.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from simulation.market_data.cache import (
    CACHE_TTL,
    is_t10yie_cache_stale,
    resolve_t10yie_read_path,
    write_t10yie_cache,
)


def test_write_t10yie_cache_uses_vendored_csv_shape(tmp_path: Path) -> None:
    cache_path = tmp_path / "t10yie_daily.csv"
    meta_path = tmp_path / "t10yie_daily.meta.json"
    fetched_at = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    pairs = [(date(2026, 6, 27), Decimal("2.35"))]

    write_t10yie_cache(pairs, now=fetched_at, cache_path=cache_path, meta_path=meta_path)

    assert cache_path.read_text(encoding="utf-8") == "observation_date,T10YIE\n2026-06-27,2.35\n"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["fetched_at"] == fetched_at.isoformat()
    assert meta["source"] == "fred_api"
    assert meta["series_id"] == "T10YIE"


def test_resolve_t10yie_read_path_prefers_cache_when_present(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.csv"
    vendored_path = tmp_path / "vendored.csv"
    cache_path.write_text("observation_date,T10YIE\n2026-01-01,2.0\n", encoding="utf-8")
    vendored_path.write_text("observation_date,T10YIE\n2025-01-01,1.0\n", encoding="utf-8")

    assert resolve_t10yie_read_path(cache_path=cache_path, vendored_path=vendored_path) == cache_path


def test_resolve_t10yie_read_path_falls_back_to_vendored_when_cache_missing(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.csv"
    vendored_path = tmp_path / "vendored.csv"
    vendored_path.write_text("observation_date,T10YIE\n2025-01-01,1.0\n", encoding="utf-8")

    assert resolve_t10yie_read_path(cache_path=cache_path, vendored_path=vendored_path) == vendored_path


def test_cache_stale_uses_source_ttl_constant(tmp_path: Path) -> None:
    meta_path = tmp_path / "t10yie_daily.meta.json"
    now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)
    fresh = now - CACHE_TTL + timedelta(seconds=1)
    meta_path.write_text(json.dumps({"fetched_at": fresh.isoformat()}), encoding="utf-8")

    assert is_t10yie_cache_stale(now=now, meta_path=meta_path) is False

    stale = now - CACHE_TTL - timedelta(seconds=1)
    meta_path.write_text(json.dumps({"fetched_at": stale.isoformat()}), encoding="utf-8")
    assert is_t10yie_cache_stale(now=now, meta_path=meta_path) is True
```

- [ ] **Step 2: Run cache tests and verify structural failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_cache.py -v
```

Expected: FAIL with missing module/symbols.

- [ ] **Step 3: Add minimal cache scaffolding**

Create `packages/simulation/simulation/market_data/cache.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

CACHE_TTL = timedelta(hours=24)


def write_t10yie_cache(pairs, *, now: datetime, cache_path: Path, meta_path: Path) -> None:
    raise NotImplementedError


def resolve_t10yie_read_path(*, cache_path: Path, vendored_path: Path) -> Path:
    raise NotImplementedError


def is_t10yie_cache_stale(*, now: datetime, meta_path: Path) -> bool:
    raise NotImplementedError
```

- [ ] **Step 4: Run cache tests and verify logical failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_cache.py -v
```

Expected: FAIL with `NotImplementedError`.

- [ ] **Step 5: Implement cache module**

Replace `cache.py`:

```python
from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from core.paths import repo_root
from simulation.market_data.fetch import FRED_T10YIE_SERIES_ID

CACHE_TTL = timedelta(hours=24)
_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_T10YIE_VENDORED_PATH = _DATA_DIR / "t10yie_daily.csv"
DEFAULT_MARKET_CACHE_DIR = repo_root() / "data" / "market_cache"
DEFAULT_T10YIE_CACHE_PATH = DEFAULT_MARKET_CACHE_DIR / "t10yie_daily.csv"
DEFAULT_T10YIE_META_PATH = DEFAULT_MARKET_CACHE_DIR / "t10yie_daily.meta.json"


def write_t10yie_cache(
    pairs: list[tuple[date, Decimal]],
    *,
    now: datetime,
    cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    meta_path: Path = DEFAULT_T10YIE_META_PATH,
    source: str = "fred_api",
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["observation_date", FRED_T10YIE_SERIES_ID])
        for observed, percent in sorted(pairs, key=lambda item: item[0]):
            writer.writerow([observed.isoformat(), str(percent)])

    meta_path.write_text(
        json.dumps(
            {
                "fetched_at": now.isoformat(),
                "source": source,
                "series_id": FRED_T10YIE_SERIES_ID,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def resolve_t10yie_read_path(
    *,
    cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    vendored_path: Path = DEFAULT_T10YIE_VENDORED_PATH,
) -> Path:
    if cache_path.is_file():
        return cache_path
    return vendored_path


def is_t10yie_cache_stale(
    *,
    now: datetime,
    meta_path: Path = DEFAULT_T10YIE_META_PATH,
    ttl: timedelta = CACHE_TTL,
) -> bool:
    if not meta_path.is_file():
        return True
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(meta["fetched_at"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return True
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    return now - fetched_at > ttl
```

- [ ] **Step 6: Run cache tests and verify green**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_cache.py -v
```

Expected: PASS.

- [ ] **Step 7: Add gitignore for live market cache**

Modify `.gitignore` near LifeFinances specific entries:

```gitignore
data/market_cache/
```

- [ ] **Step 8: Commit**

Run:

```bash
git add .gitignore packages/simulation/simulation/market_data/cache.py packages/simulation/tests/market_data/test_cache.py
git commit -m "feat(simulation): add market data cache"
```

---

## Task 5: Best-Effort Inflation Refresh Integration

**Files:**

- Modify: `packages/simulation/simulation/market_data/inflation.py`
- Modify: `packages/simulation/tests/market_data/test_inflation.py`
- Modify: `packages/simulation/tests/market_data/test_public_api.py`

### Intent

Keep the existing scalar inflation behavior, add optional live refresh, and ensure no network call happens unless both `allow_refresh=True` and an API key are passed.

- [ ] **Step 1: Write gating tests**

Append to `packages/simulation/tests/market_data/test_inflation.py`:

```python
from datetime import UTC, datetime
```

Append tests:

```python
def test_refresh_does_not_call_fetcher_when_not_allowed(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 2),
        t10yie_path=csv,
        allow_refresh=False,
        api_key="fred-key",
        fetcher=fetcher,
    )

    assert resolved.annual == pytest.approx(0.020)
    assert calls == 0


def test_refresh_does_not_call_fetcher_without_api_key(tmp_path: Path) -> None:
    csv = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    calls = 0

    def fetcher(**kwargs):
        nonlocal calls
        calls += 1
        return []

    resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 2),
        t10yie_path=csv,
        allow_refresh=True,
        api_key=None,
        fetcher=fetcher,
    )

    assert calls == 0
```

- [ ] **Step 2: Run gating tests and verify structural failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py::test_refresh_does_not_call_fetcher_when_not_allowed packages/simulation/tests/market_data/test_inflation.py::test_refresh_does_not_call_fetcher_without_api_key -v
```

Expected: FAIL with `TypeError` for unexpected `allow_refresh`, `api_key`, or `fetcher`.

- [ ] **Step 3: Add signature scaffolding**

Modify `resolve_inflation` signature in `inflation.py`:

```python
def resolve_inflation(
    plan: Plan,
    *,
    today: date | None = None,
    t10yie_path: Path | None = None,
    allow_refresh: bool = False,
    now: datetime | None = None,
    api_key: str | None = None,
    fetcher: T10YIEFetcher = fred_observations,
    t10yie_cache_path: Path = DEFAULT_T10YIE_CACHE_PATH,
    t10yie_meta_path: Path = DEFAULT_T10YIE_META_PATH,
) -> InflationResolved:
```

Add imports:

```python
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from simulation.market_data.cache import (
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    is_t10yie_cache_stale,
    resolve_t10yie_read_path,
    write_t10yie_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, fred_observations

T10YIEFetcher = Callable[..., list[tuple[date, Decimal]]]
```

If `LOOKBACK_DAYS` was not added in Task 3, add it to `fetch.py` as:

```python
LOOKBACK_DAYS = 30
```

Do not use the new parameters yet.

- [ ] **Step 4: Run gating tests and verify green**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py::test_refresh_does_not_call_fetcher_when_not_allowed packages/simulation/tests/market_data/test_inflation.py::test_refresh_does_not_call_fetcher_without_api_key -v
```

Expected: PASS.

- [ ] **Step 5: Write refresh success and failure tests**

Append to `test_inflation.py`:

```python
def test_refresh_writes_cache_and_uses_live_value_when_stale(tmp_path: Path) -> None:
    vendored = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"
    expected_percent = Decimal("2.50")

    def fetcher(**kwargs):
        return [(date(2026, 1, 3), expected_percent)]

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 4),
        t10yie_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="fred-key",
        fetcher=fetcher,
        t10yie_cache_path=cache_path,
        t10yie_meta_path=meta_path,
    )

    assert resolved.annual == pytest.approx(0.025)
    assert cache_path.is_file()
    assert meta_path.is_file()


def test_refresh_failure_falls_back_to_vendored(tmp_path: Path) -> None:
    vendored = _write_t10yie(tmp_path / "vendored.csv", ["2026-01-01,2.0"])
    cache_path = tmp_path / "cache.csv"
    meta_path = tmp_path / "cache.meta.json"

    def fetcher(**kwargs):
        raise RuntimeError("network unavailable")

    resolved = resolve_inflation(
        _suggested_plan(),
        today=date(2026, 1, 4),
        t10yie_path=vendored,
        allow_refresh=True,
        now=datetime(2026, 1, 4, 12, tzinfo=UTC),
        api_key="fred-key",
        fetcher=fetcher,
        t10yie_cache_path=cache_path,
        t10yie_meta_path=meta_path,
    )

    assert resolved.annual == pytest.approx(0.020)
```

- [ ] **Step 6: Run new refresh tests and verify logical failure**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py::test_refresh_writes_cache_and_uses_live_value_when_stale packages/simulation/tests/market_data/test_inflation.py::test_refresh_failure_falls_back_to_vendored -v
```

Expected: FAIL because no refresh/cache logic is implemented.

- [ ] **Step 7: Implement refresh logic**

Modify the suggested branch in `resolve_inflation`:

```python
    else:
        now = now or datetime.now(tz=UTC)
        read_path = t10yie_path
        if read_path is None:
            if (
                allow_refresh
                and api_key
                and is_t10yie_cache_stale(now=now, meta_path=t10yie_meta_path)
            ):
                try:
                    observation_start = now.date() - timedelta(days=LOOKBACK_DAYS)
                    pairs = fetcher(
                        api_key=api_key,
                        observation_start=observation_start,
                    )
                    if pairs:
                        write_t10yie_cache(
                            pairs,
                            now=now,
                            cache_path=t10yie_cache_path,
                            meta_path=t10yie_meta_path,
                        )
                except Exception:
                    pass
            read_path = resolve_t10yie_read_path(cache_path=t10yie_cache_path)
        else:
            if allow_refresh and api_key:
                try:
                    observation_start = now.date() - timedelta(days=LOOKBACK_DAYS)
                    pairs = fetcher(
                        api_key=api_key,
                        observation_start=observation_start,
                    )
                    if pairs:
                        write_t10yie_cache(
                            pairs,
                            now=now,
                            cache_path=t10yie_cache_path,
                            meta_path=t10yie_meta_path,
                        )
                        read_path = resolve_t10yie_read_path(
                            cache_path=t10yie_cache_path,
                            vendored_path=t10yie_path,
                        )
                except Exception:
                    pass
        annual = _suggested_annual(today, read_path)
        source = "suggested"
```

During implementation, prefer extracting the refresh block into a private helper if pyright or readability suffers. Preserve existing behavior when callers only pass `t10yie_path`.

- [ ] **Step 8: Run all inflation tests**

Run:

```bash
uv run pytest packages/simulation/tests/market_data/test_inflation.py packages/simulation/tests/market_data/test_public_api.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

Run:

```bash
git add packages/simulation/simulation/market_data/inflation.py packages/simulation/tests/market_data/test_inflation.py packages/simulation/tests/market_data/test_public_api.py
git commit -m "feat(simulation): refresh suggested inflation from cache"
```

---

## Task 6: Manual Refresh CLI

**Files:**

- Create: `scripts/refresh_market_data.py`
- Create: `tests/test_refresh_market_data.py`
- Delete: `scripts/fetch_t10yie_poc.py` if present

### Intent

Promote the PoC into a real script. It loads the FRED key from `SettingsRepository`, writes cache by default, and supports maintainer `--update-vendored` full-series fetch.

- [ ] **Step 1: Write CLI tests**

Create `tests/test_refresh_market_data.py`:

```python
from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.models import AppSettings
from core.settings_repository import SettingsRepository
from scripts.refresh_market_data import main


def test_refresh_market_data_requires_configured_fred_key(db_path, capsys) -> None:
    exit_code = main(["--db-path", str(db_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "FRED API key is not configured" in captured.err


def test_refresh_market_data_writes_cache_with_fake_fetcher(tmp_path, db_path, capsys) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="fred-cli-key"))
    cache_path = tmp_path / "t10yie_daily.csv"
    meta_path = tmp_path / "t10yie_daily.meta.json"

    def fetcher(**kwargs):
        return [(date(2026, 6, 27), Decimal("2.35"))]

    exit_code = main(
        [
            "--db-path",
            str(db_path),
            "--cache-path",
            str(cache_path),
            "--meta-path",
            str(meta_path),
        ],
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert "2026-06-27" in cache_path.read_text(encoding="utf-8")
    assert meta_path.is_file()
    captured = capsys.readouterr()
    assert "Wrote T10YIE cache" in captured.out


def test_refresh_market_data_update_vendored_writes_target_path(tmp_path, db_path, capsys) -> None:
    SettingsRepository(db_path=db_path).save(AppSettings(fred_api_key="fred-cli-key"))
    vendored_path = tmp_path / "t10yie_daily.csv"

    def fetcher(**kwargs):
        assert kwargs["observation_start"] is None
        return [(date(2026, 6, 27), Decimal("2.35"))]

    exit_code = main(
        [
            "--db-path",
            str(db_path),
            "--update-vendored",
            "--vendored-path",
            str(vendored_path),
        ],
        fetcher=fetcher,
    )

    assert exit_code == 0
    assert "2026-06-27" in vendored_path.read_text(encoding="utf-8")
    captured = capsys.readouterr()
    assert "Update PROVENANCE.md" in captured.out
```

- [ ] **Step 2: Run CLI tests and verify structural failure**

Run:

```bash
uv run pytest tests/test_refresh_market_data.py -v
```

Expected: FAIL with missing `scripts.refresh_market_data`.

- [ ] **Step 3: Add CLI implementation**

Create `scripts/refresh_market_data.py`:

```python
#!/usr/bin/env python3
"""Refresh live market-data cache from configured local API keys."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from core.settings_repository import SettingsRepository
from simulation.market_data.cache import (
    DEFAULT_T10YIE_CACHE_PATH,
    DEFAULT_T10YIE_META_PATH,
    DEFAULT_T10YIE_VENDORED_PATH,
    write_t10yie_cache,
)
from simulation.market_data.fetch import LOOKBACK_DAYS, fred_observations

Fetcher = Callable[..., object]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--cache-path", type=Path, default=DEFAULT_T10YIE_CACHE_PATH)
    parser.add_argument("--meta-path", type=Path, default=DEFAULT_T10YIE_META_PATH)
    parser.add_argument("--vendored-path", type=Path, default=DEFAULT_T10YIE_VENDORED_PATH)
    parser.add_argument("--update-vendored", action="store_true")
    return parser


def main(argv: list[str] | None = None, *, fetcher: Fetcher = fred_observations) -> int:
    args = _parser().parse_args(argv)
    settings = SettingsRepository(db_path=args.db_path).get()
    if not settings.fred_api_key:
        print("FRED API key is not configured in Settings.", file=sys.stderr)
        return 2

    now = datetime.now(tz=UTC)
    observation_start = None if args.update_vendored else now.date() - timedelta(days=LOOKBACK_DAYS)
    pairs = fetcher(api_key=settings.fred_api_key, observation_start=observation_start)
    if not pairs:
        print("FRED returned no usable T10YIE observations.", file=sys.stderr)
        return 1

    if args.update_vendored:
        write_t10yie_cache(
            pairs,
            now=now,
            cache_path=args.vendored_path,
            meta_path=args.vendored_path.with_suffix(".meta.json"),
            source="fred_api_full_series",
        )
        args.vendored_path.with_suffix(".meta.json").unlink(missing_ok=True)
        print(f"Wrote vendored T10YIE CSV to {args.vendored_path}")
        print("Update PROVENANCE.md download date before committing.")
        return 0

    write_t10yie_cache(
        pairs,
        now=now,
        cache_path=args.cache_path,
        meta_path=args.meta_path,
    )
    latest_date = max(observed for observed, _ in pairs)
    print(f"Wrote T10YIE cache to {args.cache_path} (latest {latest_date.isoformat()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

If pyright dislikes `Fetcher` returning `object`, replace it with `Callable[..., list[tuple[date, Decimal]]]` and import `Decimal`.

- [ ] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest tests/test_refresh_market_data.py -v
```

Expected: PASS.

- [ ] **Step 5: Remove the PoC script**

Run:

```bash
rm -f scripts/fetch_t10yie_poc.py
```

Expected: no output. If the file was untracked, this simply removes scratch code from the workspace.

- [ ] **Step 6: Manual live verification when FRED key is available**

Ask the user for the FRED API key now if it has not already been entered in the local UI:

> Please enter the FRED API key in the Settings section of the app, or tell me if you want me to insert it into the local `data/data.db` for this verification run.

Then run:

```bash
uv run python scripts/refresh_market_data.py
```

Expected with a valid key: `Wrote T10YIE cache to .../data/market_cache/t10yie_daily.csv (latest YYYY-MM-DD)`.

If no key is available, skip the live command and say in the final summary that live FRED verification was not run.

- [ ] **Step 7: Commit**

Run:

```bash
git add scripts/refresh_market_data.py tests/test_refresh_market_data.py
git add -u scripts/fetch_t10yie_poc.py
git commit -m "feat(simulation): add market data refresh CLI"
```

---

## Task 7: Docs, Index Status, And Full Verification

**Files:**

- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md`
- Modify: `docs/superpowers/plans/2026-06-12-phase-3a-plus-networked-market-data.md`
- Optional modify: `docs/superpowers/specs/2026-06-28-phase-3a-plus-networked-market-data-design.md` only if implementation naming differs.

### Intent

Mark the optional phase complete only after all tests pass and the local behavior is documented through the plan itself. Do not claim live network verification unless it was actually run.

- [ ] **Step 1: Run full verification**

Run:

```bash
make
```

Expected: PASS for pytest, ruff check, ruff format check, and pyright.

- [ ] **Step 2: Read lints for edited files**

Use the IDE linter diagnostics for edited files:

```text
ReadLints:
- packages/core/core/models.py
- packages/core/core/settings_repository.py
- packages/web/web/app.py
- packages/web/web/forms.py
- packages/simulation/simulation/market_data/fetch.py
- packages/simulation/simulation/market_data/cache.py
- packages/simulation/simulation/market_data/inflation.py
- scripts/refresh_market_data.py
```

Expected: no new diagnostics. Fix any diagnostics caused by this work.

- [ ] **Step 3: Update phase plan status**

At the top of this file, add a completion note under the header:

```markdown
**Status:** Complete
```

In each task, check off completed steps during implementation. If the live FRED verification was skipped because no key was available, leave a short note in this plan under Task 6 Step 6:

```markdown
Live FRED verification skipped: no API key available in this session.
```

- [ ] **Step 4: Update rebuild index Phase 3a+**

Modify `docs/superpowers/plans/2026-06-12-rebuild-index.md` Phase 3a+ exit criteria to checked boxes:

```markdown
- [x] Suggested inflation best-effort auto-updates from the FRED JSON API when `allow_refresh` + key present + stale cache; vendored CSV remains the guaranteed fallback
- [x] Refresh is fail-silent and never blocks the simulation; `make test` stays network-free (injected fetcher, never `allow_refresh=True`)
- [x] Manual refresh CLI (`scripts/refresh_market_data.py`) warms the cache loudly; `--update-vendored` rewrites the committed CSV from a full-series fetch
- [x] API keys stored in `AppSettings` (singleton DB row), entered via a minimal masked web form; injected at the web/CLI boundary; never in plan JSON, plan export, git, or CI
```

Do not change the active phase from Phase 3b unless the user explicitly asks; Phase 3a+ is optional and does not block 3b.

- [ ] **Step 5: Commit completion docs**

Run:

```bash
git add docs/superpowers/plans/2026-06-12-rebuild-index.md docs/superpowers/plans/2026-06-12-phase-3a-plus-networked-market-data.md
git commit -m "docs(simulation): mark Phase 3a+ networked market data complete"
```

- [ ] **Step 6: Final git status**

Run:

```bash
git status --short
```

Expected: no modified tracked files. If `data/market_cache/` exists from live verification, it should not appear because it is gitignored.

---

## Implementation Notes

- **When the FRED key is needed:** only Task 6 Step 6, after all offline tests are passing and the settings UI or DB row exists. No key is needed for Tasks 1–5.
- **TDD discipline:** for each new behavior, run the test once after scaffolding and before implementation so the failure is logical (`AssertionError`, `NotImplementedError`, or 404), not structural (`ImportError`, missing symbol).
- **No secrets in output:** never print the FRED key, never place it in a commit message, never include it in HTML responses, and never put it in plan JSON.
- **DB schema:** `data/data.db.blank` is committed and must change only via `uv run python scripts/create_blank_db.py`; personal `data/data.db` remains gitignored.
- **Network-free CI:** all pytest tests use fakes/injection. The only real network call is the optional manual CLI verification.

---

## Self-Review Checklist

- Spec §1 live FRED fetch: Task 3 and Task 6.
- Spec §1 on-disk cache: Task 4.
- Spec §1 best-effort auto-refresh: Task 5.
- Spec §1 DB-backed keys + minimal UI: Task 1 and Task 2.
- Spec §2 no `.env`, keys not on `Plan`: Task 1 and Task 2.
- Spec §3 fetch/cache/inflation boundaries: Task 3, Task 4, Task 5.
- Spec §5 manual refresh and `--update-vendored`: Task 6.
- Spec §6 tests: every behavior has a focused offline test before implementation.
- Spec §9 schema change: Task 1 regenerates `data/data.db.blank` and implements older DB compatibility.

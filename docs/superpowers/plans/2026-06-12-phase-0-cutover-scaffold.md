# Phase 0 — Cutover and Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve legacy v1 in a tag and archive repo, then replace the LifeFinances tree with an empty uv workspace skeleton, SQLite bootstrap, and Python-only developer tooling.

**Architecture:** Same-repo clean cutover per [design spec §2](../specs/2026-06-12-life-finances-rebuild-design.md). Tag the last legacy commit, archive docs, delete Flask/React/devcontainer trees, stand up `packages/{core,domain,simulation,web}`, `data/data.db.blank`, and bootstrap scripts. No web app yet — that is Phase 1.

**Tech Stack:** uv workspace, Python 3.14+, Pydantic 2.4, SQLite, pytest, ruff, pyright, pre-commit

**status:** complete

---

## File structure (Phase 0 end state)

```
LifeFinances/
├── AGENTS.md                          # NEW — rebuild agent guide
├── README.md                          # REWRITE — bootstrap, legacy pointers
├── LICENSE                            # KEEP
├── Makefile                           # REWRITE — Python-only test/lint
├── pyproject.toml                     # NEW — uv workspace root
├── pyrightconfig.json                 # NEW — root typecheck config
├── .gitignore                         # MODIFY — add data/data.db
├── .pre-commit-config.yaml            # KEEP (entry unchanged)
├── scripts/
│   ├── precommit.sh                   # REWRITE — drop Node logic
│   ├── init_db.py                     # NEW
│   ├── db_inspect.py                  # NEW (minimal)
│   └── import_legacy_yaml.py          # NEW (stub → Phase 4)
├── data/
│   ├── data.db.blank                  # NEW — committed empty schema
│   └── data.db                        # gitignored working copy
├── packages/
│   ├── core/
│   │   ├── pyproject.toml
│   │   ├── core/__init__.py
│   │   ├── core/paths.py
│   │   └── tests/test_scaffold.py
│   ├── domain/
│   │   ├── pyproject.toml
│   │   ├── domain/__init__.py
│   │   └── tests/test_scaffold.py
│   ├── simulation/
│   │   ├── pyproject.toml
│   │   ├── simulation/__init__.py
│   │   └── tests/test_scaffold.py
│   └── web/
│       ├── pyproject.toml
│       ├── web/__init__.py
│       └── tests/test_scaffold.py
├── tools/
│   └── AGENTS.md                      # NEW — placeholder for Phase 5
├── tests/
│   └── test_init_db.py                # NEW — integration test for init script
├── docs/superpowers/                  # KEEP — planning + spec
└── archive/
    └── docs/features/                 # MOVED from docs/features/
```

**Deleted in this phase:** `backend/`, `frontend/`, `.devcontainer/`, `.nvmrc`, `.dockerignore`, legacy root `Makefile` targets, Node-related gitignore entries no longer needed.

**Not touched without explicit user approval:** `.github/workflows/*` (see Task 15).

---

### Task 1: Tag the pre-cutover commit

**Files:**
- Create: *(git tag only)*

**Prerequisite:** Working tree clean; architecture spec committed on `main`.

- [ ] **Step 1: Confirm clean tree**

Run:

```bash
cd /Users/chris/Projects/life-finances-workspace/LifeFInances
git status
```

Expected: `nothing to commit, working tree clean` (or only unrelated untracked files you intend to ignore).

- [ ] **Step 2: Create annotated tag on current HEAD**

Run:

```bash
git tag -a legacy/v1-final -m "Final legacy Flask/React simulator before 2026 rebuild"
git show legacy/v1-final --no-patch
```

Expected: tag points at current commit; message mentions legacy v1.

- [ ] **Step 3: Push tag to origin**

Run:

```bash
git push origin legacy/v1-final
```

Expected: remote tag created.

- [ ] **Step 4: Optional legacy branch**

Run:

```bash
git branch legacy legacy/v1-final
git push origin legacy
```

Expected: branch `legacy` exists at same commit as tag.

- [ ] **Step 5: Commit**

No file commit for this task. Record the tagged SHA in your session notes:

```bash
git rev-parse legacy/v1-final
```

---

### Task 2: Create legacy archive repo (manual GitHub step)

**Files:**
- Modify: `README.md` (legacy pointer section added in Task 10)

This task is **manual** — an agent cannot create `chriskelly/life-finances-legacy` without repo admin access. Document completion in the PR description.

- [ ] **Step 1: Mirror pre-cutover state to new repo**

On a machine with `gh` authenticated as repo owner, run **once**:

```bash
LEGACY_SHA="$(git rev-parse legacy/v1-final)"
git clone --bare https://github.com/chriskelly/LifeFinances.git /tmp/life-finances-mirror
cd /tmp/life-finances-mirror
git push --mirror https://github.com/chriskelly/life-finances-legacy.git
```

If the archive repo does not exist yet:

```bash
gh repo create chriskelly/life-finances-legacy --private --description "Archived LifeFinances v1 (Flask/React) — see tag legacy/v1-final"
```

Then re-run the mirror push.

- [ ] **Step 2: Verify archive default branch shows legacy tree**

Run:

```bash
gh repo view chriskelly/life-finances-legacy --json defaultBranchRef,url
```

Expected: repo exists; default branch contains `backend/` and `frontend/`.

- [ ] **Step 3: Add archive note to PR checklist**

In the Phase 0 PR body, include:

```markdown
- [x] `life-finances-legacy` mirror pushed from `legacy/v1-final` (<SHA>)
- Archive URL: https://github.com/chriskelly/life-finances-legacy
- Legacy tag in active repo: `legacy/v1-final`
```

---

### Task 3: Archive legacy documentation

**Files:**
- Move: `docs/features/` → `archive/docs/features/`
- Create: `archive/README.md`

- [ ] **Step 1: Write failing test that old path is gone**

Create `tests/test_archive_layout.py`:

```python
"""Phase 0 archive layout checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_feature_docs_archived() -> None:
    assert not (REPO_ROOT / "docs" / "features").exists()
    assert (REPO_ROOT / "archive" / "docs" / "features").is_dir()


def test_superpowers_docs_remain() -> None:
    assert (REPO_ROOT / "docs" / "superpowers" / "specs").is_dir()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_archive_layout.py -v
```

Expected: FAIL — `uv` may fail first if workspace not yet created; if pytest runs, FAIL on missing archive paths.

- [ ] **Step 3: Move docs and add archive README**

Run:

```bash
mkdir -p archive/docs
git mv docs/features archive/docs/features
```

Create `archive/README.md`:

```markdown
# Archive

Frozen pre-rebuild documentation and artifacts. Coding agents: ignore unless explicitly asked to reference legacy design.

| Path | Contents |
|------|----------|
| `docs/features/` | Legacy speckit-style feature docs (Flask/React era) |

Active planning lives in `docs/superpowers/`.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_archive_layout.py -v
```

Expected: PASS (after workspace exists from Task 5; if not yet, defer re-run until Task 14).

- [ ] **Step 5: Commit**

```bash
git add archive/ tests/test_archive_layout.py
git commit -m "chore(docs): archive legacy feature docs under archive/"
```

---

### Task 4: Remove legacy application trees

**Files:**
- Delete: `backend/`, `frontend/`, `.devcontainer/`, `.nvmrc`, `.dockerignore`

- [ ] **Step 1: Write failing test for removed paths**

Append to `tests/test_archive_layout.py`:

```python
def test_legacy_app_trees_removed() -> None:
    assert not (REPO_ROOT / "backend").exists()
    assert not (REPO_ROOT / "frontend").exists()
    assert not (REPO_ROOT / ".devcontainer").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_archive_layout.py::test_legacy_app_trees_removed -v
```

Expected: FAIL — directories still exist.

- [ ] **Step 3: Remove legacy trees**

Run:

```bash
git rm -r backend frontend .devcontainer
git rm -f .nvmrc .dockerignore
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/test_archive_layout.py::test_legacy_app_trees_removed -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore: remove legacy Flask/React backend and devcontainer"
```

---

### Task 5: Create uv workspace root

**Files:**
- Create: `pyproject.toml`
- Delete: `backend/uv.lock` *(already removed with backend/)*

- [ ] **Step 1: Write root `pyproject.toml`**

Create `pyproject.toml`:

```toml
[project]
name = "life-finances"
version = "0.1.0"
description = "Personal finances simulator — TPAW monthly modeling"
requires-python = ">=3.10"
dependencies = []

[tool.uv.workspace]
members = ["packages/*"]

[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "ruff>=0.14.10",
    "pyright>=1.1.407",
    "pre-commit>=3.5.0",
]

[tool.pytest.ini_options]
testpaths = ["tests", "packages"]
pythonpath = ["."]

[tool.ruff]
line-length = 88
target-version = "py310"
src = ["packages", "scripts", "tests"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "C90"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"tests/*" = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"
```

- [ ] **Step 2: Sync workspace (packages added in Task 6)**

Run after Task 6 completes:

```bash
uv sync
```

Expected: `Resolved ... packages` with no errors; `.venv` created at repo root.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add uv workspace root pyproject.toml"
```

---

### Task 6: Create empty package skeletons

**Files:**
- Create: `packages/core/`, `packages/domain/`, `packages/simulation/`, `packages/web/` (pyproject + `__init__.py` + scaffold tests)

Package dependency direction (strict, wired now even though code is empty):

```
web → simulation, domain, core
simulation → domain, core
domain → core
```

- [ ] **Step 1: Write failing import test**

Create `packages/core/tests/test_scaffold.py`:

```python
import core


def test_core_package_importable() -> None:
    assert core.__doc__
```

Create analogous files for other packages (`domain`, `simulation`, `web`) with matching test names.

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest packages/core/tests/test_scaffold.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: Add package files**

`packages/core/pyproject.toml`:

```toml
[project]
name = "life-finances-core"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.4.2",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["core"]
```

`packages/core/core/__init__.py`:

```python
"""Plan model and SQLite persistence."""
```

`packages/core/core/paths.py`:

```python
"""Repository path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the LifeFinances repository root."""
    return Path(__file__).resolve().parents[3]


def default_blank_db_path() -> Path:
    return repo_root() / "data" / "data.db.blank"


def default_db_path() -> Path:
    override = os.environ.get("LIFE_FINANCES_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "data" / "data.db"
```

`packages/domain/pyproject.toml`:

```toml
[project]
name = "life-finances-domain"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "life-finances-core",
]

[tool.uv.sources]
life-finances-core = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["domain"]
```

`packages/domain/domain/__init__.py`:

```python
"""Income, pension, Social Security, and tax domain logic."""
```

`packages/simulation/pyproject.toml`:

```toml
[project]
name = "life-finances-simulation"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "life-finances-core",
    "life-finances-domain",
]

[tool.uv.sources]
life-finances-core = { workspace = true }
life-finances-domain = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["simulation"]
```

`packages/simulation/simulation/__init__.py`:

```python
"""Monthly TPAW simulation engine."""
```

`packages/web/pyproject.toml`:

```toml
[project]
name = "life-finances-web"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "jinja2>=3.1.0",
    "life-finances-core",
    "life-finances-domain",
    "life-finances-simulation",
]

[tool.uv.sources]
life-finances-core = { workspace = true }
life-finances-domain = { workspace = true }
life-finances-simulation = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["web"]
```

`packages/web/web/__init__.py`:

```python
"""FastAPI + Jinja2 + HTMX web application."""
```

Create `packages/domain/tests/test_scaffold.py`, `packages/simulation/tests/test_scaffold.py`, `packages/web/tests/test_scaffold.py` mirroring the core test.

- [ ] **Step 4: Sync and run tests**

Run:

```bash
uv sync
uv run pytest packages/*/tests/test_scaffold.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add packages/
git commit -m "chore: scaffold empty core/domain/simulation/web packages"
```

---

### Task 7: SQLite blank schema and init script

**Files:**
- Create: `data/data.db.blank`, `scripts/init_db.py`, `scripts/create_blank_db.py` *(generator, run once)*

- [ ] **Step 1: Write failing init_db test**

Create `tests/test_init_db.py`:

```python
"""Tests for database bootstrap."""

import os
import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import init_db  # noqa: E402


@pytest.fixture
def temp_repo_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    blank = data_dir / "data.db.blank"
    blank.write_bytes((REPO_ROOT / "data" / "data.db.blank").read_bytes())
    monkeypatch.setenv("LIFE_FINANCES_DB_PATH", str(data_dir / "data.db"))
    monkeypatch.setattr(init_db, "DEFAULT_BLANK", blank)
    return data_dir


def test_init_db_creates_file_from_blank(temp_repo_paths: Path) -> None:
    db_path = init_db.init_db()
    assert db_path.is_file()
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    assert ("plans",) in tables


def test_init_db_is_idempotent(temp_repo_paths: Path) -> None:
    first = init_db.init_db()
    second = init_db.init_db()
    assert first == second
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_init_db.py -v
```

Expected: FAIL — missing `data/data.db.blank` or import error.

- [ ] **Step 3: Generate blank database**

Create `scripts/create_blank_db.py`:

```python
#!/usr/bin/env python3
"""One-shot generator for data/data.db.blank. Re-run only when schema changes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.paths import default_blank_db_path, repo_root

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def main() -> None:
    blank_path = default_blank_db_path()
    blank_path.parent.mkdir(parents=True, exist_ok=True)
    if blank_path.exists():
        blank_path.unlink()
    conn = sqlite3.connect(blank_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    print(f"Wrote blank schema to {blank_path} (repo root {repo_root()})")


if __name__ == "__main__":
    main()
```

Run once:

```bash
uv run python scripts/create_blank_db.py
```

Create `scripts/init_db.py`:

```python
#!/usr/bin/env python3
"""Bootstrap data/data.db from data/data.db.blank."""

from __future__ import annotations

import shutil
from pathlib import Path

from core.paths import default_blank_db_path, default_db_path

DEFAULT_BLANK = default_blank_db_path()


def init_db(*, force: bool = False) -> Path:
    """Copy blank schema to working DB path if missing (or when force=True)."""
    db_path = default_db_path()
    blank_path = DEFAULT_BLANK
    if not blank_path.is_file():
        raise FileNotFoundError(f"Blank schema not found: {blank_path}")
    if db_path.exists() and not force:
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(blank_path, db_path)
    return db_path


def main() -> None:
    path = init_db()
    print(f"Database ready at {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests and manual smoke**

Run:

```bash
uv run pytest tests/test_init_db.py -v
rm -f data/data.db
uv run python scripts/init_db.py
test -f data/data.db && echo OK
```

Expected: tests pass; `data/data.db` created locally (gitignored).

- [ ] **Step 5: Commit**

```bash
git add data/data.db.blank scripts/init_db.py scripts/create_blank_db.py tests/test_init_db.py
git commit -m "feat(data): add blank SQLite schema and init_db bootstrap"
```

---

### Task 8: db_inspect and import_legacy_yaml stubs

**Files:**
- Create: `scripts/db_inspect.py`, `scripts/import_legacy_yaml.py`

- [ ] **Step 1: Write failing test for db_inspect help**

Create `tests/test_db_inspect.py`:

```python
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_db_inspect_help() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "db_inspect.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--plan" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/test_db_inspect.py -v
```

Expected: FAIL — script missing.

- [ ] **Step 3: Implement minimal scripts**

`scripts/db_inspect.py`:

```python
#!/usr/bin/env python3
"""Inspect plans stored in the LifeFinances SQLite database."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from core.paths import default_db_path


def inspect_plan(plan_id: int) -> None:
    db_path = default_db_path()
    if not db_path.is_file():
        print(f"No database at {db_path}. Run: uv run python scripts/init_db.py", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT id, name, data, created_at, updated_at FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        print(f"Plan {plan_id} not found.", file=sys.stderr)
        sys.exit(1)
    payload = {
        "id": row["id"],
        "name": row["name"],
        "data": json.loads(row["data"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=int, required=True, help="Plan id to print")
    args = parser.parse_args()
    inspect_plan(args.plan)


if __name__ == "__main__":
    main()
```

`scripts/import_legacy_yaml.py`:

```python
#!/usr/bin/env python3
"""Import legacy config.yml into SQLite. Full implementation: Phase 4."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", help="Path to legacy config.yml")
    _ = parser.parse_args()
    print("import_legacy_yaml.py is not implemented until Phase 4.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test**

Run:

```bash
uv run pytest tests/test_db_inspect.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/db_inspect.py scripts/import_legacy_yaml.py tests/test_db_inspect.py
git commit -m "chore(scripts): add db_inspect and legacy import stub"
```

---

### Task 9: Root AGENTS.md

**Files:**
- Modify: `AGENTS.md` *(full replace)*

- [ ] **Step 1: Replace root AGENTS.md**

Replace entire file with:

```markdown
# LifeFinances — Agent Guide

LifeFinances is a personal finances simulator rebuilt in 2026 (Python, TPAW monthly modeling, SQLite, FastAPI + HTMX). Pre-rebuild Flask/React code lives at git tag `legacy/v1-final` and https://github.com/chriskelly/life-finances-legacy.

## Tech stack

| Layer | Tech |
| ----- | ---- |
| Runtime | Python 3.10+, uv workspace |
| Web | FastAPI, Jinja2, HTMX (Phase 1+) |
| Data | SQLite (`data/data.db`), Pydantic models in `packages/core` |
| Simulation | TPAW engine in `packages/simulation` |
| Tools | Marimo apps in `tools/` |
| Tests | pytest, ruff, pyright |

## Repo map

```
.
├── AGENTS.md
├── pyproject.toml           # uv workspace root — run commands from here
├── packages/
│   ├── core/                # Plan model, SQLite persistence
│   ├── domain/              # SS, pension, job income, taxes
│   ├── simulation/          # Monthly TPAW engine
│   └── web/                 # FastAPI + HTMX UI
├── tools/                   # Marimo apps — see tools/AGENTS.md
├── data/
│   ├── data.db.blank        # committed schema
│   └── data.db              # gitignored working DB
├── scripts/
│   ├── init_db.py
│   ├── db_inspect.py
│   └── import_legacy_yaml.py
├── docs/superpowers/        # active specs and phase plans
└── archive/                 # frozen legacy docs — ignore unless asked
```

## Working directory contract

Always run developer commands from the **repository root**. `LIFE_FINANCES_DB_PATH` overrides the default `data/data.db` location.

## Bootstrap

```bash
uv sync
uv run python scripts/init_db.py
```

## Database inspection

```bash
sqlite3 data/data.db ".schema"
uv run python scripts/db_inspect.py --plan 1
```

## Commands

| Action | Command |
| ------ | ------- |
| Install deps | `uv sync` |
| Run all tests | `make test` |
| Lint | `make lint` |
| Lint + test | `make` |
| Pre-commit | `pre-commit run --all-files` |

After substantive changes, run `make` and confirm it passes before claiming work complete.

## Package dependency direction (strict)

```
web → simulation, domain, core
tools → simulation, domain, core   (never import web)
simulation → domain, core
domain → core
core → stdlib + pydantic + sqlite
```

## AI artifact policy

| Location | Role |
| -------- | ---- |
| `docs/superpowers/specs/` | Architecture spec |
| `docs/superpowers/plans/` | Phase implementation plans |
| `packages/simulation/OVERVIEW.md` | TPAW parity backlog (Phase 3+) |
| `packages/domain/OVERVIEW.md` | Legacy port map (Phase 2+) |
| `archive/` | Frozen pre-rebuild docs |

Do not create new `docs/features/.../Development/plan.md` chains.

## Hard guardrails

- NEVER commit `data/data.db` or personal plan data.
- NEVER modify `config.yml` — YAML workflow removed; legacy import is Phase 4 script only.
- NEVER modify files under `.github/workflows/` without explicit user confirmation.
- NEVER edit lockfiles by hand — use `uv add` / `uv sync`.
- NEVER import `web` from `tools/` or `simulation`.
- NEVER disable lint or type-check rules to pass CI — fix the underlying issue.

## Phase planning

Load `docs/superpowers/plans/2026-06-12-rebuild-index.md` at session start; execute only the active phase plan.
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs: rewrite root AGENTS.md for rebuild workspace"
```

---

### Task 10: README rewrite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace README.md**

Replace with concise human-facing bootstrap (keep LICENSE reference):

```markdown
# LifeFinances

Personal finances and retirement planning simulator — rebuilt 2026 with monthly TPAW modeling, SQLite, and a Python web UI.

**Legacy v1 (Flask + React):** tag [`legacy/v1-final`](https://github.com/chriskelly/LifeFinances/tree/legacy/v1-final) and mirror repo [life-finances-legacy](https://github.com/chriskelly/life-finances-legacy).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.10+.

```bash
uv sync
uv run python scripts/init_db.py
```

Working database: `data/data.db` (gitignored). Schema template: `data/data.db.blank`.

Override DB path: `LIFE_FINANCES_DB_PATH=/path/to/data.db`

## Development

```bash
make test    # pytest
make lint    # ruff + pyright
make         # both
```

Agent conventions: [`AGENTS.md`](AGENTS.md).

## Backup

Copy `data/data.db` to back up plans. No in-app export in v1.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for rebuild bootstrap"
```

---

### Task 11: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add SQLite working copy and drop obsolete entries**

Add near top under a `# LifeFinances rebuild` comment:

```gitignore
# LifeFinances rebuild
data/data.db
```

Remove (no longer applicable):

- `config.yml` line *(optional keep — harmless if file absent; remove to avoid implying YAML workflow)*
- `frontend/node_modules/`, `frontend/dist/`, `frontend/coverage/`, `*.tsbuildinfo`
- `.devcontainer/history/.zsh_history`

Keep: `.venv`, pytest caches, `.env`, `.DS_Store`, `.idea/`.

- [ ] **Step 2: Verify ignored**

Run:

```bash
uv run python scripts/init_db.py
git status --short data/data.db
```

Expected: `data/data.db` does not appear as untracked (ignored).

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore working SQLite database"
```

---

### Task 12: Makefile, pyright, and pre-commit (Python-only)

**Files:**
- Modify: `Makefile`, `scripts/precommit.sh`, `pyrightconfig.json` *(create)*

- [ ] **Step 1: Replace Makefile**

```makefile
all: test lint

test:
	uv run pytest

ruff-check:
	uv run ruff check .

ruff-format-check:
	uv run ruff format --check .

pyright:
	uv run pyright

lint: ruff-check ruff-format-check pyright
```

- [ ] **Step 2: Simplify precommit.sh**

Replace `scripts/precommit.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"
exec make "$@"
```

Run:

```bash
chmod +x scripts/precommit.sh
```

- [ ] **Step 3: Add root pyrightconfig.json**

```json
{
  "include": ["packages", "scripts", "tests"],
  "exclude": ["**/__pycache__", ".venv", "archive"],
  "pythonVersion": "3.10",
  "typeCheckingMode": "basic",
  "venvPath": ".",
  "venv": ".venv"
}
```

- [ ] **Step 4: Run full make**

Run:

```bash
make
```

Expected: all tests pass; ruff and pyright clean.

- [ ] **Step 5: Commit**

```bash
git add Makefile scripts/precommit.sh pyrightconfig.json
git commit -m "chore: Python-only Makefile, pyright, and pre-commit wrapper"
```

---

### Task 13: tools/ placeholder

**Files:**
- Create: `tools/AGENTS.md`

- [ ] **Step 1: Add tools agent guide stub**

```markdown
# Tools — Agent Guide

Marimo standalone apps live here. Phase 5 adds the disability insurance calculator.

## Rules

- Import `core`, `domain`, `simulation` only — **never** `web`.
- Load plans from SQLite (`data/data.db`) or inline parameters for what-if analysis.
- Run: `uv run marimo edit tools/<app>.py` (Marimo added in Phase 5).
```

- [ ] **Step 2: Commit**

```bash
git add tools/AGENTS.md
git commit -m "docs: add tools AGENTS.md placeholder"
```

---

### Task 14: Final verification gate

**Files:**
- Modify: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (active phase table)

- [ ] **Step 1: Run full verification**

Run:

```bash
uv sync
uv run python scripts/init_db.py
make
pre-commit run --all-files
```

Expected: all pass.

- [ ] **Step 2: Manual layout check**

Run:

```bash
test -f data/data.db.blank
test -f packages/core/pyproject.toml
test -f packages/web/pyproject.toml
! test -d backend
! test -d frontend
git tag -l 'legacy/v1-final'
```

Expected: all checks succeed; tag listed.

- [ ] **Step 3: Update rebuild index active phase**

In `docs/superpowers/plans/2026-06-12-rebuild-index.md`, set:

```markdown
| **Current phase** | Phase 0 complete |
| **Active plan** | `2026-06-12-phase-0-cutover-scaffold.md` |
| **Next action** | Write `2026-06-12-phase-1-core-loop.md`, then execute Phase 1 |
```

Add to Completed plans table:

```markdown
| Phase 0 | `2026-06-12-phase-0-cutover-scaffold.md` | complete |
```

Set this plan's header `**status:** complete`.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/
git commit -m "docs: mark Phase 0 complete in rebuild index"
```

---

### Task 15: CI workflow (requires explicit user approval)

**Guardrail:** Root `AGENTS.md` forbids editing `.github/workflows/` without explicit user confirmation. **Stop and ask the user before this task.**

**Files:**
- Replace: `.github/workflows/main_ci.yml` content
- Keep: `.github/workflows/fix_ci.yml` *(still valid)*

- [ ] **Step 0: Obtain user approval**

Ask: "Phase 0 requires replacing devcontainer-based CI with uv-native Python CI. Approve editing `.github/workflows/main_ci.yml`?"

Do not proceed until user confirms.

- [ ] **Step 1: Replace main_ci.yml**

```yaml
name: Main CI

on:
  push:
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"

      - name: Sync dependencies
        run: uv sync

      - name: Run tests
        run: make test

      - name: Run lint
        run: make lint
```

- [ ] **Step 2: Push and verify CI**

Open PR or push branch; confirm GitHub Actions "Main CI" passes.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/main_ci.yml
git commit -m "ci: replace devcontainer CI with uv Python workspace checks"
```

---

## Self-review

### Spec coverage (Phase 0 exit criteria → tasks)

| Exit criterion | Task |
| -------------- | ---- |
| Tag `legacy/v1-final` | Task 1 |
| `life-finances-legacy` repo | Task 2 (manual) |
| Workspace layout matches spec §2 | Tasks 5–6, 7, 13 |
| `uv sync` succeeds | Tasks 5–6 |
| `init_db.py` creates `data/data.db` | Task 7 |
| Root `AGENTS.md` bootstrap + inspect + artifact policy | Task 9 |
| CI minimal pass | Task 15 (with approval) |
| Archive `docs/features/` | Task 3 |
| `.gitignore` for `data/data.db` | Task 11 |

### Placeholder scan

No TBD steps. `import_legacy_yaml.py` intentionally exits 2 until Phase 4 (documented).

### Type consistency

- DB path helpers live in `core.paths`; scripts import `core.paths` via workspace install.
- Table column `data` stores JSON text; `db_inspect` uses `json.loads`.

### Note on design spec §8

Design spec Phase 0 mentions "Minimal FastAPI split-pane shell" — **rebuild index defers that to Phase 1**. This plan follows the index.

---

## PR checklist (for human review)

- [ ] Tag `legacy/v1-final` pushed
- [ ] `life-finances-legacy` mirror verified
- [ ] Legacy trees removed; `archive/docs/features/` present
- [ ] `uv sync` + `make` pass locally
- [ ] `uv run python scripts/init_db.py` creates gitignored `data/data.db`
- [ ] CI updated (if approved) and green on PR

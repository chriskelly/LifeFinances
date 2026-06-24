# LifeFinances — Agent Guide

LifeFinances is a personal finances simulator rebuilt in 2026 (Python, TPAW monthly modeling, SQLite, FastAPI + HTMX). Pre-rebuild Flask/React code lives at git tag `legacy/v1-final` and https://github.com/chriskelly/life-finances-legacy.

## Tech stack

| Layer | Tech |
| ----- | ---- |
| Runtime | Python 3.14+, uv workspace |
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

## Testing policy

Follow TDD for every feature and bugfix. Test **our logic**, not library behavior — do not add tests that only exercise Pydantic validation, trivial getters, or framework wiring unless a phase plan calls for a specific integration smoke test.

### Avoid fragile values

Never hardcode the same literal in both arrange/act and assert. Bind shared values to a variable and reference it in both places.

### Pull constants from source

Import defaults, thresholds, and config from production code in tests. Do not copy literals that can drift. Inline a literal only for intentional contract tests; comment that the value is pinned.

### TDD: red-green without wasting a structural loop

1. Write the test first against intended behavior (including symbols that do not exist yet).
2. Add minimal scaffolding so structure exists but logic does not (`NotImplementedError`, stub return).
3. Run the test once — confirm failure is **logical** (`AssertionError`, `NotImplementedError`), not **structural** (`ImportError`, `AttributeError`, `ModuleNotFoundError`). Fix scaffolding until logical; do not commit or checklist a separate "structural failure" pytest run.
4. Implement the logic.
5. Run again — must pass. Never trust an unverified green.

### General rules

- One logical behavior per test; name tests after behavior, not methods.
- Keep arrange / act / assert visually distinct.
- Inject clocks and dependencies for time-dependent logic (e.g. optional `today: date`, `ran_at: datetime`) — never assert against wall-clock time.

### Shared test infrastructure

- **`core.db_bootstrap.materialize_blank_db`** — copy committed blank schema to an arbitrary path; used by tests, `scripts/init_db.py`, and pytest fixtures.
- **Repo-root `conftest.py`** — cross-package fixtures (`db_path`, `repo`). Pytest discovers it for all `packages/*/tests/`.
- **Package `conftest.py`** — only fixtures specific to that package (e.g. web `client`). Do not duplicate `db_path` / `repo`.
- **Web routes and labels** — path/title constants in `web/routes.py`, `web/sections.py`; per-section form DTOs in `web/forms.py` with flat field names bound by FastAPI `Form()`. Form DTOs are transport-only; validation constraints live on `core.models` (see `packages/web/AGENTS.md`).

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

## Other Coding Preferences

### Complexity Reduction
- SHOULD avoid single line functions unless there's real risk of drift between call sites
- SHOULD require named parameters for functions with more than one arguement

### Performance
- SHOULD evaluate downstream consumers of O(n) operations to prevent O(n^2) performance

## Phase planning

Load `docs/superpowers/plans/2026-06-12-rebuild-index.md` at session start; execute only the active phase plan.

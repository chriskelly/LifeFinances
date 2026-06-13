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

# LifeFinances — Agent Guide

LifeFinances is a personal finances simulator rebuilt in 2026 (Python, TPAW monthly modeling, SQLite, FastAPI + HTMX). Pre-rebuild Flask/React code lives at git tag `legacy/v1-final` and https://github.com/chriskelly/life-finances-legacy.

## Tech stack

| Layer | Tech |
| ----- | ---- |
| Runtime | Python 3.14+, uv workspace |
| Web | FastAPI, Jinja2, HTMX |
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
├── data/                    # data.db.blank committed; data.db gitignored
├── scripts/                 # init_db, db_inspect, refresh_market_data, import_legacy_yaml
└── docs/                    # cross-cutting reference
```

## Bootstrap

```bash
uv sync
uv run python scripts/init_db.py
```

## Commands

Run everything from the **repository root**; `LIFE_FINANCES_DB_PATH` overrides the default `data/data.db`.

| Action | Command |
| ------ | ------- |
| Install deps | `uv sync` |
| Run all tests | `make test` |
| Coverage gate | `make coverage` |
| Lint | `make lint` |
| Lint + test | `make` |
| Pre-commit | `pre-commit run --all-files` |
| DB schema | `sqlite3 data/data.db ".schema"` |
| Inspect a plan | `uv run python scripts/db_inspect.py --plan 1` |

After substantive changes, run `make` and confirm it passes before claiming work complete.

## Tools and results

- Explain a result: with the dev server running, follow `.agents/skills/explain-results/SKILL.md`; call the local JSON routes for the cached simulation, never a separate simulation process.
- Disability insurance calculator: `uv run marimo edit tools/disability_insurance.py` (rules: `tools/AGENTS.md`).

## Testing

- A red must be **logical**: an assertion failure, not an import, missing symbol, or compile error. Scaffold until it is logical and do not record the structural run.
- Test our logic, not framework wiring, trivial getters, or defaults.
- One behaviour per test; fakes at boundaries per repo convention.
- The user's explicit instruction outranks these rules, and these rules outrank any skill's checklist.
- pytest, ruff, pyright; `make` is the full check. Keep arrange / act / assert visually distinct.
- **Coverage gate:** `make coverage` measures branch coverage over the four package source roots and fails below 95%; `make test`, `make`, and pre-commit never judge the number. Never add blanket `# pragma: no cover` to move it, and a fifth package is not measured until added to `[tool.coverage.run].source`.

## Package dependency direction (strict)

```
web → simulation, domain, core
tools → domain, core   (never web; never simulation unless nested `AGENTS.md` says so)
simulation → domain, core
domain → core
core → stdlib + pydantic + sqlite
```

## Documentation policy

| Location | Role |
| -------- | ---- |
| Root / nested `AGENTS.md` | Rules for this repo or area, plus a pointer index |
| `docs/<topic>.md`, `packages/*/docs/<topic>.md` | Durable reference; read on demand |
| `.agents/specs/`, `.agents/plans/` | Local designs and plans — **never committed** |
| GitHub issues | Roadmap / larger-work tracking |

- Name specs `.agents/specs/YYYY-MM-DD-<topic>-design.md`; load one only while continuing that work.
- Durable docs state the conclusion; never cite a spec, plan, PR, or phase.
- No package reference file beside `docs/<topic>.md`, no `docs/features/` chain, no archive tree.
- Link every nested `AGENTS.md` and every `docs/<topic>.md` from the nearest parent `AGENTS.md`.

## Reference index

- Market data refresh, caches, and vendored series → `docs/market-data.md`
- Test fixtures and conftest layout → `docs/testing.md`
- Area guides → `packages/web/AGENTS.md` · `packages/simulation/AGENTS.md` · `packages/domain/AGENTS.md` · `tools/AGENTS.md`

## Hard guardrails

- NEVER commit `data/data.db` or personal plan data.
- NEVER modify config.yml — YAML workflow removed; legacy import is the import script only (`scripts/import_legacy_yaml.py`).
- NEVER modify files under `.github/workflows/` without explicit user confirmation.
- NEVER edit lockfiles by hand — use `uv add` / `uv sync`.
- NEVER import `web` from `tools/` or `simulation`.
- NEVER disable lint or type-check rules to pass CI — fix the underlying issue.

## Other Coding Preferences

- SHOULD use underscores to make large values human readable (ex: Decimal('1_000_000') instead of Decimal('1000000'))

### Complexity Reduction
- SHOULD avoid single line functions unless there's real risk of drift between call sites
- SHOULD require named parameters for functions with more than one argument
- SHOULD configure sensible defaults for arguments rather than making each caller have to do the work

### Performance
- SHOULD evaluate downstream consumers of O(n) operations to prevent O(n^2) performance, for example in calculated properties that zip/sum lists

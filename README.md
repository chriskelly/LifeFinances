# LifeFinances

Personal finances and retirement planning simulator — rebuilt 2026 with monthly TPAW modeling, SQLite, and a Python web UI.

**Legacy v1 (Flask + React):** tag [`legacy/v1-final`](https://github.com/chriskelly/LifeFinances/tree/legacy/v1-final) and mirror repo [life-finances-legacy](https://github.com/chriskelly/life-finances-legacy).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and **Python 3.14+**.

```bash
uv sync
uv run python scripts/init_db.py
```

Working database: `data/data.db` (gitignored). Schema template: `data/data.db.blank`.

Override DB path: `LIFE_FINANCES_DB_PATH=/path/to/data.db`

## Workspace packages

| Package | Role | Overview |
| ------- | ---- | -------- |
| `packages/core` | Plan model, SQLite persistence, path helpers | [`OVERVIEW.md`](packages/core/OVERVIEW.md) |
| `packages/domain` | SS, pension, job income, taxes | [`OVERVIEW.md`](packages/domain/OVERVIEW.md) |
| `packages/simulation` | Monthly TPAW engine | [`OVERVIEW.md`](packages/simulation/OVERVIEW.md) |
| `packages/web` | FastAPI + Jinja2 + HTMX UI (Phase 1+) | — |

`uv sync` installs all workspace packages via the root dev dependency group — no extra flags needed for local development or CI.

Dependency direction: `web → simulation → domain → core`. Tools import `core`/`domain`/`simulation` only, never `web`.

## Scripts

| Script | Purpose |
| ------ | ------- |
| `scripts/init_db.py` | Copy `data.db.blank` → working `data/data.db` (idempotent) |
| `scripts/create_blank_db.py` | Regenerate `data.db.blank` after schema changes |
| `scripts/db_inspect.py --plan <id>` | Print plan JSON from the working database |
| `scripts/import_legacy_yaml.py` | Legacy YAML import stub (Phase 4) |

## Development

```bash
make test    # pytest (root tests + all packages)
make lint    # ruff + pyright
make         # both
```

Agent conventions: [`AGENTS.md`](AGENTS.md). Active rebuild plans: [`docs/superpowers/plans/`](docs/superpowers/plans/).

## Troubleshooting

| Problem | Fix |
| ------- | --- |
| `ModuleNotFoundError: core` | Run `uv sync` from the repo root |
| `No database at …` from `db_inspect` | Run `uv run python scripts/init_db.py` |
| `Blank schema not found` | Ensure `data/data.db.blank` exists; regenerate with `uv run python scripts/create_blank_db.py` |
| Python version mismatch | Install Python 3.14+; `uv` will select it per `requires-python` |
| Tests pass locally but imports fail in IDE | Point the IDE at `.venv` and include `packages/` on `PYTHONPATH` |

## Backup

Copy `data/data.db` to back up plans. No in-app export in v1.

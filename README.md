# LifeFinances

Personal finances and retirement planning simulator — rebuilt 2026 with monthly TPAW modeling, SQLite, and a Python web UI.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+.

```bash
uv sync
uv run python scripts/init_db.py
uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Run all commands from the repository root.

Working database: `data/data.db` (gitignored). Schema template: `data/data.db.blank`.

Override DB path: `LIFE_FINANCES_DB_PATH=/path/to/data.db`

Disability insurance calculator (Marimo): `uv run marimo edit tools/disability_insurance.py` — see `tools/AGENTS.md`.

## Development

```bash
make test    # pytest
make lint    # ruff + pyright
make         # both
```

Agent conventions: `[AGENTS.md](AGENTS.md)`.

## Backup

Copy `data/data.db` to back up plans. No in-app export currently.



**Legacy v1 (Flask + React):** tag `[legacy/v1-final](https://github.com/chriskelly/LifeFinances/tree/legacy/v1-final)` and mirror repo [life-finances-legacy](https://github.com/chriskelly/life-finances-legacy).
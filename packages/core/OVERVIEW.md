# Core — Package Overview

Plan model, SQLite persistence, and repository path helpers. Phase 0 delivers the database schema and `paths` module; the `Plan` model and repository arrive in Phase 1.

## Public API (Phase 0)

### `core.paths`

| Function | Returns | Purpose |
| -------- | ------- | ------- |
| `repo_root()` | `Path` | LifeFinances repository root (four parents up from `core/paths.py`) |
| `default_blank_db_path()` | `Path` | `data/data.db.blank` — committed schema template |
| `default_db_path()` | `Path` | Working DB at `data/data.db`, or `LIFE_FINANCES_DB_PATH` override |

`LIFE_FINANCES_DB_PATH` accepts any absolute or `~`-expanded path. Scripts and tests use this to isolate databases without touching the working copy.

## SQLite schema

Committed in `data/data.db.blank`. Phase 0 has a single table:

```sql
CREATE TABLE plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    data TEXT NOT NULL,          -- JSON-serialized Plan (Phase 1+)
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

The `data` column stores plan configuration as JSON text. `db_inspect.py` parses it with `json.loads`.

## Bootstrap workflow

```bash
uv sync
uv run python scripts/init_db.py    # copy blank → data/data.db (idempotent)
```

| Script | When to run |
| ------ | ----------- |
| `scripts/init_db.py` | Fresh clone, CI, or after deleting `data/data.db` |
| `scripts/create_blank_db.py` | After changing `SCHEMA` in that script — regenerates `data/data.db.blank` |
| `scripts/db_inspect.py --plan <id>` | Debug plan JSON in the working database |

`init_db` copies the blank file; it does not run migrations. Schema changes require regenerating `data.db.blank` and re-running `init_db` (or deleting the working copy).

## Constraints

- Never commit `data/data.db` — it may contain personal plan data.
- `core` depends only on stdlib + Pydantic (no imports from `domain`, `simulation`, or `web`).
- Phase 1 adds `Plan` pydantic model and a SQLite repository in this package.

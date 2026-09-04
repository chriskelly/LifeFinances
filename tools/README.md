# Tools

Standalone Marimo apps. Run every command from the **repository root**.

## Disability insurance calculator

```bash
uv run marimo edit tools/disability_insurance.py
```

View-only: `uv run marimo run tools/disability_insurance.py`.

Needs a SQLite plan database at `data/data.db` (or `LIFE_FINANCES_DB_PATH`). If the file is missing or empty, run `uv run python scripts/init_db.py` and/or open the web app.

### Personal config (not committed)

1. Copy `tools/disability_insurance.local.toml.example` to `tools/disability_insurance.local.toml`.
2. Edit `plan_id` (omit it to use the app default plan) and `[person1]` / `[person2]`.
3. Do not commit `*.local.toml` — git ignores `tools/*.local.toml`.

`percentage` is on a 0–100+ scale: `60` means 60%, not `0.60`. Values over 100 are allowed; replacement is capped at 100% in the calculator. When `percentage` is greater than 0, set **only one** of `duration_years` or `age_limit`. When `percentage` is 0, omit both.

If `tools/disability_insurance.local.toml` is missing, the calculator uses zeros and the default plan. That is valid.

Agent / import rules: [AGENTS.md](AGENTS.md).

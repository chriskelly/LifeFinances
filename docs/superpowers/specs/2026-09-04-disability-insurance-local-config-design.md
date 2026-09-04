# Disability insurance — gitignored local config

**Date:** 2026-09-04  
**Status:** Approved

**Parent:** [2026-08-28-phase-5-tools-disability-insurance-design.md](./2026-08-28-phase-5-tools-disability-insurance-design.md)  
**Phase plan:** *(write after spec review)*

---

## 1. Goal

Keep personal calculator knobs (plan id, coverage, later extras) out of git while remaining easy to edit. The notebook stays a read-only consumer of SQLite; it does not persist coverage on `Plan`.

### In scope

- Gitignored `tools/disability_insurance.local.toml`
- Committed `tools/disability_insurance.local.toml.example`
- Notebook loads that file (or safe defaults if missing)
- Human `tools/README.md` with how to run and configure the calculator
- `tools/AGENTS.md` pointer to the local-file pattern
- `.gitignore`: `tools/*.local.toml`

### Out of scope

- Writing the local file from the notebook
- SQLite / `Plan` fields for coverage
- Marimo widgets
- Pytest of TOML parsing or gap math
- Other tools’ local files (the glob is shared so they can follow later)

---

## 2. Files

| Path | Git | Role |
| ---- | --- | ---- |
| `tools/disability_insurance.local.toml` | ignored | Personal values |
| `tools/disability_insurance.local.toml.example` | committed | Copy target; zeros / unset `plan_id` |
| `tools/README.md` | committed | Human run + config instructions |
| `tools/disability_insurance.py` | committed | Load TOML; no coverage / `PLAN_ID` literals |
| `.gitignore` | committed | `tools/*.local.toml` |

The notebook never writes the local file. Operator copies example → local once.

---

## 3. TOML schema

Filled **local** file the notebook **reads today** (not the committed example):

```toml
# Omit plan_id → AppSettings.default_plan_id
plan_id = 21

[person1]
percentage = 60
duration_years = 5
# age_limit = 65

[person2]
percentage = 50
age_limit = 100
# duration_years = 5
```

- `plan_id`: optional integer. Absent / omitted → same as today’s `PLAN_ID is None`.
- `percentage`: 0–100+ scale (`60` means 60%, not `0.60`).
- `duration_years` and `age_limit`: optional integers; XOR rules unchanged from Phase 5 §5.
- Missing `[person1]` / `[person2]`: treat as `percentage = 0` and both windows unset.
- **Unknown keys are ignored** (forward-compatible). Do not fail the cell for extras.

Committed example uses unset `plan_id` and both people `percentage = 0` with no window keys.

---

## 4. Notebook load and errors

Resolve path as `Path("tools/disability_insurance.local.toml")` from **repo root** (same cwd contract as the DB). Do not search `__file__` relatives that break when Marimo’s working directory is the repo root.

| Situation | Behavior |
| --------- | -------- |
| File missing | Use example defaults; status line says defaults (file not found) |
| Invalid TOML | `mo.stop` with a message to fix the file |
| Coverage XOR / percentage rules violated | Same `validate_coverage` failures as Phase 5 |
| `plan_id` set but not in `list()` | Same stop as a bad `PLAN_ID` today |

Drop Python assignments for `PLAN_ID` and the six coverage literals so personal numbers cannot land in a notebook commit.

Status cell: which source (local file vs defaults), resolved plan id, and a one-line coverage summary — not the full report.

Still: `core` + `domain` + `marimo` only; `tomllib` (stdlib). Never `web` / `simulation`. Never `PlanRepository.save`.

---

## 5. Human README (`tools/README.md`)

Audience: a person using the calculator, not an agent. Cover:

1. Run from repo root: `uv run marimo edit tools/disability_insurance.py` (optional `marimo run` for view-only).
2. Needs `data/data.db` (or `LIFE_FINANCES_DB_PATH`); `uv run python scripts/init_db.py` / web app if empty.
3. Copy `disability_insurance.local.toml.example` → `disability_insurance.local.toml`.
4. Edit `plan_id` and `[person1]` / `[person2]`; do not commit `*.local.toml`.
5. Percentage and XOR window rules in plain language (pointer that 60 means 60%).
6. Missing local file is valid (zeros + default plan).
7. Link to `AGENTS.md` for import / read-only DB rules.

Keep it short. Do not duplicate gap formulas.

---

## 6. Agent docs

`tools/AGENTS.md`: local TOML pattern, gitignore glob, never commit `*.local.toml`, still no Plan persistence.

Root `README.md`: one extra phrase that config lives in gitignored `tools/*.local.toml` if the existing calculator line would otherwise tell people to edit the `.py`.

---

## 7. Testing

No pytest. `uv run marimo check tools/disability_insurance.py` and `make` still pass. Do not add a Marimo execute step to CI.

---

## 8. Exit criteria

- [ ] Local TOML gitignored; example committed
- [ ] Notebook has no personal coverage / plan-id literals
- [ ] Missing file → defaults; invalid TOML / XOR → stop with a clear message
- [ ] `tools/README.md` explains run + copy/edit local config
- [ ] `make` still passes

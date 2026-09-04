# Disability insurance local TOML Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Personal plan id and coverage live in gitignored `tools/disability_insurance.local.toml`; the notebook and a human `tools/README.md` explain copy/edit without committing numbers.

**Architecture:** Stdlib `tomllib` reads `Path("tools/disability_insurance.local.toml")` from repo root. Missing file → zeros and unset `plan_id` (same as today’s `PLAN_ID is None`). Invalid TOML or XOR rules stop the notebook. The notebook never writes the file.

**Tech Stack:** Python 3.14+ `tomllib`, Marimo notebook, existing `validate_coverage`, `PlanRepository` / `SettingsRepository`.

**Design spec:** `docs/superpowers/specs/2026-09-04-disability-insurance-local-config-design.md`

**Branch:** continue `feat/phase-5-disability-insurance-design`.

## Global Constraints

- Run all commands from the **repository root**.
- Notebook imports: `marimo`, `core`, `domain`, stdlib. Never `web`. Never `simulation`.
- Do not call `PlanRepository.save`, `create`, `ensure_bootstrap`, or `get_or_create_default`.
- Coverage `percentage` is on a 0–100+ scale (`60` means 60%, not `0.60`).
- Unknown TOML keys are ignored.
- Path is `tools/disability_insurance.local.toml` (cwd), not `__file__`.
- The notebook never writes the local file.
- No pytest for TOML parsing or gap math. Do not add a Marimo execute step to `make test`.
- `make` must still pass.
- Do not persist coverage on `Plan`. Do not commit `tools/*.local.toml` or `tools/__marimo__/`.

---

## File Structure

| File | Responsibility |
| ---- | -------------- |
| Modify: `.gitignore` | Add `tools/*.local.toml` |
| Create: `tools/disability_insurance.local.toml.example` | Committed zeros / unset `plan_id` |
| Modify: `tools/disability_insurance.py` | Load TOML; drop `PLAN_ID` and coverage literals |
| Create: `tools/README.md` | Human run + config |
| Modify: `tools/AGENTS.md` | Local-file pattern for agents |
| Modify: `README.md` | Point at gitignored local TOML / `tools/README.md` |
| Modify: spec header | Link this plan |

---

### Task 1: Gitignore, example TOML, notebook load

**Files:**
- Modify: `.gitignore`
- Create: `tools/disability_insurance.local.toml.example`
- Modify: `tools/disability_insurance.py`

**Interfaces:**
- Consumes: existing `validate_coverage`, plan list / `get_by_id` / `settings.default_plan_id`
- Produces: `PLAN_ID: int | None` from TOML `plan_id` (or `None`); `PERSON1_*` / `PERSON2_*` from `[person1]` / `[person2]`; `config_source: str`

- [ ] **Step 1: Gitignore**

In `.gitignore`, under the LifeFinances Specific block (after `config.yml`), add:

```
# Personal Marimo tool knobs (keep *.example committed)
tools/*.local.toml
```

- [ ] **Step 2: Example TOML**

Create `tools/disability_insurance.local.toml.example` with **exactly**:

```toml
# Copy to disability_insurance.local.toml and edit. Do not commit the copy.
# Omit plan_id to use the app default plan.
# percentage: 60 means 60%. When percentage > 0, set only one of duration_years or age_limit.

[person1]
percentage = 0

[person2]
percentage = 0
```

No `plan_id` key. No `duration_years` / `age_limit` keys.

- [ ] **Step 3: Imports cell**

In the first cell of `tools/disability_insurance.py`, add:

```python
import tomllib
from pathlib import Path
```

Return `Path` and `tomllib` from that cell (Marimo needs them if later cells import from this cell — load logic lives in the config cell, so only that cell needs the imports). Prefer putting `tomllib` / `Path` in the **config cell** that loads the file so the first cell stays package imports only.

- [ ] **Step 4: Replace plan-id cell and coverage cell**

Replace the cell that assigns `PLAN_ID: int | None = None` and the cell that assigns the six `PERSON*` literals with the following two cells (keep the plans-list cell unchanged). Load config **before** resolving the plan.

**Config cell** (after plans list, before `get_by_id`):

```python
@app.cell
def _(Decimal, mo, summaries):
    import tomllib
    from pathlib import Path

    LOCAL_CONFIG_PATH = Path("tools/disability_insurance.local.toml")

    def optional_int(table: object, key: str) -> int | None:
        if not isinstance(table, dict) or key not in table:
            return None
        value = table[key]
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be an integer")
        return value

    def person_from_table(raw: object) -> tuple[Decimal, int | None, int | None]:
        if raw is None:
            return Decimal(0), None, None
        if not isinstance(raw, dict):
            raise ValueError("person1/person2 must be TOML tables")
        percentage_raw = raw.get("percentage", 0)
        if isinstance(percentage_raw, bool) or not isinstance(
            percentage_raw, (int, float)
        ):
            raise ValueError("percentage must be a number")
        return (
            Decimal(str(percentage_raw)),
            optional_int(raw, "duration_years"),
            optional_int(raw, "age_limit"),
        )

    def validate_coverage(
        *,
        percentage: Decimal,
        duration_years: int | None,
        age_limit: int | None,
        label: str,
    ) -> None:
        has_duration = duration_years is not None
        has_age = age_limit is not None
        if has_duration and has_age:
            raise ValueError(f"{label}: set only one of duration_years or age_limit")
        if percentage > 0:
            if not has_duration and not has_age:
                raise ValueError(
                    f"{label}: when percentage > 0, set duration_years or age_limit"
                )
            if has_duration and duration_years is not None and duration_years <= 0:
                raise ValueError(f"{label}: duration_years must be positive")
        elif has_duration or has_age:
            raise ValueError(
                f"{label}: when percentage is 0, omit duration_years and age_limit"
            )

    data: dict = {}
    config_source = "defaults (file not found)"
    if LOCAL_CONFIG_PATH.exists():
        try:
            data = tomllib.loads(LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            mo.stop(
                True,
                mo.md(f"Invalid TOML in `{LOCAL_CONFIG_PATH}`: {exc}"),
            )
        if not isinstance(data, dict):
            mo.stop(True, mo.md(f"`{LOCAL_CONFIG_PATH}` must be a TOML table."))
        config_source = str(LOCAL_CONFIG_PATH)

    try:
        PLAN_ID = optional_int(data, "plan_id")
        PERSON1_PERCENTAGE, PERSON1_DURATION_YEARS, PERSON1_AGE_LIMIT = (
            person_from_table(data.get("person1"))
        )
        PERSON2_PERCENTAGE, PERSON2_DURATION_YEARS, PERSON2_AGE_LIMIT = (
            person_from_table(data.get("person2"))
        )
        validate_coverage(
            percentage=PERSON1_PERCENTAGE,
            duration_years=PERSON1_DURATION_YEARS,
            age_limit=PERSON1_AGE_LIMIT,
            label="person1",
        )
        validate_coverage(
            percentage=PERSON2_PERCENTAGE,
            duration_years=PERSON2_DURATION_YEARS,
            age_limit=PERSON2_AGE_LIMIT,
            label="person2",
        )
    except ValueError as exc:
        mo.stop(True, mo.md(str(exc)))

    mo.md(
        f"Config: `{config_source}`. "
        f"plan_id={PLAN_ID!s}. "
        f"person1 {PERSON1_PERCENTAGE}% "
        f"(duration_years={PERSON1_DURATION_YEARS!s}, age_limit={PERSON1_AGE_LIMIT!s}); "
        f"person2 {PERSON2_PERCENTAGE}% "
        f"(duration_years={PERSON2_DURATION_YEARS!s}, age_limit={PERSON2_AGE_LIMIT!s}). "
        "Not saved to the plan."
    )
    return (
        PLAN_ID,
        PERSON1_AGE_LIMIT,
        PERSON1_DURATION_YEARS,
        PERSON1_PERCENTAGE,
        PERSON2_AGE_LIMIT,
        PERSON2_DURATION_YEARS,
        PERSON2_PERCENTAGE,
    )
```

**Plan cell** — keep resolution the same, but `PLAN_ID` comes from the config cell (no `PLAN_ID = None` assignment). Change the stop copy from “Set `PLAN_ID`…” to:

```python
            "Set `plan_id` in `tools/disability_insurance.local.toml` "
            "to an id from the list above (default plan is missing or invalid)."
```

Do **not** leave `PERSON1_PERCENTAGE = Decimal("60")` or any other personal literals in the `.py`.

- [ ] **Step 5: Verify**

```bash
uv run marimo check tools/disability_insurance.py
uv run ruff check tools/disability_insurance.py && uv run ruff format tools/disability_insurance.py
rg -n "PLAN_ID: int|PERSON1_PERCENTAGE = Decimal|PERSON2_PERCENTAGE = Decimal" tools/disability_insurance.py
```

Expected: marimo check and ruff clean; `rg` finds **no** coverage/plan literals (config cell may still *name* `PLAN_ID` as a loaded variable — that is fine; it must not assign a numeric coverage default other than `Decimal(0)` inside `person_from_table`).

Confirm `.gitignore` matches `tools/disability_insurance.local.toml` (`git check-ignore -v tools/disability_insurance.local.toml`).

- [ ] **Step 6: Commit**

```bash
git add .gitignore tools/disability_insurance.local.toml.example tools/disability_insurance.py
git commit -m "$(cat <<'EOF'
feat(tools): load disability knobs from gitignored local TOML

Keep personal plan id and coverage out of the notebook so they cannot be committed by accident.
EOF
)"
```

Do not `git add` `tools/disability_insurance.local.toml` or `tools/__marimo__/`.

---

### Task 2: Human README, agent/root docs, `make`

**Files:**
- Create: `tools/README.md`
- Modify: `tools/AGENTS.md`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-09-04-disability-insurance-local-config-design.md`

**Interfaces:**
- Consumes: Task 1 paths and copy/edit workflow
- Produces: human + agent instructions; spec **Phase plan** link

- [ ] **Step 1: `tools/README.md`**

Write this file (inner commands are fenced with triple backticks in the real README):

~~~~markdown
# Tools

Standalone Marimo apps. Run every command from the **repository root**.

## Disability insurance calculator

```bash
uv run marimo edit tools/disability_insurance.py
```

View-only: `uv run marimo run tools/disability_insurance.py`.

Needs a SQLite plan database at `data/data.db` (or `LIFE_FINANCES_DB_PATH`). If the file is missing or empty, run `uv run python scripts/init_db.py` and/or open the web app.

### Personal config (not committed)

1. Copy `disability_insurance.local.toml.example` to `disability_insurance.local.toml`.
2. Edit `plan_id` (omit it to use the app default plan) and `[person1]` / `[person2]`.
3. Do not commit `*.local.toml` — git ignores `tools/*.local.toml`.

`percentage` is on a 0–100 scale: `60` means 60%, not `0.60`. When `percentage` is greater than 0, set **only one** of `duration_years` or `age_limit`. When `percentage` is 0, omit both.

If `disability_insurance.local.toml` is missing, the calculator uses zeros and the default plan. That is valid.

Agent / import rules: [AGENTS.md](AGENTS.md).
~~~~

- [ ] **Step 2: `tools/AGENTS.md`**

Replace the bullet:

`- Coverage and other tool inputs stay in the notebook. Do not add fields to \`Plan\` for a tool unless a later spec says so.`

with:

```markdown
- Coverage and other tool knobs live in gitignored `tools/<name>.local.toml` (committed `*.local.toml.example`). Do not add fields to `Plan` for a tool unless a later spec says so. Never commit `tools/*.local.toml`.
```

In **Adding a tool**, add step 4:

```markdown
4. If the tool has personal knobs, add `tools/<name>.local.toml.example` and load `tools/<name>.local.toml` (ignored by `tools/*.local.toml`).
```

Keep the rest of the file.

- [ ] **Step 3: Root `README.md`**

Replace:

`Disability insurance calculator (Marimo): \`uv run marimo edit tools/disability_insurance.py\` — see \`tools/AGENTS.md\`.`

with:

`Disability insurance calculator (Marimo): \`uv run marimo edit tools/disability_insurance.py\` — personal knobs in gitignored \`tools/*.local.toml\`; see \`tools/README.md\`.`

- [ ] **Step 4: Spec header**

In `docs/superpowers/specs/2026-09-04-disability-insurance-local-config-design.md`, replace:

`**Phase plan:** *(write after spec review)*`

with:

`**Phase plan:** [\`2026-09-04-disability-insurance-local-config.md\`](../plans/2026-09-04-disability-insurance-local-config.md)`

- [ ] **Step 5: `make`**

```bash
make
```

Expected: pytest, ruff, pyright pass.

- [ ] **Step 6: Commit**

```bash
git add tools/README.md tools/AGENTS.md README.md docs/superpowers/specs/2026-09-04-disability-insurance-local-config-design.md docs/superpowers/plans/2026-09-04-disability-insurance-local-config.md
git commit -m "$(cat <<'EOF'
docs(tools): human README and local TOML instructions

Operators should copy the example file, not edit coverage literals in the notebook.
EOF
)"
```

Include this plan file in that commit if it is still untracked.

---

## Spec coverage

| Spec | Task |
| ---- | ---- |
| `tools/*.local.toml` gitignore | 1 |
| Example TOML zeros / unset plan_id | 1 |
| Load from repo-root path; missing → defaults | 1 |
| Invalid TOML / XOR → stop | 1 |
| No personal literals in `.py` | 1 |
| Status line source + plan_id + coverage | 1 |
| `tools/README.md` | 2 |
| `tools/AGENTS.md` + root README | 2 |
| No pytest / no `make test` Marimo | global |
| No Plan persistence / no notebook write | global |

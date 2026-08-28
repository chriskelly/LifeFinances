# Phase 5 — Tools: Disability Insurance Calculator Design

**Date:** 2026-08-28  
**Status:** Approved

**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md) §5, Phase 5  
**Legacy behavior:** `life-finances-legacy` notebook `backend/standalone_tools/disability_insurance_calculator.ipynb` and feature spec under `docs/features/disability-insurance-calculator/`  
**Phase plan:** `2026-06-12-phase-5-tools-disability-insurance.md` *(to write)*  
**Index:** Phase 5 in [2026-06-12-rebuild-index.md](../plans/2026-06-12-rebuild-index.md)

---

## 1. Goal & scope

Ship a Marimo app that proves standalone tools can consume shared packages without `web`. The app is a full-parity port of the legacy disability-insurance coverage-gap calculator: lost job income plus knock-on Social Security and pension, after-tax employer coverage, remaining gap as **% of income for X years**.

### In scope

- `tools/disability_insurance.py` (Marimo), run via `uv run marimo edit tools/disability_insurance.py` from repo root
- Load a named plan from SQLite; default to `AppSettings.default_plan_id` when no plan id is set
- Tool-only coverage inputs (not on `Plan`, not saved)
- Baseline vs disability via `domain.build_monthly_cashflows` (clone plan, clear that person’s `jobs`)
- Person 1 always; person 2 when `household.person2` is not `None`
- Structured text report matching legacy’s three-part output
- `tools/AGENTS.md` documenting how to add another tool
- Marimo as a root **dev** dependency

### Out of scope

- Persisting `DisabilityCoverage` on `Plan` or a web editor for it
- YAML import of coverage (Phase 4f); 4f must document this gap if YAML still has those keys
- TPAW / Monte Carlo / portfolio / spending in the gap
- `simulation` package (unless implementation discovers a nominal stream that cashflows do not already express in plan dollars — then stop and add a scalar, do not silently switch to TPAW)
- Extracting gap math into `domain` or a tested library
- Pytest of the gap formula; `make test` does not execute Marimo
- Additional Marimo apps beyond this calculator
- Creating or writing plans from the tool (`repo.save` is forbidden)

---

## 2. Decisions captured from brainstorming

| # | Decision | Choice |
| - | -------- | ------ |
| 1 | Success bar | Full legacy parity (outputs and edge cases), not a thinner demo |
| 2 | Coverage storage | Tool-only literals in the notebook; never on `Plan` |
| 3 | Plan source | Named plan from SQLite (`PlanRepository`); same DB as the web app |
| 4 | Unset plan id | Use `SettingsRepository.get().default_plan_id` (same default as `/`) |
| 5 | Income engine | `domain.build_monthly_cashflows` only |
| 6 | Where math lives | Marimo cells (legacy testing exemption); no unit tests of the gap formula |
| 7 | UX | Linear notebook (edit cells, run top to bottom), not reactive widgets |
| 8 | Layout | Single file `tools/disability_insurance.py`; marimo in the root `dev` group — not a `tools` uv package, not a CLI dual entry point |

---

## 3. Architecture

```
SQLite (LIFE_FINANCES_DB_PATH / data/data.db)
    → PlanRepository + SettingsRepository (core)
    → deepcopy Plan
    → person.jobs = []
    → build_monthly_cashflows × 2 (domain)
    → gap arithmetic in notebook cells
    → printed report
```

| Unit | Does | Depends on |
| ---- | ---- | ---------- |
| `tools/disability_insurance.py` | Load plan, coverage literals, clone/zero jobs, compare cashflows, print report | `core` (`Plan`, repositories, paths), `domain` (`build_monthly_cashflows`, `project_job_income`, `Timeline`) |
| `tools/AGENTS.md` | Run command, import rule, test exemption, how to add a tool | — |

**Import rule:** `core` and `domain` only. Never `web`. Do not import `simulation` in this phase.

**Process:** Read-only. Do not call `PlanRepository.save`, `create`, `ensure_bootstrap`, or `get_or_create_default` (those can write). Loading uses `list` / `get_by_id` and `SettingsRepository.get`.

---

## 4. Notebook cell sequence

Cells are sequential. Coverage and `PLAN_ID` are Python assignments the user edits, not Marimo UI widgets.

1. **Imports and DB** — `PlanRepository()` / `SettingsRepository()` using `default_db_path()` (honors `LIFE_FINANCES_DB_PATH`).
2. **List plans** — print `id` and `name` from `repo.list()`.
3. **Choose plan** — `PLAN_ID: int | None = None`. Resolution:
   - If `PLAN_ID` is an `int`, load that id.
   - If `PLAN_ID` is `None`, load `settings.default_plan_id`.
   - If the chosen id is missing or `default_plan_id` is `None` / not in `list()`, **stop** with a message to set `PLAN_ID` from the printed list. Do not create a plan.
   - If the DB file is missing or `list()` is empty, **stop** and tell the user to run `uv run python scripts/init_db.py` and/or open the web app.
4. **Coverage literals** — one block per person (see §5). Partner block is unused when `person2` is `None`.
5. **Baseline** — `baseline = build_monthly_cashflows(plan)` (inject `today` only if other domain call sites in the notebook need a pinned date; default `today=None` matches production).
6. **Person-1 disability** — `disabled = deepcopy(plan)`; `disabled.household.person1.jobs = []`; rebuild cashflows; compute needs, employer replacement, gap; print.
7. **Person-2 disability** — if `person2` is not `None`, same with `person2.jobs = []` (person 1’s jobs unchanged). Skip this cell’s calculations when there is no partner.
8. **Household empty-income guard** — if neither person has any future job income (see §6), print that disability insurance is not needed and skip gap formulas.

Manual income streams and the other person’s jobs stay on the disability clone. Formula pensions attached to the disabled person’s jobs disappear with those jobs (correct knock-on). Household-level manual pension / manual income is unchanged in both runs.

---

## 5. Coverage inputs (not persisted)

Notebook-local values, same meaning as legacy `DisabilityCoverage` (percentage on a **0–100+** scale: `60` means 60%, not `0.60`).

| Field | Meaning |
| ----- | ------- |
| `percentage` | Employer coverage share of current annual income. `0` = none. Values `> 100` are allowed; replacement uses `min(percentage, 100)`. |
| `duration_years` | Benefit period in whole years from timeline start (`Timeline` month 0). Mutually exclusive with `age_limit`. |
| `age_limit` | Benefits until the insured’s age in whole years. Mutually exclusive with `duration_years`. |

Rules (fail the cell with a clear `ValueError` / printed message, do not invent a default duration):

- At most one of `duration_years` or `age_limit`.
- If `percentage > 0`, exactly one of them; `duration_years` must be `> 0` if used.
- If `percentage == 0`, both must be unset (`None`).

**Policy window** (capped at `horizon_months`):

- `duration_years`: months `0` through `duration_years * 12 - 1` inclusive.
- `age_limit`: months where the insured’s completed whole-year age is **`< age_limit`** (benefits until they *reach* that age, not including age `age_limit` and after). Use `Timeline` + birth month/year, same as other age boundaries.

Covered month count `N` is the size of that window after capping.

**Years until policy end** for the gap % denominator is `N / 12`. If `N == 0`, skip the % formula and report that the coverage window is empty.

---

## 6. Gap formulas

Let `net(c)` = `sum(c.net_cashflow)` for a `MonthlyCashflows` result. Domain `net_cashflow` is already `(job + SS + pension + manual) + taxes` with taxes stored as negatives.

**Replacement need** (per disabled person):

`need = net(baseline) - net(disability)`

Also print lifetime **gross** deltas for job, SS, and pension (`sum(gross_*)`) so SS/pension knock-on is visible. Needs include **post-policy-end** SS/pension differences because both cashflow series run to the full horizon.

**No insurance needed** (skip gap for that person, print the legacy-style explanation):

- That person’s `project_job_income` series is all zeros (already retired / no jobs), or
- Household: both people have all-zero job series — print once and skip both gap blocks.

**Current annual income** (gap % denominator and employer benefit base):

- `jobs = project_job_income(plan, Timeline(plan))` on the **baseline** plan.
- Take that person’s `PersonJobIncome.gross`.
- First month index `i` with `gross[i] > 0` (sabbatical-at-start). If none, that person has no insurance need.
- `current_annual_income = gross[i] * 12`.

Do not use household `MonthlyCashflows.gross_job` for this (it mixes both earners).

**Average tax rate** for taxable employer benefits, matching legacy FR-007 (ordinary income tax + Medicare on earning months; **not** Social Security FICA):

- Earning months: baseline `gross_job[m] > 0` (household job, same as legacy “earning quarters”).
- `avg_tax_rate = -sum(federal_income + state_income + fica_medicare) / sum(gross_job)` on those months.
- If the denominator is 0, `avg_tax_rate = 0`.

**Employer replacement** over covered months `N`, with `pct = min(percentage, 100) / 100`:

- `gross_benefits = (current_annual_income / 12) * pct * N`
- `taxes = gross_benefits * avg_tax_rate`
- `net_replacement = gross_benefits - taxes`
- If `percentage == 0` or `current_annual_income <= 0`: all three are 0.

**Gap:**

- `coverage_gap = max(0, need - net_replacement)`
- `benefit_percent = (coverage_gap / years_until_policy_end) / current_annual_income * 100` when `years_until_policy_end > 0` and `current_annual_income > 0`
- If `coverage_gap == 0`, report that no additional coverage is needed (do not recommend a negative %).

Units: plan dollars (same as cashflows). Format the printed report with thousands separators; do not rescale by the legacy notebook’s `* 1000` (that was YAML-in-thousands).

---

## 7. Printed report

For each person who is analyzed, print:

1. **Total income replacement needed** — `need`, plus a short breakdown of job / SS / pension lifetime gross deltas and baseline vs disability post-tax lifetime `net`.
2. **Existing coverage replacement (after taxes)** — gross benefits, taxes, net; note that workplace DI is treated as taxable; note the 100% cap if the user entered `percentage > 100`.
3. **Remaining coverage gap** — dollar gap and, when additional coverage is needed, **`{benefit_percent:.0f}% of income for {years} years`** (years = years until policy end, same window as employer benefits).

Explanatory notes: secondary SS/pension effects are included for the full horizon; employer benefits only until policy end.

---

## 8. Errors and tooling

| Situation | Behavior |
| --------- | -------- |
| Missing DB or no plans | Stop; point at `scripts/init_db.py` / web app |
| Bad / unset default plan id | Stop; print `list()` ids |
| Coverage XOR rules violated | Fail that cell with a clear message |
| Marimo traceback | Leave as-is; no HTTP error page |

**Dependency:** `uv add --dev marimo` at the workspace root (never hand-edit the lockfile).

**Lint:** Prefer treating `tools/*.py` as normal Python (`# %%` cells). If ruff or pyright cannot parse Marimo, exclude `tools/` from those checkers only — do not weaken rules for `packages/`.

**Tests:** No pytest for this notebook. `make test` / `make lint` must still pass for the rest of the repo. Do not add a Marimo execute step to CI in this phase.

**Docs:**

- `tools/AGENTS.md`: run command, `core`/`domain` only, never `web`, read-only DB, test exemption, “add a new `tools/<name>.py`” recipe.
- Root `AGENTS.md` and `README.md`: one-line pointer to the calculator.
- Rebuild index: mark Phase 5 design; exit criteria as in §9; replace “uses domain + simulation” with “uses `core` + `domain`” for this tool.

---

## 9. Exit criteria

- [ ] `tools/disability_insurance.py` runs via `uv run marimo edit tools/disability_insurance.py`
- [ ] Loads the default plan when `PLAN_ID is None` and `default_plan_id` is valid
- [ ] Uses `core` + `domain`; no `web` import; no `simulation` import
- [ ] Report covers replacement need, after-tax employer coverage, and gap as % of income for X years, for person 1 and person 2 when present
- [ ] `tools/AGENTS.md` documents adding new tools
- [ ] `make` still passes (notebook not required to be executed by `make`)

---

## 10. Testing policy (explicit exemption)

Application packages remain TDD. This notebook is a standalone tool, not imported by `web`, `domain`, or `simulation`. Gap arithmetic is specified here for implementers and for future extraction; Phase 5 does **not** add tests that only re-encode these formulas.

# LifeFinances Rebuild — Architecture Design

**Date:** 2026-06-12  
**Status:** Approved (architecture + parity workshop)  
**Scope:** Greenfield rebuild in `chriskelly/LifeFinances`; legacy archived to `life-finances-legacy`

---

## 1. Goals

- **AI-first development** via directory-scoped `AGENTS.md` and selective `OVERVIEW.md` files
- **Monthly modeling** (not quarterly)
- **Python only** — single-process web app (no separate frontend/backend API)
- **Modern tooling** — uv workspace, no dev containers
- **UI-managed configuration** — no YAML workflow; SQLite source of truth
- **Managed AI artifacts** — no living spec/plan chains; archive stale docs
- **Modular standalone tools** — shared packages + Marimo labs
- **TPAW modeling** — replace Monte Carlo success-rate simulation with Total Portfolio and Withdrawal modeling (tpaw reference)
- **Primary outcome:** current and expected spending; retirement is implicit (job income ends), not a system state

---

## 2. Repository and migration

### Same repo, clean cutover

| Action | Detail |
|--------|--------|
| Active repo | `chriskelly/LifeFinances` (preserve history and stars) |
| Archive repo | `life-finances-legacy` — one-time mirror of pre-rebuild state |
| Tag | `legacy/v1-final` on last legacy commit |
| Optional branch | `legacy` pointing at same commit |
| `main` | Replaced with new uv workspace tree |

README note: rebuilt 2026; pre-rebuild code at tag `legacy/v1-final` and `life-finances-legacy`.

### New workspace layout

```
LifeFinances/
├── AGENTS.md
├── pyproject.toml                 # uv workspace root
├── packages/
│   ├── core/                      # Plan model, SQLite persistence
│   ├── domain/                    # SS, pension, job income, taxes
│   ├── simulation/                # Monthly TPAW engine
│   └── web/                       # FastAPI + Jinja + HTMX
├── tools/                         # Marimo apps
├── data/
│   ├── data.db.blank              # committed empty schema
│   └── data.db                    # gitignored working copy
├── scripts/
│   ├── init_db.py
│   ├── db_inspect.py
│   └── import_legacy_yaml.py
└── archive/                       # frozen legacy docs (agents: ignore)
```

### Package dependency direction (strict)

```
web → simulation, domain, core
tools → simulation, domain, core   (never import web)
simulation → domain, core
domain → core
core → stdlib + pydantic + sqlite
```

---

## 3. Simulation architecture

### Time model

- Native unit: **one month** (`month_index`; ages in months)
- **Dated plans:** birth year + calendar dates; simulation **starts from today** forward
- **End age:** user-configurable **per person**; default **100**
- No system-level “retirement” state

### Two-layer design

**Domain (`packages/domain`)** — ported legacy logic producing **unified timed income streams** and tax-adjusted cashflows:

- Job income (ends at configured date → implicit retirement)
- Social Security (auto-generated, user-configurable)
- Pension (formula types e.g. admin DB + manual streams)
- Manual income streams (annuities, rental, etc.)
- Income-side taxes only (no withdrawal/capital-gains taxes in v1)

**Simulation (`packages/simulation`)** — TPAW engine (tpaw concepts ported to Python):

- Percentile bands (user-configurable)
- Block-bootstrap monthly returns (tpaw historical data)
- Block-bootstrap or suggested/manual inflation (see parity)
- TPAW withdrawal method only
- RRA-driven total-portfolio stock allocation (savings + PV of future income)
- Monthly rebalancing
- Separate planning expected returns/volatility for PV and allocation

### Cashflow accounting (no future savings)

Portfolio grows each month from:

```
surplus = income − taxes − spending
```

No separate contribution streams (tpaw “future savings” skipped). Surplus accumulates; deficit draws from portfolio.

### Account structure (v1)

- Single savings portfolio, stock/bond split
- Total portfolio = savings + PV of future income
- **Deferred:** taxable / tax-deferred / Roth buckets — schema designed for later addition

### Public API

```python
def run_simulation(plan: Plan, *, percentiles: list[int]) -> SimulationResult:
    cashflows = domain.build_monthly_cashflows(plan)
    processed = preprocess(plan, cashflows, percentiles)
    return simulate_monthly(processed)
```

---

## 4. Web app, config, and SQLite

### Stack

- **FastAPI** + **Jinja2** + **HTMX**
- Single process; simulation in-process
- Charts: server-rendered HTML/SVG (Plotly embed, Altair SVG, or similar)

### UI layout — TPAW-style split pane

```
┌─────────────────────────────────────────────────────────────┐
│  LifeFinances          [Plan: My Plan ▾]  [New] [Duplicate] │
├──────────────────────────┬──────────────────────────────────┤
│   PLAN EDITOR (left)     │   RESULTS (right)                │
│   Scrollable sections    │   Auto-updates on plan change    │
│                          │   (debounced ~500–1000ms)        │
└──────────────────────────┴──────────────────────────────────┘
```

Routes (fragments via HTMX):

| Route | Purpose |
|-------|---------|
| `/` | Split-pane shell |
| `/plans` | Plan list / create / switch |
| `/editor/{section}` | Editor section partial |
| `/results` | Results partial (runs simulation) |

### Database

| File | Git | Purpose |
|------|-----|---------|
| `data/data.db.blank` | Yes | Empty schema (+ optional non-personal example plan) |
| `data/data.db` | No | Developer working DB |

Bootstrap:

```bash
uv run python scripts/init_db.py   # copies blank → data.db if missing
```

Override path: `LIFE_FINANCES_DB_PATH` env var.

**No in-app export.** Backup via copying `data/data.db` (documented in README/AGENTS.md).

### Plan persistence

- `Plan` Pydantic model in `packages/core`
- v1: JSON blob per plan in SQLite
- Optional `plan_versions` later

---

## 5. Tools and agent documentation

### Standalone tools

- **Marimo** apps in `tools/` (e.g. disability insurance calculator)
- Import `core`, `domain`, `simulation` — never `web`
- Load plans from SQLite or inline parameters for what-if analysis

### AI artifacts (C′ policy)

| Location | Role |
|----------|------|
| Root + package `AGENTS.md` | Commands, boundaries, guardrails |
| `packages/simulation/OVERVIEW.md` | TPAW parity backlog + non-obvious decisions |
| `packages/domain/OVERVIEW.md` | Ported legacy modules map |
| `archive/` | Frozen pre-rebuild docs — agents ignore unless asked |

No `docs/features/.../Development/plan.md` chains in the new tree.

### Agent DB inspection

```bash
sqlite3 data/data.db ".schema"
uv run python scripts/db_inspect.py --plan 1
```

---

## 6. TPAW parity decisions

Decided in parity workshop (2026-06-12). Status: `keep` unless noted.

| # | Feature | Stance | Notes |
|---|---------|--------|-------|
| 1 | Withdrawal methods | **keep** | TPAW only |
| 2 | Spending structure | **keep** | Base target + timed extra essential/discretionary |
| 3 | Spending adjustments | **keep** | Spending tilt only; no floor/ceiling |
| 4 | Total portfolio allocation | **keep** | Full RRA on total portfolio incl. PV of future income |
| 5 | Percentile output | **keep** | User-configurable percentile bands |
| 6 | Return path generation | **keep** | Block-bootstrap; Python port; no CUDA v1 |
| 7 | Inflation (default) | **keep** | Block-bootstrap from historical data |
| 8 | Account structure | **keep + defer** | Single savings portfolio v1; schema ready for tax buckets |
| 9 | Taxes | **keep** | Income-side only |
| 10 | Household | **keep** | Two-person (user + partner) |
| 11 | Social Security | **keep** | Port legacy module; auto-generated configurable streams |
| 12 | Pension | **keep** | Formula types (e.g. admin DB) + manual streams |
| 13 | Job income | **keep** | Port legacy module |
| 14 | Future savings | **skip** | Portfolio grows via income − taxes − spending |
| 15 | Annuities | **skip** | Manual timed income streams |
| 16 | Plan time basis | **keep** | Dated plans (birth year + calendar) |
| 17 | Income modeling | **keep** | Unified timed streams; no pre/post retirement split |
| 18 | Spending over time | **keep** | Base target + extra timed streams + tilt |
| 19 | External spending | **skip** | All spending portfolio-funded |
| 20 | External wealth | **skip** | Total portfolio = savings + PV income only |
| 21 | Risk tolerance | **keep** | Full tpaw RRA: at-20, delta to max age, time preference |
| 22 | Market data | **keep** | Port tpaw historical monthly data |
| 23 | Sampling config | **keep** | tpaw defaults in UI; advanced overrides |
| 24 | Results charts | **keep** | Full tpaw major chart types |
| 25 | Multiple plans | **keep + defer** | Named plans v1; comparison view later |
| 26 | Planning returns | **keep** | Split: bootstrap paths vs planning expected returns/vol |
| 27 | Inflation override | **keep** | Suggested preset or manual fixed rate (alt. to bootstrap) |
| 28 | Legacy YAML import | **keep** | One-time `import_legacy_yaml.py`; documented gaps |
| 29 | Rebalancing | **keep** | Monthly |
| 30 | Simulation horizon | **keep** | Per-person end age; default 100 |
| 31 | Simulation start | **keep** | Dated plans start from today |
| 32 | Plan backup | **keep** | Copy SQLite file; no in-app export |

### Explicitly removed from legacy

- Monte Carlo success-rate trials
- Quarterly intervals
- YAML config workflow
- React frontend / Flask JSON API split
- Dev containers

---

## 7. Legacy logic to port

| Legacy module | Destination | Priority |
|---------------|-------------|----------|
| `social_security.py` | `domain/social_security/` | High |
| `pension.py` | `domain/pension/` | High |
| `job_income.py` | `domain/job_income/` | High |
| `taxes.py` (income-side) | `domain/taxes/` | High |
| `economic_data` / historic data | `domain/market_data/` + tpaw data | Medium |
| `allocation.py` (total portfolio) | `simulation/allocation/` | High (merge with TPAW) |
| `simulator.py` | **Replace** | N/A |

Port pattern: adapt tests from legacy → implement with monthly boundaries → wire to engine.

---

## 8. Development phases

### Phase 0 — Cutover and scaffold

- Tag `legacy/v1-final`; mirror to `life-finances-legacy`
- Replace repo tree: uv workspace, packages, `data.db.blank`, init script, root `AGENTS.md`
- Minimal FastAPI split-pane shell

### Phase 1 — Core loop (minimal E2E)

- `core`: minimal `Plan`, SQLite repository
- `simulation`: monthly stub (fixed returns, simple TPAW withdrawal)
- `web`: split-pane; two editor sections (Household + Current Savings Portfolio); debounced auto-results
- Base spending is simulation output; only extra essential/discretionary spending are user inputs (Phase 4)

### Phase 2 — Domain port

- SS, pension, job income, income-side taxes (tests first)
- Unified timed income pipeline

### Phase 3 — TPAW engine (feature-by-feature)

- Walk parity table; implement in dependency order
- Validate against tpaw/legacy where applicable
- Update `packages/simulation/OVERVIEW.md`

### Phase 4 — UI completeness

- All editor sections driven by parity decisions
- Full tpaw chart set in results panel

### Phase 5 — Tools

- Marimo: disability insurance calculator (proves modular tool story)
- Additional offshoots as needed

Phases 2–3 may overlap once domain modules are independent.

---

## 9. Error handling and validation

- Pydantic validates `Plan` on save and before simulation
- Inline form errors via Jinja
- Simulation failures surfaced in results panel + logged

---

## 10. Security (single-user local)

- Bind `127.0.0.1` by default
- No auth
- `data/data.db` gitignored; never commit personal data

---

## 11. Open items (intentionally deferred)

- Tax-advantaged account buckets (Item 8)
- Plan comparison view (Item 25)
- CUDA / native simulation acceleration
- SPAW, fixed SWR withdrawal methods (Item 1)

---

## 12. Next step

After spec approval: invoke **writing-plans** skill to produce a detailed implementation plan for Phase 0–1.

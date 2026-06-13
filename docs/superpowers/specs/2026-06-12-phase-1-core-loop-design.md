# Phase 1 — Core Loop (Minimal E2E) Design

**Date:** 2026-06-13  
**Status:** Draft — pending user review  
**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)  
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-1-core-loop.md` *(to write after spec approval)*

---

## 1. Goal

Prove the full edit → persist → simulate → refresh loop on a working web app:

1. User edits plan fields in a TPAW-style split-pane UI
2. Changes save to SQLite automatically (debounced)
3. Results panel refreshes with a deterministic simulation stub
4. pytest covers core, simulation, and web smoke paths

Phase 1 is **not** responsible for real TPAW math, charts, base-spending calculation, extra-spending inputs, stock/bond allocation inputs, or plan switching.

---

## 2. Scope adjustments from rebuild index

The [rebuild index](../plans/2026-06-12-rebuild-index.md) lists "one editor section" for Phase 1. This spec delivers **two** sections to match TPAW sectioning:

| Order | Section | Inputs |
|-------|---------|--------|
| 1 | Household | Birth month/year and max age per person (two-person household) |
| 2 | Current Savings Portfolio | Total investment savings balance only |

### Spending model (all phases)

Recorded here because it corrects a common misconception:

- **Base spending = simulation output** (TPAW withdrawal result), never a user input
- **User spending inputs** = extra essential and discretionary timed streams only (Phase 4 editor)
- **Stock/bond split = prescribed** by simulation/allocation logic, never an editor input

---

## 3. Architecture approach

**Recommended:** Scrollable all-sections shell (Approach A).

Both editor sections render stacked in the left pane on `/`. Field changes POST via HTMX to `PATCH /plan`; after a successful save, a `planUpdated` event triggers `GET /results` on the right pane.

Section partial routes (`/editor/household`, `/editor/portfolio`) exist for HTMX swap and Phase 4 reuse, but Phase 1 shows both sections without requiring navigation.

**Rejected alternatives:**

- **Section-routed navigation only** — overkill for two sections; hides content until clicked
- **Whole-form save** — simpler but loses field-level partial updates needed for Phase 4

---

## 4. Plan model (`packages/core`)

### Schema

```python
class PersonHousehold(BaseModel):
    birth_month: int          # 1–12 (dated plan)
    birth_year: int
    max_age_years: int = 100    # per-person simulation end age

class Household(BaseModel):
    person1: PersonHousehold   # labeled "You" in UI
    person2: PersonHousehold   # labeled "Partner" in UI

class Portfolio(BaseModel):
    current_savings_balance: Decimal  # single savings account; no split input

class Plan(BaseModel):
    name: str
    household: Household
    portfolio: Portfolio
    # Future phases add: extra_spending, risk, inflation, simulation config, …
```

### Persistence

- Existing `plans` table unchanged: `id`, `name`, `data` (JSON blob), `created_at`, `updated_at`
- `PlanRepository`: `get_by_id`, `save`, `list_all`, `get_or_create_default()`
- `data` column stores `Plan.model_dump_json()`

### Bootstrap

- `data.db.blank` stays **empty** (no seed row committed)
- First `GET /` calls `get_or_create_default()` when zero plans exist
- Default plan: name `"Default Plan"`, non-personal placeholders (e.g., birth years 1970/1972, $500,000 balance)

---

## 5. Simulation stub (`packages/simulation`)

No `domain` dependency in Phase 1.

```python
class SimulationResult(BaseModel):
    ran_at: datetime
    horizon_months: int
    echo: dict[str, Any]       # key inputs echoed back
    stub_version: str = "phase1"

def run_simulation(
    plan: Plan,
    *,
    percentiles: list[int] | None = None,
) -> SimulationResult:
    ...
```

### Deterministic behavior

- `horizon_months`: months from today to the later of person1/person2 max age (using birth year/month)
- `echo`: `{balance, person1_age_years, person2_age_years, plan_name}`
- `percentiles` accepted but ignored (signature matches future public API)
- Same inputs → same output every time

No base-spending calculation until Phase 3.

---

## 6. Web app (`packages/web`)

### Stack additions

- `uvicorn` — dev server
- `python-multipart` — form posts
- HTMX — CDN script in base template

### App entry

`web.app:app` — FastAPI, binds `127.0.0.1` by default.

### Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Split-pane shell; `get_or_create_default()`; embeds both editor sections |
| `/editor/household` | GET | Household section partial |
| `/editor/portfolio` | GET | Portfolio section partial |
| `/plan` | PATCH | Merge form fields into `Plan`, validate, save |
| `/results` | GET | Run stub simulation; return placeholder partial |

### Left pane — editor sections

**Household** (per person: "You" / "Partner"):

- Birth month (select 1–12)
- Birth year (number)
- Max age (number, default 100)

**Current Savings Portfolio:**

- Single currency field: total investment savings balance
- Helper text (TPAW-aligned): investment accounts only; exclude home equity and real estate

### Right pane — minimal placeholder

```
Results updated at 2026-06-13 14:32:05
Horizon: 412 months
Balance: $500,000 · You: 56 · Partner: 54
(stub — charts and spending outputs arrive in Phase 3)
```

No charts, no base-spending readout in Phase 1.

### HTMX flow

```
Editor form  ──change delay:750ms──►  PATCH /plan  ──►  SQLite
                                              │
                                              ▼ dispatch planUpdated
Results div  ◄──hx-get /results───────────────┘
```

- Editor: `hx-patch="/plan"`, `hx-trigger="change delay:750ms"` on inputs
- After successful PATCH, dispatch `planUpdated` → results div runs `hx-get="/results"`
- Header shows static "Default Plan" label (plan switcher deferred to Phase 4)

### Styling

Minimal custom CSS (`web/static/style.css`): CSS grid split pane (~40/60), system font stack. Wireframe-quality is acceptable for Phase 1.

### Dev command

Document in `packages/web/AGENTS.md`:

```bash
uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000
```

---

## 7. File layout

```
packages/core/
├── core/
│   ├── models.py
│   ├── repository.py
│   └── defaults.py
└── tests/
    ├── test_models.py
    └── test_repository.py

packages/simulation/
├── simulation/
│   ├── result.py
│   └── stub.py
└── tests/
    └── test_stub.py

packages/web/
├── web/
│   ├── app.py
│   ├── dependencies.py
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── editor_household.html
│       ├── editor_portfolio.html
│       └── results_stub.html
├── web/static/
│   └── style.css
├── AGENTS.md
└── tests/
    └── test_app.py
```

`packages/domain` unchanged in Phase 1.

---

## 8. Error handling

| Failure | Behavior |
|---------|----------|
| Invalid form field | Pydantic validation → inline error in section partial (`422` + error fragment) |
| DB missing on startup | `GET /` shows message: run `uv run python scripts/init_db.py` |
| Simulation stub raises | Error banner in results panel; logged at WARNING |
| Corrupt stored JSON | Repository catches `ValidationError`; error partial, no app crash |

---

## 9. Testing

| Package | Tests |
|---------|-------|
| `core` | Plan validation; repository round-trip; `get_or_create_default()` on empty DB |
| `simulation` | Stub determinism; `horizon_months` from household ages |
| `web` | `GET /` 200 with both sections; `PATCH /plan` persists; `GET /results` echoes after edit |

`make` (lint + test) passes at phase end.

---

## 10. Exit criteria

- [ ] `Plan` with `Household` + `Portfolio` persists via repository
- [ ] Empty DB auto-creates "Default Plan" on first visit
- [ ] Split-pane at `/` with Household and Current Savings sections
- [ ] Field edits trigger debounced save + results refresh
- [ ] Stub returns deterministic placeholder (timestamp + echo + horizon)
- [ ] Dev server documented and runnable
- [ ] pytest passes for core, simulation, web
- [ ] Rebuild index updated when phase completes

---

## 11. Follow-up doc updates (during implementation)

- Rebuild index: note two editor sections; update active phase table on completion
- Parent architecture spec §8 Phase 1: add spending-model clarification (base = output)

---

## 12. Next step

After spec approval: invoke **writing-plans** to produce `docs/superpowers/plans/2026-06-12-phase-1-core-loop.md`.

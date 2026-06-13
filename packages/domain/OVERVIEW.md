# Domain — Package Overview

Income, pension, Social Security, and tax domain logic. Produces unified timed income streams and tax-adjusted monthly cashflows for the simulation engine.

**Status:** Phase 0 scaffold only — no ported modules yet. Phase 2 delivers the domain port.

## Target public API

```python
def build_monthly_cashflows(plan: Plan) -> MonthlyCashflows:
    """Income-side taxes applied; unified timed streams."""
```

## Legacy port map

Source: legacy `backend/app/models/controllers/` at tag [`legacy/v1-final`](https://github.com/chriskelly/LifeFinances/tree/legacy/v1-final). Port pattern: adapt legacy tests → implement with monthly boundaries → wire to engine.

| Legacy module | Target path | Priority | Status |
| ------------- | ----------- | -------- | ------ |
| `social_security.py` | `domain/social_security/` | High | not started |
| `pension.py` | `domain/pension/` | High | not started |
| `job_income.py` | `domain/job_income/` | High | not started |
| `taxes.py` (income-side) | `domain/taxes/` | High | not started |
| `economic_data` / historic data | `domain/market_data/` + tpaw data | Medium | not started |

**Replaced, not ported:** `simulator.py` — superseded by `packages/simulation`.

## Design constraints

- Native time unit is **one month** (`month_index`; ages in months).
- No system-level retirement state — job income ends at a configured date.
- Income-side taxes only in v1 (no withdrawal or capital-gains taxes).
- Unified timed income streams — no pre/post retirement split.

## References

- Architecture spec §3, §7: `docs/superpowers/specs/2026-06-12-life-finances-rebuild-design.md`
- Phase 2 plans: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (Phases 2a–2d)

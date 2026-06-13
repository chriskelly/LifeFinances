# Simulation — Package Overview

Monthly TPAW (Total Portfolio Allocation and Withdrawal) simulation engine. Replaces legacy Monte Carlo success-rate trials.

**Status:** Phase 0 scaffold only — no engine yet. Phase 1 delivers a deterministic stub; Phase 3 delivers the full TPAW port.

## Target public API

```python
def run_simulation(plan: Plan, *, percentiles: list[int]) -> SimulationResult:
    cashflows = domain.build_monthly_cashflows(plan)
    ...
```

## TPAW parity backlog

Source: architecture spec §6. Update this table as features land in Phases 3a–3d.

| # | Feature | Stance | Status |
| - | ------- | ------ | ------ |
| 1 | Withdrawal methods | TPAW only | not started |
| 2 | Spending structure | Base target + timed extra essential/discretionary | not started |
| 3 | Spending adjustments | Spending tilt only | not started |
| 4 | Total portfolio allocation | Full RRA on total portfolio incl. PV of future income | not started |
| 5 | Percentile output | User-configurable percentile bands | not started |
| 6 | Return path generation | Block-bootstrap; Python port | not started |
| 7 | Inflation (default) | Block-bootstrap from historical data | not started |
| 8 | Account structure | Single savings portfolio v1 | not started |
| 9 | Taxes | Income-side only (via domain) | not started |
| 10 | Household | Two-person (user + partner) | not started |
| 14 | Future savings | **skip** — portfolio grows via income − taxes − spending | n/a |
| 15 | Annuities | **skip** — manual timed income streams | n/a |
| 19 | External spending | **skip** | n/a |
| 20 | External wealth | **skip** | n/a |
| 21 | Risk tolerance | Full tpaw RRA | not started |
| 22 | Market data | Port tpaw historical monthly data | not started |
| 23 | Sampling config | tpaw defaults + advanced overrides | not started |
| 24 | Results charts | Full tpaw major chart types | not started |
| 26 | Planning returns | Bootstrap paths vs planning expected returns/vol | not started |
| 27 | Inflation override | Suggested preset or manual fixed rate | not started |
| 29 | Rebalancing | Monthly | not started |
| 30 | Simulation horizon | Per-person end age; default 100 | not started |
| 31 | Simulation start | Dated plans start from today | not started |

Full parity table with notes: `docs/superpowers/specs/2026-06-12-life-finances-rebuild-design.md` §6.

## Legacy allocation port

| Legacy module | Target path | Status |
| ------------- | ----------- | ------ |
| `allocation.py` (total portfolio) | `simulation/allocation/` | not started |

Merge with TPAW RRA logic during Phase 3c.

## References

- tpaw reference implementation (external): compare golden tests in Phase 3b+
- Phase 3 plans: `docs/superpowers/plans/2026-06-12-rebuild-index.md` (Phases 3a–3d)

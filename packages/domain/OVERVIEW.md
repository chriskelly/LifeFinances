# Domain Package — Overview

Ported legacy finance logic that produces unified timed income/spending streams
and tax-adjusted cashflows. Depends only on `core`. Never imports `web`.

## Stream primitive

Income and spending sources are built from `core.streams.TimedStream` and
projected with `core.timeline.project_stream`. See the Phase 2a design spec:
`docs/superpowers/specs/2026-06-12-phase-2a-domain-core-design.md`.

- **Real vs nominal (spec §6):** `is_nominal=False` => today's dollars, inflation
  applied by the simulation layer, growth is a real raise. `is_nominal=True` =>
  fixed nominal dollars, inflation not applied, growth is a nominal raise.
- **Future-dated nominal anchoring is NOT supported** (spec §6) — only add a
  3-way mode when a consumer needs it.
- **Composition (spec §6.1):** features that modify income over a sub-window
  (e.g. planned sabbaticals — break or % reduction) are expressed by composing
  multiple `TimedStream` segments, honoring the growth re-anchoring rule (§4).

## Legacy port map

| Legacy module | Destination | Phase | Status |
|---------------|-------------|-------|--------|
| `social_security.py` | `domain/social_security/` | 2b | not started |
| `job_income.py` (incl. planned sabbaticals) | `domain/job_income/` | 2c | not started |
| `pension.py` | `domain/pension/` | 2d | not started |
| `taxes.py` (income-side) | `domain/taxes/` | 2d | not started |
| `build_monthly_cashflows(plan)` aggregator | `domain/__init__.py` | 2d | not started |

Port pattern: adapt legacy tests -> implement with monthly boundaries -> wire to
the engine.

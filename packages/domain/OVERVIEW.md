# Domain Package — Overview

Ported legacy finance logic that produces unified timed income/spending streams
and tax-adjusted cashflows. Depends only on `core`. Never imports `web`.

## Stream primitive

Income and spending sources are built from `core.streams.TimedStream` and
projected with `core.timeline.project_stream`.

- **Real vs nominal:** `is_nominal=False` => today's dollars, inflation
  applied by the simulation layer, growth is a real raise. `is_nominal=True` =>
  fixed nominal dollars, inflation not applied, growth is a nominal raise.
- **Future-dated nominal anchoring is NOT supported** — only add a
  3-way mode when a consumer needs it.
- **Composition:** features that modify income over a sub-window
  (e.g. planned sabbaticals — break or % reduction) are expressed by composing
  multiple `TimedStream` segments, honoring the growth re-anchoring rule on
  each segment boundary.

## Legacy port map

| Legacy module | Destination | Status |
|---------------|-------------|--------|
| `job_income.py` (incl. planned sabbaticals) | `domain/job_income/` | done |
| `social_security.py` | `domain/social_security/` | done |
| `pension.py` | `domain/pension/` | done |
| `taxes.py` (income-side) | `domain/taxes/` | done |
| `build_monthly_cashflows(plan)` aggregator | `domain/__init__.py` | done |

Port pattern: adapt legacy tests -> implement with monthly boundaries -> wire to
the engine.

## Single-person households

`Household.person2` is optional (`None` = single-person plan). `Household.people`
yields present members; `Household.resolved_filing_status` derives `single` vs
`married_filing_jointly` from household size unless `filing_status` is set
explicitly. Job income, Social Security (spousal skipped when absent), pension,
taxes, and `build_monthly_cashflows` all operate over present members only.

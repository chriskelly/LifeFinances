# Domain models and streams

Scope: the timed-stream primitive, real/nominal basis, and single-person
households. Read before adding an income or spending source.

The finance logic here produces unified timed income/spending streams and
tax-adjusted cashflows; the pre-rebuild implementation is preserved at tag
`legacy/v1-final`.

## Stream primitive

Income and spending sources are built from `core.streams.TimedStream` and
projected with `core.timeline.project_stream`.

- **Real vs nominal:** `is_nominal=False` => today's dollars, consumed as-is by
  the simulation layer (no inflation conversion), growth is a real raise.
  `is_nominal=True` => fixed nominal dollars, deflated to today's dollars by the
  simulation layer, growth is a nominal raise.
- **No third basis mode exists**; add one only when a consumer needs it.
- **Composition:** features that modify income over a sub-window
  (e.g. planned sabbaticals — break or % reduction) are expressed by composing
  multiple `TimedStream` segments, honoring the growth re-anchoring rule on
  each segment boundary.

## Single-person households

`Household.person2` is optional (`None` = single-person plan). `Household.people`
yields present members; `Household.resolved_filing_status` derives `single` vs
`married_filing_jointly` from household size unless `filing_status` is set
explicitly. Job income, Social Security (spousal skipped when absent), pension,
taxes, and `build_monthly_cashflows` all operate over present members only.

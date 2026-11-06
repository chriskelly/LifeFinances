# Resolved assumptions without a simulation

`resolve_assumptions(plan, ...)` in `../simulation/assumptions.py` resolves
inflation and planning returns and returns a `ResolvedAssumptions` snapshot
without running `preprocess`, `build_return_paths`, or the engine. It is for
display-only consumers such as the Market assumptions editor.

It refreshes market data only when a caller passes `allow_refresh=True` and the
resolver's staleness (and, for keyed feeds, API key) conditions are met. With the
default `False`, the existing cache -> vendored fallback applies and the editor
ignores configured API keys.

Values and observation dates match a simulation reading the same cache/vendored
files. A live refresh can make the two differ in either direction until the
other side re-reads or its cache misses; source labels describe each caller's
own read path, so a fresh editor read can say `cache` where a just-refreshed run
said `live`.

The entrypoint validates assumption resolution only. It does not run plan,
cashflow, or timeline validation, so a plan that fails a later simulation stage
still shows its assumptions here while the results panel reports the failure.

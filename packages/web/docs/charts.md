# Results charts

Scope: how the results panel selects, caches, and renders charts. Read before
changing `../web/charts.py`, the results template, or the simulation cache.

## Chart selection

`GET /results?plan={id}&chart={type}` renders `../web/templates/results.html`. Valid `chart`
values are the constants in `../web/charts.py` (`CHART_TYPES`); unknown values
fall back to `DEFAULT_CHART` (`spending-total`).

| Value | Chart |
| --- | --- |
| `portfolio` | Portfolio balance band |
| `spending-total` | Total spending band |
| `income-by-source` | Income by source: four stacked expected-path flows plus the dotted net total |
| `asset-allocation-savings-portfolio` | Savings stock allocation (0–100%) |
| `wealth-composition-low` / `-mid` / `-high` | Wealth composition at the low / middle / high configured percentile |

`income-by-source` reads the expected-path `diagnostics.net_income_*` flows (real
dollars, one value per month), so it has no percentile axis: the selector lists
it without a suffix and its traces do not vary with the configured percentiles.

The chart plots **net** flows, so a source can be negative (tax prorating, or the
nominal-basis manual adjustment). Plotly stacks negatives below zero, so the
dotted total is the authoritative line and may not sit at the top of the stack;
in a month with no gross income the four sources are zero while the total keeps
that month's residual tax.

## Simulation cache and resolved assumptions

Home and results both go through `web.simulation_cache.get_or_run_simulation`
(process-local LRU on `app.state`, keyed by plan id + plan JSON hash excluding
`name` + API keys + calendar date) so chart switches reuse the same
`SimulationResult` until the plan economics, settings keys, or day change. Cache
hits skip `allow_refresh` until the next miss — mid-day market-data updates are
invisible until then. The cache is single-process and not thread-safe (fine for
typical single-worker local use).

Every `SimulationResult` carries a required `resolved_assumptions` snapshot
(exact inflation/returns/volatility values plus source labels and observation
dates used by that run). On home and `/results`, charts and the Market
assumptions summary render `#resolved-assumptions-summary` from that cached
result; `/results` refreshes the same container via HTMX OOB
(`hx-swap-oob="innerHTML"`). The direct `GET /editor/market-assumptions` does
not run the engine: it resolves inflation and planning returns through
`simulation.assumptions.resolve_assumptions` with refresh disabled, so it never
blocks on a market-data fetch. The route is resolution-only: it does not run
plan, cashflow, or timeline validation, and it ignores configured API keys
because refresh is disabled. Refresh, freshness, and source-label caveats:
`packages/simulation/docs/assumptions.md`. A resolution failure on the
standalone editor route shows the editor's own assumptions-error message. Home
still passes its simulation failure into the included editor section through the
shared context key, and `/results` keeps the simulation-failure alert.

If the simulation raises, the results panel shows a generic `Simulation failed…`
alert (exception is logged server-side with stack trace; raw exception text is
not shown), keeps a hidden `#chart-select` so `planUpdated` can preserve the
chart query, omits the Plotly mount (`#chart-config` / `#results-chart`), and
replaces the resolved summary with **Unavailable for current settings** (no
stale numeric values).

## Rendering

Figures are built server-side as Plotly JSON (`web.charts.build_figure`); band
charts with ≥2 percentiles include a translucent fill between the outer
percentile rows. Figure JSON escapes `<` before `| safe` injection into the
config script tag. plotly.js loads once from CDN in `../web/templates/base.html`. The shell calls
`Plotly.react` on load and on every `htmx:afterSettle` targeting
`#results-panel`. The panel keeps the `#chart-select` value across `planUpdated` refreshes (see
`packages/web/docs/templates.md`).

Chart figures use `hovermode="x unified"` and `legend.traceorder="reversed"` so
unified hover lists all series with the lowest percentile last.
Wealth-composition and income-by-source traces set `hoveron="points"` because
unified hover does not reliably hit filled areas.

**Gotcha:** render charts on `htmx:afterSettle`, not `afterSwap`. Settle
re-applies server attributes to id-matched elements and strips Plotly's
`js-plotly-plot` class, which breaks absolute SVG positioning and pushes
tooltips off-screen. Always re-render after settle for HTMX-swapped Plotly divs.

**Gotcha:** `#results-chart` has a CSS `min-height` (`../web/static/style.css`)
matching Plotly's default figure height. Without it the empty chart div
collapses during the HTMX swap (before `Plotly.react` runs on settle), so the
summary line jumps up and back down — a flicker on every chart change. Keep the
`min-height` in sync if you set an explicit figure height in `build_figure`.

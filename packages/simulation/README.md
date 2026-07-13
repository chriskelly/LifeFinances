# `simulation` — the TPAW monthly withdrawal engine

This package turns a `Plan` into a set of simulated retirement outcomes. It is a
Python port of the withdrawal logic from [TPAW](https://tpawplanner.com/), adapted
to this rebuild's product scope (no spending ceiling/floor, no tax-bucket
sequencing yet, single scalar inflation rate). This document is a prose walkthrough
of how a plan flows through the engine — read it before diving into the source.

## The pipeline

```
domain.build_monthly_cashflows(plan)        # Decimal net income/taxes per month
        │  (→ float64 at the boundary)
        ▼
preprocess(plan)                            # NEW
  ├─ resolve_inflation(plan)                # Phase 3a (scalar monthly rate)
  ├─ resolve_planning_returns(plan)         # Phase 3c-2 (expected stock/bond returns)
  ├─ risk:    RRA-by-month + legacy RRA     # NEW  (risk.py)
  ├─ mertons: stock-alloc + spending-tilt   # NEW  (mertons.py)
  └─ npv:     backward PV pass + cumulative  # NEW  (npv.py, vectorized)
        ▼
build_return_paths(plan, months)          # Phase 3a (per-run monthly returns)
        ▼
simulate_monthly(processed, paths)          # vectorized forward loop (engine.py)
        ▼
RawSimulationResult  (engine-internal)      # per-run arrays in result.py
        ▼
aggregate + wealth composition            # aggregate.py, composition.py
        ▼
SimulationResult  (percentile-major)      # public return from run_simulation
```

## Stage by stage

**Domain cashflows.** Everything starts with `domain.build_monthly_cashflows`,
which produces a month-by-month schedule of net income and taxes as exact
`Decimal` values, independent of any simulation concerns. The engine converts
these to `float64` the moment they cross into simulation code — Decimal
precision matters for tax/income logic, but the downstream math is array-oriented
and needs floating point performance.

**Inflation and the shift to real terms.** Domain cashflows are nominal (today's
dollars projected forward with raises, COLAs, etc.), but the engine internally
works in *real* terms, matching how TPAW's historical return bootstrapping
already strips out inflation. `preprocess` resolves a single scalar monthly
inflation rate for the whole horizon (Phase 3a) and uses it to deflate the
nominal cashflows once, at the boundary, rather than carrying inflation as a
per-month adjustment through the rest of the pipeline. This is a deliberate
simplification versus TPAW's stochastic/bootstrapped inflation — see
`OVERVIEW.md` for the parity note.

**Return paths.** Also from Phase 3a, `build_return_paths` produces bootstrapped
monthly stock and bond returns for every simulated run, over the full horizon.
These are the random inputs that make each run differ from the others; the rest
of the pipeline is otherwise deterministic given a plan and a set of return
paths.

**Planning returns (expected).** Separate from the bootstrapped return paths,
`resolve_planning_returns` (`planning_returns.py`) produces the *expected*
annual stock and bond returns that drive Merton allocation, the backward NPV
pass, and the "expected run" baseline in the forward loop. The default preset
is TPAW's CAPE regression (`regression_prediction`); see
[Planning returns and CAPE regression](#planning-returns-and-cape-regression).
Bonds for most presets come from the vendored/live 20-year TIPS yield; stock
log-variance always comes from a vendored block-size table (not from the
preset choice).

**Risk tolerance → RRA.** A person's risk tolerance is translated into a
relative risk-aversion (RRA) coefficient per month — allowing an "age glide"
where risk aversion increases as retirement progresses — plus a separate RRA
for the legacy (bequest) goal, which can differ from the RRA used for ordinary
spending. This is the input that ultimately drives how much of the portfolio
sits in stocks versus bonds.

**Merton's formula: allocation and spending tilt.** Given the RRA, the expected
equity premium, and return variance, Merton's formula produces two things: the
theoretically optimal stock allocation, and a monthly "spending tilt" — a small
systematic drift (up or down) applied to the amortized general-spending
schedule to account for the risk-adjusted return the portfolio is expected to
earn over time. The formula includes guardrails for degenerate inputs (zero or
negative equity premium, infinite RRA meaning "no stocks at all") so it never
produces nonsensical allocations. See [Merton's formula](#mertons-formula) for
the equations.

**Backward NPV pass.** Before the forward simulation can run, the engine needs
to know, at every month, the net present value of all *future* cashflows and
goals from that point to the end of the horizon. This is computed with a
backward pass over the months (starting from the end and working back), and it
also produces `cumulative_1_plus_g_over_1_plus_r` — a cumulative discount factor
used to amortize the general spending pool evenly (with the Merton tilt) across
the remaining months. This pass is vectorized across runs but is inherently
sequential across months, since each month's NPV depends on the next month's.

**The forward monthly loop.** This is the heart of the engine (`engine.py`).
For each month, in order:

1. **Wealth** is computed as the current savings balance, plus the NPV of all
   future income (excluding the current month), plus the current month's
   income.
2. From that wealth, the engine withdraws — in order — the NPV of essential
   spending, then the NPV of discretionary spending (scaled), then the NPV of
   the legacy goal (scaled). Whatever remains is the **general** spending pool.
   Each of these draws is clamped so it can never exceed the wealth remaining
   at that point.
3. An **"expected run"** — a hypothetical run using fixed planning returns
   instead of the actual bootstrapped returns for this run — establishes a
   baseline "scheduled wealth" at every month, along with how sensitive
   (elastic) the discretionary and legacy goals are to changes in wealth.
   Real runs then scale discretionary and legacy spending up or down based on
   how this run's actual wealth compares to the scheduled wealth from the
   expected run. This is what makes discretionary spending "flex" with market
   performance while essential spending does not.
4. **Target withdrawals** for the month are set: essential is simply the
   current month's essential need; discretionary is the current discretionary
   need scaled by the elasticity factor from step 3; general is the general
   pool divided by the cumulative discount factor from the NPV pass, i.e.
   amortized evenly (with tilt) across the remaining horizon. There is no
   ceiling or floor on general spending in this port.
5. **Contributions and withdrawals** are applied to the savings balance: income
   for the month is added as a contribution, and the target withdrawals are
   subtracted. If the portfolio cannot cover everything, withdrawals are
   clamped to what's available and the run is flagged as having had
   insufficient funds for that month.
6. **Stock allocation** for the savings portfolio (as opposed to the
   theoretical whole-portfolio allocation from Merton's formula) is derived by
   comparing the stock-target implied by the general/discretionary/legacy pools
   to the actual savings balance, saturated to the [0, 1] range so the engine
   never asks for leverage or short positions.
7. **Applying allocation and returns.** The post-withdrawal balance is split
   between stocks and bonds according to that allocation, this run/month's
   bootstrapped real returns are applied to each piece (with monthly
   rebalancing back to the target split), and the result becomes the ending
   balance that feeds into next month's wealth calculation.

Because each month's ending balance depends on the previous month's, the month
loop is necessarily sequential — but every operation *within* a month is
vectorized across all simulated runs at once, which is what keeps the whole
simulation fast (on the order of tens of milliseconds for hundreds of runs over
multi-decade horizons).

**Public results.** `run_simulation` returns a percentile-major `SimulationResult`:
each chart series is reduced along the run axis (default percentiles from
`plan.advanced.percentiles`, overridable via kwarg). The forward loop still
emits a private `RawSimulationResult` (`num_runs × months`) internally; callers
should treat raw arrays as an engine artifact, not the public API. Wealth
composition bands (job, Social Security, pension, manual income — tax-prorated
remaining NPV at each month) are attached for stacked total-portfolio charts in
Phase 4.

## Merton's formula

Implementation lives in `mertons.py`. The engine calls `effective_mertons` (not
`plain_mertons` directly) once per month during preprocess, using planning
(expected) returns and the month's RRA. Symbols below match the code and TPAW.

| Symbol | Code / plan field | Meaning |
| ------ | ----------------- | ------- |
| \(r_b\) | `planning.annual_bonds` | Expected annual bond return |
| \(\mu\) | `planning.annual_stocks − planning.annual_bonds` | Expected annual equity premium |
| \(\sigma^2\) | vendored stock log-variance × 12 | Annual variance of stock log returns |
| \(\gamma\) | RRA from `risk.py` (per month, or legacy RRA) | Relative risk aversion |
| \(\rho\) | `plan.risk.time_preference` | Time preference (impatience) |
| \(g_{\text{add}}\) | `plan.risk.additional_annual_spending_tilt` | User override on annual consumption growth |

### Stock allocation

The plain Merton optimal equity weight (before guardrails) is:

\[
\pi^* = \frac{1}{\gamma}\,\frac{\mu}{\sigma^2}
\]

`effective_mertons` applies three guardrails that TPAW uses as well:

1. **Non-negative premium** — \(\mu_{\text{eff}} = \max(0,\,\mu)\). Negative
   equity premium would imply leverage; the engine treats it as zero stocks
   instead of calling the raw formula.
2. **RRA floor for 100% stocks** — \(\gamma_{\min} = \mu_{\text{eff}} / \sigma^2\)
   is the RRA at which Merton would allocate 100% to equities. The engine uses
   \(\gamma_{\text{eff}} = \max(\gamma_{\min},\, \gamma)\) so allocation never
   exceeds 100% without leverage.
3. **Saturate to \([0, 1]\)** — \(\pi = \min(1,\,\max(0,\,\pi^*))\) after the
   above, to absorb floating-point edge cases.

**Infinite RRA** (\(\gamma \to \infty\), meaning zero tolerance for stocks):
\(\pi = 0\).

### Spending tilt

Spending tilt is the optimal *annual* consumption growth rate from the same
Merton model, plus any user add-on. Define:

\[
c_0 = r_b - \rho + \frac{\mu^2}{2\sigma^2}, \qquad
c_1 = \frac{\mu^2}{2\sigma^2}
\]

Then:

\[
g_{\text{annual}}
  = \frac{1}{\gamma}\,c_0 + \frac{1}{\gamma^2}\,c_1 + g_{\text{add}}
  = \frac{r_b - \rho}{\gamma}
    + \frac{\mu^2}{2\sigma^2}\left(\frac{1}{\gamma} + \frac{1}{\gamma^2}\right)
    + g_{\text{add}}
\]

The value stored on `ProcessedPlan.spending_tilt` is the **monthly** rate,
compounded from the annual figure:

\[
g_{\text{monthly}} = (1 + g_{\text{annual}})^{1/12} - 1
\]

**Infinite RRA:** only the add-on survives — \(g_{\text{annual}} = g_{\text{add}}\).

#### Why tilt can be non-zero when \(\rho = 0\)

Time preference \(\rho\) is impatience: it appears only in the \(r_b - \rho\)
term. Setting \(\rho = 0\) does *not* mean flat spending. Bond returns
(\(r_b/\gamma\)) and the equity-risk terms (\(\mu^2/(2\sigma^2)\) scaled by
\(1/\gamma\) and \(1/\gamma^2\)) still push optimal consumption growth up or
down. Zero tilt requires zero returns, zero risk effects, and \(g_{\text{add}} = 0\)
(or infinite RRA with no add-on).

#### Where tilt is consumed

During the backward NPV pass in `preprocess.py`, each month's
`spending_tilt` enters the cumulative amortization factor for general spending:

\[
(1 + g_{\text{monthly}}) \times \frac{1}{1 + r_{\text{portfolio}}}
\]

where \(r_{\text{portfolio}}\) is that month's planning total-portfolio return.
That cumulative factor amortizes the general pool into monthly withdrawal
targets in the forward loop.

Unit tests pin numeric outputs against TPAW doctests in `test_mertons.py`.

## Planning returns and CAPE regression

Implementation lives in `presets.py` (pure math) and `planning_returns.py`
(dispatch + market-data injection). Vendored inputs are under
`market_data/data/` — see `PROVENANCE.md` for sources.

### Preset menu

`Plan.planning_returns.preset` selects how expected returns are derived. The
engine fixes these values at month 0 for the whole horizon (TPAW does not
glide expected returns). Stock log-variance is always
`variance_by_block[block_size_months] × stock_volatility_scale²`, independent
of the preset.

| Preset | Stocks | Bonds |
| ------ | ------ | ----- |
| `regression_prediction` | mean of 8 CAPE regressions (below) | round3(20-yr TIPS) |
| `conservative_estimate` | mean of 4 lowest of [1/CAPE, *8 regressions] | round3(20-yr TIPS) |
| `one_over_cape` | round3(1/CAPE) | round3(20-yr TIPS) |
| `historical` | unrounded historical mean | unrounded historical mean |
| `fixed_equity_premium` | round3(TIPS) + premium | round3(20-yr TIPS) |
| `custom` | chosen stock base + delta | chosen bond base + delta |
| `fixed` | `expected_annual_return_stocks` | `expected_annual_return_bonds` |

`round3` matches TPAW `round_p(3)` (half away from zero to 3 decimal places).

### Runtime: from market data to `regression_prediction`

When the preset needs live valuation (all except `fixed` and `historical`):

1. **1/CAPE** — `shiller_10yr_real_earnings / sp500_close`. Earnings are
   vendored (v7 Shiller 10-year average real earnings); price is the latest
   S&P close at or before `today` (cache → vendored → optional live EOD).
2. **Regression input** — \(x = \ln(1 + 1/\text{CAPE})\).
3. **Eight linear predictions** — for each `(slope, intercept)` in
   `cape_regression_v7.json`: `annual_log = slope × x + intercept`.
4. **Log → simple conversion** — each `annual_log` is converted to a simple
   annual return via the shift correction (next subsection).
5. **Aggregate** — `regression_prediction = round3(mean of all 8 simple returns)`.

Bonds for these presets use `round3` of the 20-year TIPS real yield from the
Treasury resolver (cache → vendored → optional live Treasury API).

### Where the eight coefficients come from

The JSON coefficients are **not** fitted at runtime. TPAW's maintainer CLI
(`cli_process_historical_data_part_2_derive` in the `tpaw` repo) runs eight
separate OLS regressions on Shiller history and bakes the results into Rust
constants; LifeFinances copies the v7 set verbatim.

For each fit:

- **Predictor (X):** \(\ln(1 + 1/\text{CAPE})\) at the start of each overlapping
  forward window.
- **Response (Y):** realized forward **annualized log** stock return — the sum
  of the next \(N \times 12\) monthly log returns, divided by \(N\).

| | 5 yr | 10 yr | 20 yr | 30 yr |
| --- | --- | --- | --- | --- |
| **full** | from first month CAPE exists | … | … | … |
| **restricted** | from Jan 1950 | … | … | … |

- **full** — longest available Shiller sample (~1871 onward).
- **restricted** — post-1950 subsample (TPAW treats pre-WWII as a different regime).

Each cell is one `(slope, intercept)` pair. At runtime we evaluate all eight
against today's \(x\) and average.

### Why the shift correction exists

The regressions predict **annual log returns**, but the preset menu and Merton
math consume **simple annual returns** (e.g. `0.05` = 5%). You cannot naively
apply `exp(annual_log) − 1` — log and simple returns relate nonlinearly, and
TPAW defines "annual non-log return" empirically as the mean of overlapping
12-month *simple* returns built from monthly log data.

For the preset menu (`block_size = None`, `volatility_scale = 1.0`), the
correction is:

\[
\text{correction}
  = \frac{\ln(1 + \bar{r}_{\text{simple,annual}})}{12} - \bar{r}_{\text{log,monthly}}
\]

where the bars are computed from the vendored v7 historical stock series
(`_shift_correction` in `presets.py`, mirroring TPAW `get_shift_correction`).
Each regression output is then:

\[
r_{\text{simple,annual}} = \exp\!\left(\left(\frac{\text{annual\_log}}{12} + \text{correction}\right) \times 12\right) - 1
\]

The **historical** preset skips this path for stocks/bonds — it uses the
unrounded empirical mean directly (TPAW does not `round_p(3)` historical).

Golden outputs for a pinned input tuple (`sp500_close`, Shiller earnings,
TIPS) live in `tests/tpaw_preset_contract.py`; `test_presets.py` asserts parity.

## What essential, discretionary, general, and legacy mean

- **Essential** spending is non-negotiable (housing, food, and the like). It is
  reserved first from wealth, every month, and is discounted at the risk-free
  (bond) rate on the theory that it must be funded regardless of how markets
  perform.
- **Discretionary** spending is the spending a person could choose to cut back
  on if the portfolio is doing poorly, or increase if it's doing well. It is
  reserved second, after essential, and is the goal that flexes via the
  expected-run elasticity mechanism described above.
- **General** spending is everything else — the "base" spending someone expects
  in retirement that isn't tied to a named essential or discretionary goal. It
  is whatever wealth remains after essential, discretionary, and legacy have
  been carved out, and it is amortized as evenly as possible (with the Merton
  spending tilt) across the rest of the horizon, rather than being drawn down
  unevenly.
- **Legacy** is an end-of-horizon bequest target — money intended to be left
  over at the end of the plan rather than spent. It is reserved last (after
  essential and discretionary), and it is discounted using its own,
  separately-derived risk-aversion rate rather than the RRA used for ordinary
  spending.

## Withdrawals start at month 0

There is no separate "accumulation phase" concept in this engine — spending is
active from the very first simulated month (`withdrawal_start_month = 0` for
every month). Retirement, in other words, is implicit in the plan's cashflows
rather than being a distinct phase the engine transitions into partway through
a run. If a plan represents someone who hasn't retired yet, that shows up as
income in the cashflows for the pre-retirement months, not as a flag the engine
checks.

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
preprocess(plan, cashflows)                 # NEW
  ├─ resolve_inflation(plan)                # Phase 3a (scalar monthly rate)
  ├─ build_return_paths(plan, months)       # Phase 3a (per-run monthly returns)
  ├─ risk:    RRA-by-month + legacy RRA     # NEW  (risk.py)
  ├─ mertons: stock-alloc + spending-tilt   # NEW  (mertons.py)
  └─ npv:     backward PV pass + cumulative  # NEW  (npv.py, vectorized)
        ▼
simulate_monthly(processed)                 # NEW vectorized forward loop (engine.py)
        ▼
SimulationResult  (raw per-run arrays)      # expanded result.py
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
produces nonsensical allocations.

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

**Raw results.** The engine does not aggregate its output into percentiles or
charts — that's Phase 3d's job. Instead it returns a `SimulationResult` holding
the raw per-run, per-month arrays (starting balances, and the essential /
discretionary / general / total withdrawals, plus the resulting stock
allocation and a count of runs that ran out of money), so downstream code can
choose how to summarize them.

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

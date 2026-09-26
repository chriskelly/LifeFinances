# Explain-results glossary

Document the explain JSON fields in `packages/web/OVERVIEW.md`, point the
`explain-results` skill at that file, and lock the name lists to the payloads
with a test. Covers GitHub issues #224 and #225.

The API does not change. Diagnostics slicing (#226), calendar labels (#227),
and a reproducible eval harness (#223) stay out of scope.

## Documents

`packages/web/OVERVIEW.md` is new. It is the field glossary for the explain
JSON routes. `packages/simulation/README.md` stays the mechanism document. The
overview points there for how essential, discretionary, general, and legacy
spending are decided, and for Merton allocation. It does not restate those
equations.

`.agents/skills/explain-results/SKILL.md` points at the overview for names and
meanings. It keeps the route list, plan resolution, errors, grounding rules,
and the expected-path versus percentile allocation paragraph. It does not copy
the tables.

`packages/web/AGENTS.md` gains one sentence after the opening description:
"Explain JSON payload fields are documented in `OVERVIEW.md`."

## Overview tables

Three tables, headed exactly `## Series`, `## Summary`, and `## Diagnostics`.
Each name cell is one backtick token, including dotted names such as
`spending.worst_case`. A short intro on each table states units and indexing.

Row order is the order the test derives (below). Meaning cells are prose. The
test does not check them.

### Series

Intro: real monthly dollars, except `savings_stock_allocation`, which is a
fraction of savings. Month 0 is the summary `start_month`. Omitting
`percentile` on a withdrawal or allocation series returns every configured
percentile in one response. The four `wealth_*` series have no percentile
axis.

| Name | Meaning |
| --- | --- |
| `balance_start` | Savings at the start of the month, before that month's income, withdrawals, and returns. Month 0 is the plan's current savings. |
| `withdrawals_essential` | Amount withdrawn that month for essential spending. |
| `withdrawals_discretionary` | Amount withdrawn that month for discretionary spending. |
| `withdrawals_general` | Amount withdrawn that month for general spending. |
| `withdrawals_total` | Sum of the three withdrawal series. |
| `savings_stock_allocation` | Fraction of savings in stocks after that month's withdrawal. Monte Carlo percentiles. |
| `wealth_job` | Remaining present value of tax-prorated real job income, including the current month, discounted at the planning bond rate. One path, shared by every run. |
| `wealth_social_security` | Same present-value definition, for Social Security. |
| `wealth_pension` | Same present-value definition, for pension income. |
| `wealth_manual` | Same present-value definition, for manual income streams. |

### Summary

Intro: scalars for the cached run. No month arrays.

| Name | Meaning |
| --- | --- |
| `ran_at` | ISO timestamp of the cached run. |
| `horizon_months` | Number of simulated months. |
| `num_runs` | Monte Carlo run count. |
| `percentiles` | Configured percentile values, ascending. |
| `start_month` | `[year, month]` of month 0. |
| `num_runs_insufficient` | How many runs had a month where requested withdrawals exceeded savings plus that month's income, and withdrawals were clamped to what was available. |
| `resolved_assumptions.annual_inflation` | Annual inflation rate used for the whole horizon. |
| `resolved_assumptions.annual_stock_return` | Expected annual stock return used for planning. |
| `resolved_assumptions.annual_bond_return` | Expected annual bond return used for planning. |
| `resolved_assumptions.annual_stock_log_variance` | Annual variance of stock log returns used by Merton allocation. |
| `resolved_assumptions.planning_preset` | Preset that produced the planning returns. |
| `resolved_assumptions.inflation_source` | `manual`, or a market-data source: `live`, `cache`, or `vendored`. |
| `resolved_assumptions.inflation_observation_date` | Date of the inflation observation. Null when the rate is manual. |
| `resolved_assumptions.sp500_source` | Source of the S&P close used for CAPE presets. Null when the preset does not use one. |
| `resolved_assumptions.sp500_observation_date` | Date of that S&P close. Null when unused. |
| `resolved_assumptions.treasury_source` | Source of the Treasury real yield. Null when the preset does not use one. |
| `resolved_assumptions.treasury_observation_date` | Date of that yield. Null when unused. |
| `spending.initial` | Total withdrawals at month 0. |
| `spending.worst_case` | Smallest month on the lowest configured percentile of `withdrawals_total`. Each month's percentile is computed on its own, so the row is an envelope across months. |

`plan_id` and `name` are omitted. Every explain route returns them, and the
skill already tells the agent to state both.

### Diagnostics

Intro: the expected path only, one value per month. Real dollars, except
fractions and risk aversion.

| Name | Meaning |
| --- | --- |
| `legacy_stock_allocation` | Merton stock weight for the legacy goal. One value for the whole horizon. |
| `rra_by_month` | Relative risk aversion. Infinity is stored as `1e300`. |
| `stock_allocation_total_portfolio` | Merton stock weight of total wealth. |
| `scheduled_wealth` | Expected-path wealth that discretionary and legacy spending are scaled against. Savings, plus the present value of future income, plus the current month's income, before this month's withdrawals. |
| `elasticity_discretionary` | Coefficient in the discretionary spending scale `max(0, (wealth / scheduled_wealth - 1) * elasticity + 1)`. On the expected path, wealth equals scheduled wealth, so the scale is 1. The coefficient itself varies by month. |
| `elasticity_legacy` | Same coefficient for the legacy goal. |
| `savings_balance` | Savings after that month's withdrawals on the expected path. Month 0 differs from series `balance_start`, which is the balance before that month's income and withdrawals. |
| `income_npv` | Present value of future income, excluding the current month. |
| `wealth_base` | `savings_balance` plus `income_npv`. |
| `essential_reserve` | Present value set aside for remaining essential spending, excluding the current month. |
| `discretionary_reserve` | Present value set aside for remaining discretionary spending, excluding the current month. |
| `legacy_reserve` | Present value set aside for the legacy goal. |
| `discretionary_pool` | Wealth left for discretionary spending after earlier reserves are carved out. |
| `legacy_pool` | Wealth left for the legacy goal after earlier reserves are carved out. |
| `general_pool` | Wealth left for general spending after essential, discretionary, and legacy reserves are carved out. |
| `stocks_target` | Dollar amount of stocks implied by the discretionary, legacy, and general pools. |
| `expected_savings_stock_fraction` | `stocks_target / savings_balance`, clamped to the range 0 through 1. |

## Skill text

Four edits. Everything else in the skill stays.

Under **Tools**, after the route bullets:

> Field names and meanings are in `packages/web/OVERVIEW.md`. Read that file before calling a series or quoting a field. Do not send an unknown `series` to discover the names.

The series bullet gains:

> Omit `percentile` to get every configured percentile in one response.

The `wealth_*` rule stays: those four series have no percentile axis, so do not
send `percentile` for them.

The closing lines become:

> Do not mutate the plan.
>
> What-if: the cached simulation is the plan as saved. Cite figures from that result. You may describe the direction of a change from `packages/simulation/README.md` when you label it best-effort, and you must not invent numbers for the changed plan. Do not suggest copying, editing, or re-running a plan. Do not ask which input the user would change.

## Drift test

`packages/web/tests/test_explain_overview.py` reads `packages/web/OVERVIEW.md`
through the `repo` fixture. It does not check meaning prose, the skill, or
`AGENTS.md`.

The parser takes the body under each exact heading and collects the backtick
token in the first cell of each table row.

Flattening a payload walks it in insertion order. A nested object becomes
dotted keys (`spending.initial`). Lists and nulls are leaves. Top-level
`plan_id` and `name` are dropped.

Three tests:

- The series names equal `list(PUBLIC_ARRAY_FIELDS)`.
- The summary names equal the flattened keys of `summary_payload` for a small in-memory result.
- The diagnostics names equal the flattened keys of `diagnostics_payload` for that same result.

A new payload field fails until a row is added. A row the payload does not
return fails too. Build the in-memory result the way
`packages/web/tests/test_explain_payload.py` already does, so the summary
includes null observation dates and those keys still appear.

## Verification

`make` passes. The acceptance reruns named in #224 and #225 (initial spending,
allocation at an age, worst-case spending, essential versus discretionary, a
spending drop, and the retire-later question) stay a manual check. This change
does not add an eval harness.

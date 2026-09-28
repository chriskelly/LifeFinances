# Web — Overview

FastAPI + HTMX UI for plan editing and simulation results. Depends on
`simulation`, `domain`, and `core`.

Explain JSON field names for `.agents/skills/explain-results` live in the three
tables below. Mechanism (essential / discretionary / general / legacy spending,
Merton allocation) is in `packages/simulation/README.md` — this file does not
restate those equations.

## Series

Real monthly dollars, except `savings_stock_allocation`, which is a fraction of
savings. Month 0 is the summary `start_month`. Omit `percentile` on a
withdrawal or allocation series to get every configured percentile in one
response. The four `wealth_*` series have no percentile axis.

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

## Summary

Scalars for the cached run. No month arrays. `plan_id` and `name` are on every
explain route and are omitted here.

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

## Diagnostics

The expected path only, one value per month (except `legacy_stock_allocation`,
which is a single scalar). Real dollars, except fractions and risk aversion.
`plan_id` and `name` are omitted.

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

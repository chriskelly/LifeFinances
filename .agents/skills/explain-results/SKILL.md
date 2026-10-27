---
name: explain-results
description: Explain the current LifeFinances plan and cached simulation by calling the local JSON API. Use when the user asks why a result, allocation, spending, or wealth number is what it is, or names a plan to inspect.
---

# Explain results

The dev server must be running:

`uv run uvicorn web.app:app --reload --host 127.0.0.1 --port 8000`

Base URL: `http://127.0.0.1:8000`. Read the response body on every status, including 4xx.

## Tools

All GET. For plan-scoped routes, pass exactly one of `plan_id` or `name`. Do not omit both. Do not send both. This API does not choose the default plan.

- `/api/plans` — loadable plans: `id`, `name`, `is_default`. No simulation.
- `/api/plan` — full plan JSON.
- `/api/result/summary` — scalars, resolved assumptions, initial and worst-case spending. No arrays.
- `/api/result/diagnostics?month=<index>&fields=<name>[,<name>...]` — expected-run diagnostics. `month` is a zero-based horizon index (0 is the Summary's `start_month`) that slices every array to one element and adds `month`; `fields` selects array fields, comma-separated or repeated (`fields=a,b` and `fields=a&fields=b` are equivalent). Omitting both returns the whole horizon and every field. Valid names, ordering, and always-returned keys are in `packages/web/OVERVIEW.md`.
- `/api/result/series?series=&month=&month_from=&month_to=&percentile=` — one Monte Carlo series. `series` is required; omitting it is 400 `invalid_query`. `percentile` is the configured value (for example 50), not a row index. On percentile-shaped series (`balance_start`, withdrawals, `savings_stock_allocation`), omit `percentile` to get every configured percentile in one response. Every response has `labels`: one `YYYY-MM` calendar month per returned month, aligned with each row's `values`; rows are `{percentile, values}`, with `percentile: null` on the `wealth_*` series. Omit the month parameters for the whole horizon, use `month=<index>` for one month, or `month_from`/`month_to` (inclusive horizon indices, either bound optional; absent rather than null when unused) for a range; a range response echoes the effective bounds. Derive an index with `(year - start_month.year) * 12 + (month - start_month.month)`. Do not combine `month` with a range. `values` is always a list.

Field names and meanings are in `packages/web/OVERVIEW.md`. Read that file before calling a series or quoting a field. Do not send an unknown `series` to discover the names.

If the user did not name a plan, call `/api/plans`, take the row with `is_default` true, and pass that `plan_id` on later calls. If none is default, ask which plan.

`wealth_job`, `wealth_social_security`, `wealth_pension`, and `wealth_manual` have no percentile axis. Do not send `percentile` for them.

## Errors

- 400 `invalid_query`, `unknown_series`, `unknown_field`, `unknown_percentile`, `percentile_not_applicable`, `month_out_of_range`, `invalid_range`
- 404 `plan_not_found`
- 409 `ambiguous_plan` with `candidates` — ask which id
- 422 `plan_unloadable` or `simulation_failed` — the `message` is the reason. Do not invent diagnostics.
- 422 with a `detail` list when a month parameter is not an integer (framework validation).
- 503 `db_not_initialized` — run `uv run python scripts/init_db.py`

`unknown_series`, `unknown_field`, and `unknown_percentile` include `allowed`. `month_out_of_range` includes `min` and `max` when the horizon has months; a zero-month horizon omits them. `invalid_range` means `month_from` is greater than `month_to`; `invalid_query` also covers combining `month` with a range.

After the `db_not_initialized` check, validation order is `series` (series route only), then plan, then the route's parameter shape (`fields` on diagnostics; the month selection on series, including the framework 422 for a non-integer month parameter), then the simulation, then the month bounds, then `percentile`. When both range bounds are out of range, `month_from` is reported first. Only the first failure is reported, so fix one parameter and retry.

## How to answer

State the `plan_id` and `name` from the response.

Grounded: every cited figure comes from these responses. Do not invent intermediates.

Mechanism: read `packages/simulation/README.md` first. You may read `packages/simulation/simulation/engine.py` and `packages/simulation/simulation/preprocess.py` only when that README does not state the mechanism, or when the README conflicts with the API. Say that the mechanism came from source. If the source disagrees with the cached series, cite the cached series and say they disagree.

Best-effort: for a question these payloads and the README do not cover, say the answer is best-effort. Do not fabricate intermediates.

Allocation: chart bands are Monte Carlo percentiles. The diagnostics spine is the expected/planning path. `expected_savings_stock_fraction` is that path. `savings_stock_allocation` on the series route is the percentile chart. Do not treat them as the same number.

Do not mutate the plan.

What-if: the cached simulation is the plan as saved. Cite figures from that result. You may describe the direction of a change from `packages/simulation/README.md` when you label it best-effort, and you must not invent numbers for the changed plan. Do not suggest copying, editing, or re-running a plan. Do not ask which input the user would change.

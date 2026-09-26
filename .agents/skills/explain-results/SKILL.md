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
- `/api/result/diagnostics` — full expected-run diagnostics.
- `/api/result/series?series=&month=&percentile=` — one Monte Carlo series. `percentile` is the configured value (for example 50), not a row index. Omit `month` for the whole horizon. `values` is always a list.

If the user did not name a plan, call `/api/plans`, take the row with `is_default` true, and pass that `plan_id` on later calls. If none is default, ask which plan.

`wealth_job`, `wealth_social_security`, `wealth_pension`, and `wealth_manual` have no percentile axis. Do not send `percentile` for them.

## Errors

- 400 `invalid_query`, `unknown_series`, `unknown_percentile`, `percentile_not_applicable`, `month_out_of_range`
- 404 `plan_not_found`
- 409 `ambiguous_plan` with `candidates` — ask which id
- 422 `plan_unloadable` or `simulation_failed` — the `message` is the reason. Do not invent diagnostics.
- 503 `db_not_initialized` — run `uv run python scripts/init_db.py`

`unknown_series` and `unknown_percentile` include `allowed`. `month_out_of_range` includes `min` and `max`.

## How to answer

State the `plan_id` and `name` from the response.

Grounded: every cited figure comes from these responses. Do not invent intermediates.

Mechanism: read `packages/simulation/README.md` first. You may read `packages/simulation/simulation/engine.py` and `packages/simulation/simulation/preprocess.py` only when that README does not state the mechanism, or when the README conflicts with the API. Say that the mechanism came from source. If the source disagrees with the cached series, cite the cached series and say they disagree.

Best-effort: for a question these payloads and the README do not cover, say the answer is best-effort. Do not fabricate intermediates.

Allocation: chart bands are Monte Carlo percentiles. The diagnostics spine is the expected/planning path. `expected_savings_stock_fraction` is that path. `savings_stock_allocation` on the series route is the percentile chart. Do not treat them as the same number.

Do not mutate the plan. Do not tell the user to change inputs as part of this skill.

# Explain JSON API

Scope: HTTP shape, parameter rules, and error responses for the read-only
explain routes. Read before changing `../web/explain_routes.py` or calling the API.
Field names and meanings are in `packages/web/docs/json-payloads.md`; agent
usage is in `.agents/skills/explain-results/SKILL.md`.

Read-only GET handlers live in `../web/explain_routes.py` (registered from
`create_app()`). Path constants are in `../web/routes.py`:

| Constant | Path |
| -------- | ---- |
| `API_PLANS` | `/api/plans` |
| `API_PLAN` | `/api/plan` |
| `API_RESULT_SUMMARY` | `/api/result/summary` |
| `API_RESULT_DIAGNOSTICS` | `/api/result/diagnostics` |
| `API_RESULT_SERIES` | `/api/result/series` |

Each plan-scoped route accepts exactly one of query params `plan_id` or `name`
(not both, not neither). Resolution uses `ApiPlanDep` (`web.explain.resolve_plan`);
result routes compose that with `SettingsDep` into `ApiResultDep`, which calls
`web.simulation_cache.get_or_run_simulation` — the same process-local cache as
Home and Results (see `packages/web/docs/charts.md`). Do not spawn a separate
simulation process for these routes. Failures raise `web.explain.ApiError`,
rendered as JSON by one app-level exception handler.

Unloadable plan JSON returns JSON `422` with code `plan_unloadable` and a
`message` (see `web.explain.resolve_plan`). That path intentionally does not use
`PlanDep` / `PathPlanDep`, which return JSON `404` `{"detail": "Plan not found"}`
and drop the validation message.

## Diagnostics slicing

`fields` is validated before the simulation runs, so an unknown field returns
`400 unknown_field` without a run. `month` and range errors follow the payload
rules in `packages/web/docs/json-payloads.md` (Diagnostics).

## Series selection

Monte Carlo spending and allocation series are percentile-major;
`wealth_job`, `wealth_social_security`, `wealth_pension`, and `wealth_manual`
accept no `percentile` (`percentile_not_applicable`). `month_from`/`month_to`
are resolved by `require_month_range`; a conflict with `month` or an inverted
range fails in `require_series_month_selection` before the simulation runs.
Response shape and `labels` are in `packages/web/docs/json-payloads.md` (Series).

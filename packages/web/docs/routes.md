# Web routes and plan resolution

Scope: plan-scoped routing, the header plan menu, and settings. Read before
adding or changing a plan-scoped route or the plan menu.

Behavior for the entry route, plan-scoped requests, and unknown ids:

- **`GET /`** without `plan` → `302` redirect to `/?plan={AppSettings.default_plan_id}` (user-marked default).
- **`GET /?plan=2`**, editor GETs, **`GET /results?plan=2`**, and section **`PATCH`** routes operate on that plan id, except `PATCH /plan/settings`, which writes the global settings row.
- Unknown plan id anywhere, or a missing id on an editor, results, or section route → `404` (`GET /` without `plan` redirects).
- Empty DB bootstrap creates one plan and sets `default_plan_id`.

Route constants for plan management live in `../web/routes.py` (`PLAN_CREATE`,
`PLAN_DUPLICATE`, etc.). Switching plans is a normal link to `/?plan={id}` (full
page reload).

## Header plan menu

`../web/templates/plan_menu.html` (included from `../web/templates/index.html`) exposes:

| Action | Route | Notes |
| ------ | ----- | ----- |
| Switch | `GET /?plan={id}` | Link per plan in the list |
| New | `POST /plans` | Blank `default_plan()`; redirect to new id |
| Duplicate | `POST /plans/{id}/duplicate` | Deep copy; redirect to new id |
| Rename | `POST /plans/{id}/rename` | `forms.PLAN_NAME`; redirect to same id |
| Set default | `POST /plans/{id}/set-default` | Updates `AppSettings.default_plan_id` |
| Delete | `POST /plans/{id}/delete` | Confirm in UI; optional `forms.RETURN_PLAN` keeps active plan when deleting a sibling; blocked when only one *loadable* plan remains; works by row id (no Plan JSON load); falls back to default when active was deleted |

## Settings (API keys)

`fred_api_key` and `eod_api_key` are edited in
`../web/templates/editor_settings.html`; `patch_settings` applies
`AppSettingsForm` and saves the singleton `AppSettings` row.
`get_or_run_simulation` passes both keys to
`run_simulation(..., allow_refresh=True)`.

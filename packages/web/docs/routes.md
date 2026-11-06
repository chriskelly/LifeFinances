# Web routes and plan resolution

Scope: plan-scoped routing, the header plan menu, and settings. Read before
adding or changing a plan-scoped route or the plan menu.

Every plan-scoped request uses the **`plan` query parameter** (`?plan={id}`).
There is no session or cookie state.

- **`GET /`** without `plan` → `302` redirect to `/?plan={AppSettings.default_plan_id}` (user-marked default).
- **`GET /?plan=2`**, editor GETs, **`GET /results?plan=2`**, and section **`PATCH`** routes operate on that plan id.
- Unknown or missing plan id on a plan-scoped route → `404`.
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

`fred_api_key` and `eod_api_key` live on **`AppSettings`** (singleton DB row),
edited via `../web/templates/editor_settings.html` / `AppSettingsForm`. They are injected at the
web boundary into `run_simulation(..., allow_refresh=True)`. Keys never go into
plan JSON, plan export, or git.

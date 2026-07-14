# Phase 4a — Web: Plan Shell & Management Design

**Date:** 2026-07-14  
**Status:** Approved  

**Parent:** [2026-06-12-life-finances-rebuild-design.md](./2026-06-12-life-finances-rebuild-design.md)  
**Builds on:** Phase 1 core loop (split-pane shell, `get_or_create_default`), Phase 3a+ / 3c settings (`AppSettings`, FRED key form; `eod_api_key` already read by HOME/RESULTS)  
**Phase plan:** `docs/superpowers/plans/2026-06-12-phase-4a-plan-shell.md` *(to write after spec approval)*  
**Index:** Phase 4a in [2026-06-12-rebuild-index.md](../plans/2026-06-12-rebuild-index.md)

---

## 1. Goal & scope

Replace the single implicit “first row / Default Plan” shell with **named multi-plan management** in the header, **URL-based active plan resolution** with a user-chosen default for `/`, and an **EOD API key** field in settings mirroring FRED.

### In scope

- Header plan menu: switch, new, duplicate, rename, set as default, delete
- Active plan via `?plan={id}`; `/` without `plan` redirects to the marked default
- `PlanRepository`: `list` / `create` / `duplicate` / `rename` / `delete` (+ bootstrap evolve)
- `AppSettings.default_plan_id` (+ schema / ensure migration)
- `eod_api_key` set/clear in `AppSettingsForm` + `editor_settings.html`
- Thread `plan` through home, editor GETs, results, and plan PATCH routes
- Tests for repository behaviors and web redirects / multi-plan save targeting

### Out of scope

- Plan comparison view (architecture: “later”)
- Separate `/plans` management page (header-only UX)
- Session/cookie active-plan state
- Path-prefixed routes (`/plans/{id}/…`)
- HTMX shell swap on switch (full page reload)
- Charts / income / spending editors (4b–4d)
- Legacy YAML import / launcher (4f)
- Form DTO `create_model` spike (4c Task 0)

---

## 2. Decisions captured from brainstorming

| # | Decision | Rationale |
| - | -------- | --------- |
| 1 | **URL only** for active plan (`?plan=`) | Bookmarkable; no session complexity |
| 2 | **User-marked default** for `/` / first load | Personal home plan without cookies |
| 3 | **`/?` → redirect to `/?plan={default}`** | After redirect every request has an explicit id; least branching |
| 4 | **Full light CRUD** | Create, switch, duplicate, rename, delete, set default |
| 5 | **New = blank `default_plan()`; Duplicate = copy of active** | Keep New and Duplicate distinct |
| 6 | **Header-only** (layout B: single plan menu) | Matches personal-app chrome; no second page |
| 7 | **Approach 1: query-param + full page reloads** | Least complex; fits current FastAPI/HTMX style |
| 8 | **`default_plan_id` on `AppSettings`** | One field; simpler than `is_default` uniqueness on rows |
| 9 | **Unknown plan id → 404** | Fail loudly; orphan default rewrites to lowest id |
| 10 | **EOD key mirrors FRED UI** | Simulation already consumes `eod_api_key` |

---

## 3. Active plan resolution & routing

**Source of truth:** `plan` query parameter on every plan-scoped request.

```
GET /                    → 302 /?plan={default_plan_id}
GET /?plan=2             → shell for plan 2
GET /results?plan=2      → results for plan 2
PATCH /plan/household?plan=2  → save into plan 2
```

**Bootstrap:**

- Empty `plans` table → create one plan via today’s bootstrap (`default_plan()`), set `AppSettings.default_plan_id` to that id, then redirect/serve as usual
- `/` with no `plan` → resolve default (see §7 orphan handling) → `302` to `/?plan={id}`
- Invalid / missing plan id on a plan-scoped route → `404`

**Replace** ubiquitous `get_or_create_default()` as the active-plan loader. Keep a bootstrap helper (“ensure at least one plan exists and default is set”) for empty DB / first visit only.

**HTMX forms:** pass `plan` via `hx-vals` or a hidden input so PATCH targets never silently hit the wrong plan.

**Plan-management endpoints** (under `/plans…`): POST (and similar) for create / duplicate / rename / delete / set-default; respond with **redirect** to `/?plan=…` (PRG). Not a management HTML page.

Suggested route constants (exact paths fixed in the phase plan):

| Action | Method | Example |
| ------ | ------ | ------- |
| Create | `POST /plans` | body: optional name → redirect `/?plan={new}` |
| Duplicate | `POST /plans/{id}/duplicate` | → redirect `/?plan={new}` |
| Rename | `POST /plans/{id}/rename` | name form → redirect `/?plan={id}` |
| Delete | `POST /plans/{id}/delete` | → redirect `/?plan={default}` |
| Set default | `POST /plans/{id}/set-default` | → redirect `/?plan={id}` |

Switching plans is a normal link: `/?plan={id}`.

---

## 4. Repository & data model

### `PlanRepository`

| Method | Behavior |
| ------ | -------- |
| `list()` | Return lightweight summaries (`id`, `name`, optionally `updated_at`) — no full JSON for the menu |
| `create(name=…)` | Insert `default_plan()` with given name; return `(id, plan)` |
| `duplicate(plan_id)` | Deep-copy JSON; name `"{name} (copy)"`; return new `(id, plan)` |
| `rename(plan_id, name)` | Update `plans.name` and `Plan.name` inside JSON (keep column/JSON in sync, as `save` already does) |
| `delete(plan_id)` | Refuse if only one plan remains; if deleted id was default, reassign default to lowest remaining id |
| `get_by_id` / `save` | Unchanged semantics |
| Bootstrap | Ensure ≥1 plan; set `default_plan_id` if unset |

### `AppSettings`

- Add `default_plan_id: int | None`
- Add column on `app_settings` in blank schema + `_ensure` / migrate path (same pattern as existing settings ensure)
- “Set as default” writes this field only

### Schema touchpoints

- `data/data.db.blank`: `app_settings.default_plan_id`
- Existing DBs: ensure/ALTER on settings repository open (match current FRED/EOD ensure style)

**Out of scope for data model:** plan versions, export, comparison metadata.

---

## 5. Header UI

**Layout B — single plan menu:** brand left; one control right showing active plan name (★ / “default” when it is the marked default).

**Menu:**

1. Plan list — active checkmarked; default annotated  
2. Divider  
3. **New plan…** — blank defaults; auto-name `Untitled Plan` (append ` 2`, ` 3`, … on collision); redirect to new id; rename available after  
4. **Duplicate** — copy active; `"{name} (copy)"` (same collision suffix rule if needed); redirect to new id  
5. **Rename…** — prompt/dialog; stay on same `?plan=`  
6. **Set as default** — no-op UI when already default; updates settings  
7. **Delete…** — confirm; disabled when only one plan left  

Implementation: native `<details>` / `<dialog>` (or equivalent small menu); no separate plans page.

---

## 6. Settings — `eod_api_key`

Mirror FRED in `AppSettingsForm` + `editor_settings.html`:

- Password input; “key is set” placeholder when present; empty submit does not clear  
- Separate clear form (`clear_eod_api_key`)  
- Constants: `EOD_API_KEY`, `CLEAR_EOD_API_KEY`  

HOME/RESULTS already pass `settings.eod_api_key` into `run_simulation(..., allow_refresh=True)` — no simulation API change.

---

## 7. Error handling & edge cases

| Case | Behavior |
| ---- | -------- |
| No `?plan=` on `/` | Redirect to default |
| Unknown `plan` id | `404` |
| Delete last plan | Reject (4xx); UI disables Delete |
| Delete current default | Reassign default to lowest remaining id; redirect there |
| Delete active (non-default) | Redirect to current default |
| Rename blank | Validation reject |
| Orphan `default_plan_id` | On resolve, fall back to lowest plan id and rewrite settings |
| Missing DB file | Unchanged init_db error page |

Editor PATCH validation errors stay as today (422 + message for HTMX).

---

## 8. Testing

**Core**

- `list` / `create` / `duplicate` / `rename` / `delete` (last-plan refusal; default reassignment)
- First create sets `default_plan_id` when unset; set-default updates settings
- Orphan default fallback + rewrite

**Web**

- `/` without `plan` redirects to `/?plan={default}`
- Home / results / PATCH operate on the queried plan (save to A does not mutate B)
- New / Duplicate / Delete / Rename / Set-default happy paths; last-plan delete blocked
- EOD key set/clear mirrors FRED tests

TestClient + repo fixtures only; no browser E2E. `make` must pass.

---

## 9. Package boundaries

```
web  →  core (PlanRepository, SettingsRepository, AppSettings, Plan)
     →  simulation (unchanged run_simulation call site; keys already forwarded)
```

`tools` / `simulation` never import `web`. Schema + repository logic stay in `core`.

---

## 10. Exit criteria (index alignment)

- [ ] Header shows active plan name with switcher; New and Duplicate (and rename / delete / set-default) work
- [ ] `PlanRepository` supports list, create, duplicate (plus rename/delete as above); saves target the active plan id from `?plan=`
- [ ] User-marked default; `/` redirects to it
- [ ] `eod_api_key` set/clear in settings editor; live S&P refresh usable from the UI once keyed
- [ ] `make` passes; app runs with multiple named plans

---

## 11. Implementation notes for the phase plan

- Prefer one FastAPI dependency: `resolve_active_plan(plan: int, repo, settings_repo) -> tuple[int, Plan]` used by home/editor/results/PATCH
- Update `web/AGENTS.md` briefly: active plan query param + header menu
- Update rebuild index Active phase / exit checkboxes when the plan is written and again when the phase completes
- Do not expand into 4b chart work in this PR

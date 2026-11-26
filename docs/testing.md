# Testing fixtures and layout

Scope: where test fixtures live, what each shared fixture owns, and the
browser-only editor checks. Read before adding a fixture; test rules are in the
root `AGENTS.md`.

- **`core.db_bootstrap.materialize_blank_db`** — copy committed blank schema to an arbitrary path; used by tests, `scripts/init_db.py`, and pytest fixtures.
- **Repo-root `conftest.py`** — cross-package fixtures (`db_path`, `repo`). Pytest discovers it for all `packages/*/tests/`.
- **Package `conftest.py`** — only fixtures specific to that package (e.g. web `client`). Do not duplicate `db_path` / `repo`.

## Browser-only editor behavior

`make browser-checks` runs the Playwright/Chromium harness in `browser_tests/`.
It starts the app with `LIFE_FINANCES_DB_PATH` pointed at a throwaway database
(never `data/data.db`) and automates the list and pane checks below that it
covers; the remaining checks stay manual. The first run installs Chromium; on
Linux use `uv run playwright install --with-deps chromium` once. A missing
browser fails the target instead of skipping. CI runs the same target.

The checks below are the complete manual pass. The harness covers the add,
focus, summary, sabbatical, removal, `existing_index`, pane-toggle, Plotly
resize, and corrupt-storage cases; keyboard/focus-ring, computed-style,
partner-independence, and re-add-sabbatical checks remain manual.

- Add a job, spending row, or income row: it opens, its label is focused, and
  the summary follows the label as it is typed. Clearing the label or entering
  whitespace falls back to the row's empty label.
- Add and remove a sabbatical inside a job; confirm focus lands on its Start
  control, then close and reopen the job and confirm the sabbatical's open
  state survives.
- Re-add a sabbatical after removing one; confirm the new row saves and the
  remaining sabbaticals stay attributed to the right job.
- Add a job to each person when a partner exists; confirm each form's
  add/remove/indexing stays independent.
- Save a new job, spending, or income row and confirm its `existing_index` input
  is inside `.row-fields`, not before `<summary>`.
- Remove a row and confirm focus moves to a neighbouring row summary or the
  list's add button.
- Toggle a row and a section summary with the keyboard (Enter/Space) and
  confirm the focus ring is visible.
- Confirm computed styles: `.row` and `.editor-section` margins are 0, `.rows`
  gap is 7px, the summary chevron has no background image and zero margin, the
  open row label color matches body text, and a focused summary outline is 2px
  with a -2px offset.
- Toggle the pane rail and confirm the Plotly chart resizes; corrupt
  `lifeFinances.panes` and confirm the editor falls back to visible.

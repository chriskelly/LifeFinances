# Testing fixtures and layout

Scope: where test fixtures live and what each shared fixture owns. Read before
adding a fixture; test rules are in the root `AGENTS.md`.

- **`core.db_bootstrap.materialize_blank_db`** — copy committed blank schema to an arbitrary path; used by tests, `scripts/init_db.py`, and pytest fixtures.
- **Repo-root `conftest.py`** — cross-package fixtures (`db_path`, `repo`). Pytest discovers it for all `packages/*/tests/`.
- **Package `conftest.py`** — only fixtures specific to that package (e.g. web `client`). Do not duplicate `db_path` / `repo`.

## Browser-only editor behavior

The repo has no JavaScript test runner. A change to
`packages/web/web/static/editor_lists.js` or `editor_layout.js` needs a
headless-browser pass against a temporary database (`LIFE_FINANCES_DB_PATH`),
not `data/data.db`:

- Add a job, spending row, or income row: it opens, its label is focused, and
  the summary follows the label as it is typed. Clearing the label or entering
  whitespace falls back to the row's empty label.
- Add and remove a sabbatical inside a job; close and reopen the job and
  confirm the sabbatical's open state survives.
- Save a new row and confirm its `existing_index` input is inside
  `.row-fields`, not before `<summary>`.
- Remove a row and confirm the remaining controls still work.
- Toggle the pane rail and confirm the Plotly chart resizes; corrupt
  `lifeFinances.panes` and confirm the editor falls back to visible.

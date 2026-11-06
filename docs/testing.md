# Testing fixtures and layout

Scope: where test fixtures live and what each shared fixture owns. Read before
adding a fixture; the TDD rules themselves are in `~/.agents/docs/tdd.md`.

- **`core.db_bootstrap.materialize_blank_db`** — copy committed blank schema to an arbitrary path; used by tests, `scripts/init_db.py`, and pytest fixtures.
- **Repo-root `conftest.py`** — cross-package fixtures (`db_path`, `repo`). Pytest discovers it for all `packages/*/tests/`.
- **Package `conftest.py`** — only fixtures specific to that package (e.g. web `client`). Do not duplicate `db_path` / `repo`.

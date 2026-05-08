# LifeFInances

A simulator for personal finances and retirement planning. The app is a Python (Flask) backend with a React + TypeScript frontend.

> **For coding agents and contributors:** project conventions, commands, and guardrails live in [`AGENTS.md`](AGENTS.md) (root), [`backend/AGENTS.md`](backend/AGENTS.md), and [`frontend/AGENTS.md`](frontend/AGENTS.md). Read those before making changes.

## Developer Setup

### With DevContainer (recommended)

Requires [Docker](https://docs.docker.com/get-docker/), [VS Code](https://code.visualstudio.com/), and the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

**Installation:**

1. Clone the repository and open the folder in VS Code
2. Click **Reopen in Container** when prompted, or run **Dev Containers: Reopen in Container** from the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Wait for the container to build (first time may take a few minutes)

The container provides Python 3.10, Node.js, all dependencies, pre-commit hooks, and a default `config.yml` if none exists. Port **3500** is forwarded for the Python backend (matches `python backend/run.py`, which binds **`0.0.0.0:3500`**) and port **5173** for the React frontend.

**Pre-commit hooks:** Installed automatically. They run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`.
Use Conventional Commits for commit messages (see [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary)), e.g. `fix(frontend): handle empty simulation response`.

**Common commands (inside the container):**

| Action             | Command                      |
| ------------------ | ---------------------------- |
| Start the backend  | `python backend/run.py`      |
| Start the frontend | `cd frontend && npm run dev` |
| Run tests          | `make test`                  |
| Lint and format    | `make lint`                  |

### Without DevContainer

**Installation:**

1. Python 3.10 required. This project uses [uv](https://docs.astral.sh/uv/) for dependencies. From the top-level directory:

   ```bash
   uv sync --project backend
   ```
1. Node.js `^20.19.0 || ^22.12.0 || >=24.0.0` is required by the frontend test stack (jsdom → html-encoding-sniffer → @exodus/bytes needs `require(ESM)` support). The repo pins a default in `.nvmrc`:

   ```bash
   # with nvm
   nvm install   # reads .nvmrc
   nvm use
   ```

   Without nvm, install a compatible Node via your package manager / `fnm` / `volta` / `asdf` / `mise`. The pre-commit wrapper checks the active version and fails fast with a clear message if it is too old.
1. Copy a sample config:

   ```bash
   cp backend/tests/sample_configs/full_config.yml config.yml
   ```

   (Use `min_config_net_worth.yml` or `min_config_income.yml` for smaller examples.)
1. Review allocation options at [`backend/app/data/README.md`](https://github.com/chriskelly/LifeFinances/blob/main/backend/app/data/README.md)

**Pre-commit hooks:**

```bash
pre-commit install
```

Hooks run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`. To skip: `git commit --no-verify`.
Use Conventional Commits for commit messages (see [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/#summary)), e.g. `chore(docs): clarify local setup`.

> **Note on Node + Cursor IDE:** Cursor Server bundles `node v20.18.2` and prepends it to `$PATH` for git operations launched from the IDE. That version is too old to `require()` ESM modules and will break the frontend test suite. The pre-commit hook is wrapped by [`scripts/precommit.sh`](scripts/precommit.sh), which sources nvm (if installed) and validates the resulting Node version before running `make`. If you don't use nvm, make sure a compatible Node appears on `$PATH` before Cursor's bundled one.

**Common commands:**

| Action             | Command                                          |
| ------------------ | ------------------------------------------------ |
| Start the backend  | `uv run --project backend python backend/run.py` |
| Start the frontend | `cd frontend && npm run dev`                     |
| Run tests          | `make test`                                      |
| Lint and format    | `make lint`                                      |

### Migrating from a previous Docker Compose setup

If you previously ran `docker compose up`, run `docker compose down --remove-orphans` once to clean up any leftover containers. This repo no longer uses Docker Compose; the only container in play is the dev container under `.devcontainer/`.

## Monorepo Structure

- `backend/`: Python application code, tests, and Python tooling configuration
- `frontend/`: React + TypeScript client for configuration editing and simulation results (Vitest + RTL + MSW); see [feature quickstart](docs/features/react-flask-migration/Development/quickstart.md) for running with the Flask API
- Root: orchestration (`Makefile`, CI/workspace config) and the dev container build (`.devcontainer/`)

### Command Contract

- Run developer and CI commands from the repository root.
- Backend commands are root-orchestrated and target `backend/` paths.

### Code Structure

- Application entry point: `backend/run.py`
- [Figma board](https://www.figma.com/file/UddWSekF9Sl6REDWII9dtr/LifeFinances-Functional-Tree?type=whiteboard&node-id=0%3A1&t=p6KDxEXCU2BdB7MZ-1) for intended structure (may not stay current)

### Flask HTTP API (`/api`)

The UI talks to Flask over JSON under the `/api` prefix (see `backend/app/__init__.py`). Contract and examples: [`docs/features/react-flask-migration/Development/contracts/openapi.yaml`](docs/features/react-flask-migration/Development/contracts/openapi.yaml).

| Method | Path                  | Role                                                                                                 |
| ------ | --------------------- | ---------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/config`         | Returns `{ "content": "<yaml string>" }` for the active file.                                        |
| `PUT`  | `/api/config`         | Body `{ "content": "<yaml string>" }` — validates against the `User` schema, then writes **`config.yml` in the process working directory** (typically the repo root). |
| `POST` | `/api/simulation/run` | Runs the simulator from the on-disk config; returns `success_percentage` and `first_result` (`columns` / `data` in pandas "split" form). |

**Working directory:** Start the backend from the repo root (`python backend/run.py` or `uv run --project backend python backend/run.py`) so `config.yml` resolves next to the checkout. If that file is missing, `GET /api/config` still returns YAML (fallback to `backend/tests/sample_configs/min_config_income.yml` for read-only display); `PUT` always targets `./config.yml` when no custom path is passed.

**Root URL `/`:** Returns **302** to the SPA. Override the target with **`FRONTEND_REDIRECT_URL`** (defaults to `http://localhost:5173/`).
# LifeFInances

## Run with Docker

To run the application without any development setup (Docker required):

1. Clone the repository and `cd` into it
2. Copy a sample config to the project root:
   ```bash
   cp tests/sample_configs/full_config.yml config.yml
   ```
   (Use `min_config_net_worth.yml` or `min_config_income.yml` for smaller examples.)
3. Start the application:
   ```bash
   docker compose up --build
   ```
4. Open http://localhost:3500 in your browser

---

## Developer Setup

### With DevContainer

The recommended way to develop. Requires [Docker](https://docs.docker.com/get-docker/), [VS Code](https://code.visualstudio.com/), and the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

**Installation:**
1. Clone the repository and open the folder in VS Code
2. Click **Reopen in Container** when prompted, or run **Dev Containers: Reopen in Container** from the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Wait for the container to build (first time may take a few minutes)

The container provides Python 3.10, all dependencies, pre-commit hooks, and a default `config.yml` if none exists. Port 3500 is forwarded for the Flask app.

**Pre-commit hooks:** Installed automatically. They run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`.

**Common commands (inside the container):**
| Action | Command |
|--------|---------|
| Start the Flask app | `flask run` |
| Run tests | `pytest` or `make test` |
| Lint and format | `make lint` |

### Without DevContainer

**Installation:**
1. Python 3.10 required. This project uses [uv](https://docs.astral.sh/uv/) for dependencies. From the top-level directory:
   ```bash
   uv sync
   ```
2. Copy a sample config:
   ```bash
   cp tests/sample_configs/full_config.yml config.yml
   ```
3. Review allocation options at [`app/data/README.md`](https://github.com/chriskelly/LifeFinances/blob/main/app/data/README.md)

**Pre-commit hooks:**
```bash
pre-commit install
```
Hooks run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`. To skip: `git commit --no-verify`.

**Common commands:**
| Action | Command |
|--------|---------|
| Start the Flask app | `uv run flask run` or `flask run` (after activating `.venv`) |
| Run tests | `pytest` or `make test` |
| Lint and format | `make lint` |

### Code Structure

- Application entry point: `run.py`
- [Figma board](https://www.figma.com/file/UddWSekF9Sl6REDWII9dtr/LifeFinances-Functional-Tree?type=whiteboard&node-id=0%3A1&t=p6KDxEXCU2BdB7MZ-1) for intended structure (may not stay current)

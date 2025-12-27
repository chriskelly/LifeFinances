# LifeFInances

## Dependencies
Supported for python version 3.10.

The code requires various packages, which are listed in the `requirements/` directory. Using virtual enviroments is recommended. To install them all at once, run the following command in the top-level directory of this repository.
```bash
pip install -r requirements/common.txt
```
or 
```bash
pip3 install -r requirements/common.txt
```
Developers should replace `common.txt` with `dev.txt`.


## Developer Setup

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality.

**Using DevContainer (VS Code):** Pre-commit hooks are automatically installed when the container is created. Skip to "What the hooks do" below.

**Without DevContainer:** Run these commands to set up:

1. Install dependencies:
   ```bash
   pip install -r requirements/dev.txt
   ```

2. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

**What the hooks do:**

The hooks will run automatically before each commit, executing:
- Docker build (if not in devcontainer)
- All tests via pytest
- Linting (ruff check, ruff format, pyright)
- The first commit takes longer, but subsequent tests run within 2-4 seconds

To run hooks manually without committing:
```bash
pre-commit run --all-files
```
or to just run tests & linting direclty
```bash
make
```

To skip hooks temporarily (not recommended):
```bash
git commit --no-verify
```


## First Time Usage
More documentation is still pending. In the meantime, feel free to open an issue with questions about usage.

Without Docker:
- Install the dependencies (see above)
- Look at the configs in `tests/sample_configs/` and copy the config you want to start with to the root directory under the name `config.yml`
- Review the options for allocation at [`app/data/README.md`](https://github.com/chriskelly/LifeFinances/blob/main/app/data/README.md)
- Run `flask run` from your terminal

With DevContainer (VS Code):
- Ensure you have Docker installed and running
- Open the repository in VS Code
- When prompted, click "Reopen in Container" or use the Command Palette (Ctrl+Shift+P / Cmd+Shift+P) and select "Dev Containers: Reopen in Container"
- The devcontainer will automatically:
  - Build the container with Python 3.10 and development dependencies
  - Install required packages from `requirements/dev.txt`
  - Create a default `config.yml` from `tests/sample_configs/full_config.yml` if one doesn't exist
  - Install pre-commit hooks automatically
  - Forward port 3500 for the Flask application
- Once the container is running, you can:
  - Run `flask run` to start the application (port 3500 will be automatically forwarded)
  - Run tests using `pytest` (configured to run from the `tests` directory)
  - Use the integrated Python debugger and linting tools


## Code Structure
- Application entry point is `/run.py`
- While this may not stay up-to-date, you can view this [Figma board](https://www.figma.com/file/UddWSekF9Sl6REDWII9dtr/LifeFinances-Functional-Tree?type=whiteboard&node-id=0%3A1&t=p6KDxEXCU2BdB7MZ-1) to see a visual representation of the intended structure.
  
  

# Strip-down Dockerization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the Docker Compose stack, collapse the Makefile, and run CI inside the existing devcontainer image with GHCR layer caching, while rewriting onboarding docs to lead with the devcontainer.

**Architecture:** The repo retains exactly one container artifact — `.devcontainer/Dockerfile` — which serves both local development (VS Code Reopen in Container) and CI (`devcontainers/ci@v0.3` builds and runs commands inside it, with cache pulled from `ghcr.io/<repo>-devcontainer` and pushed only on `main`). All `make` targets become single-branch host-direct invocations of `uv` and `npm`, so they behave the same on a contributor laptop, inside the devcontainer, and inside the CI runner.

**Tech Stack:** Make, Docker (devcontainer only), GitHub Actions, `devcontainers/ci@v0.3`, GHCR, `uv`, Vite/Vitest, pytest, ruff, pyright.

**Spec:** [`spec.md`](spec.md). Read it before starting — task acceptance criteria reference §5 of the spec.

---

## File structure

| File | Action | Responsibility after change |
|---|---|---|
| `Makefile` | rewrite | Single-branch host-direct targets: `test`, `ruff-check`, `ruff-format-check`, `pyright`, `lint`, `coverage`, `profile`, `all`. No Compose, no env detection. |
| `.github/workflows/main_ci.yml` | rewrite | One job, `ubuntu-latest`, runs `make test` and `make lint` inside the devcontainer image via `devcontainers/ci@v0.3`. Reads cache from GHCR; pushes cache only on `main`. |
| `docker-compose.yml` | delete | n/a |
| `backend/Dockerfile` | delete | n/a |
| `frontend/Dockerfile` | delete | n/a |
| `README.md` | edit | Devcontainer-first onboarding. Drops "Run with Docker" section. Drops Compose-specific port/redirect-URL notes. |
| `frontend/README.md` | edit | Drops the "Docker Compose" subsection. |
| `.devcontainer/*` | unchanged | Local + CI container source of truth. |
| `.dockerignore` | unchanged | Still applies to devcontainer build context. |
| `backend/app/__init__.py` | unchanged | `FRONTEND_REDIRECT_URL` default `http://localhost:5173/` already correct. |
| `frontend/vite.config.ts` | unchanged | `API_PROXY_TARGET` default `http://127.0.0.1:3500` already correct. |

---

## Task 0: Branch setup and pre-flight verification

**Files:**
- (no edits; environment setup only)

- [ ] **Step 0.1: Confirm clean working tree on `main`**

```bash
git status
git rev-parse --abbrev-ref HEAD
```

Expected: `nothing to commit, working tree clean` and `main`. If the branch is already a feature branch from a previous attempt, that's fine; skip Step 0.2.

- [ ] **Step 0.2: Create the feature branch**

```bash
git switch -c feature/strip-down-dockerization
```

Expected: `Switched to a new branch 'feature/strip-down-dockerization'`.

- [ ] **Step 0.3: Verify the existing CI/Makefile baseline passes locally**

This is the regression baseline — the same commands must continue to pass after each subsequent task.

```bash
make test
make lint
```

Expected: both pass. If they don't, **stop**: this plan assumes a green baseline. Resolve the failure before continuing.

- [ ] **Step 0.4: Verify that the gitignored research note exists locally (sanity check, optional)**

```bash
ls docs/features/strip-down-dockerization/Research/
```

Expected: `evaluation.md` (or empty if running in a fresh clone). Either is fine — `Research/` is gitignored.

---

## Task 1: Collapse the Makefile to a single host-direct branch

**Files:**
- Modify (full rewrite): `Makefile`

**Why:** The current Makefile double-implements every target (host vs. Compose). With Compose gone, the Compose branch is dead code and the env detection (`DOCKER_COMPOSE`, `IN_DEVCONTAINER`, `USE_DIRECT`, `COMPOSE_SERVICE`) becomes irrelevant. The collapsed version works identically on the host, in the devcontainer, and in CI.

- [ ] **Step 1.1: Capture the current `make test` and `make lint` durations and outputs**

Used as a regression check across this task and Task 4.

```bash
time make test 2>&1 | tail -20
time make lint 2>&1 | tail -20
```

Expected: both PASS, durations recorded for comparison.

- [ ] **Step 1.2: Rewrite `Makefile`**

Replace the entire contents with the following:

```makefile
all: test lint

test:
	uv run --project backend pytest backend/tests && cd frontend && npm run test:run

ruff-check:
	uv run --project backend ruff check backend

ruff-format-check:
	uv run --project backend ruff format --check backend

pyright:
	uv run --project backend pyright -p backend/pyrightconfig.json

lint: ruff-check ruff-format-check pyright

coverage:
	uv run --project backend pytest backend/tests --cov=backend/app --cov-report=term-missing --cov-report=html

profile:
	uv run --project backend python -m cProfile -o backend/tests/profiling/results/gen_trials.prof backend/tests/profiling/gen_trials.py
	uv run --project backend snakeviz backend/tests/profiling/results/gen_trials.prof
```

Notes:
- `DOCKER_BUILDKIT` env export is removed — it only affected `docker compose build`, which is gone.
- `build`, `up`, `down` targets are removed — Compose-only.
- `COMPOSE_SERVICE`, `USE_DIRECT`, `IN_DEVCONTAINER`, `DOCKER_COMPOSE` variables are removed.
- All `ifeq` branching is removed.

- [ ] **Step 1.3: Verify no Compose references remain in the new Makefile**

```bash
rg -n "docker compose|docker-compose|USE_DIRECT|IN_DEVCONTAINER|COMPOSE_SERVICE|DOCKER_COMPOSE|^build:|^up:|^down:" Makefile || echo "clean"
```

Expected: `clean`.

- [ ] **Step 1.4: Verify `make test` and `make lint` still pass after the rewrite**

Same regression baseline as Step 1.1.

```bash
make test
make lint
```

Expected: both PASS. The output of `make test` should now show `uv run --project backend pytest …` directly (no `docker compose run` invocation). If it still shells out to Docker, the Makefile rewrite didn't take.

- [ ] **Step 1.5: Commit**

```bash
git add Makefile
git commit -m "build: collapse Makefile to single host-direct branch

Removes the docker compose path and the env detection (USE_DIRECT,
IN_DEVCONTAINER, COMPOSE_SERVICE, DOCKER_COMPOSE) used to switch
between host and Compose execution. Drops the Compose-only build/up/
down targets. Remaining targets (test, lint, ruff-check,
ruff-format-check, pyright, coverage, profile, all) run uv/npm
directly and behave the same on host, in the devcontainer, and in CI.

Compose stack files are still on disk at this commit; subsequent
commits remove them and rewrite CI to use the devcontainer image."
```

---

## Task 2: Rewrite `.github/workflows/main_ci.yml` to run on the devcontainer image

**Files:**
- Modify (full rewrite): `.github/workflows/main_ci.yml`

**Why:** Run CI inside the same image VS Code uses locally, with GHCR layer caching, so steady-state CI hits cache for the expensive layers (apt + nvm install of Node 24, `uv sync` of the Python venv) and avoids the Docker Hub flake that motivated the current 3× retry loop.

**Image naming gotcha:** GHCR requires lowercase image references. `${{ github.repository }}` preserves the source-of-truth case (`chriskelly/LifeFInances`), which would be rejected. The plan computes a lowercase variant once and reuses it.

- [ ] **Step 2.1: Replace the workflow file**

Replace the entire contents of `.github/workflows/main_ci.yml` with the following. The inline comments are part of the deliverable — they document the non-obvious mechanics for future maintainers (GHCR's lowercase requirement, the cache-push-only-on-main semantics, why there are two `devcontainers/ci` invocations).

```yaml
name: Main CI

on:
  push:
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    # `packages: write` is required so devcontainers/ci can push the built layer
    # cache to ghcr.io/<repo>-devcontainer on main. PR runs read cache but do not
    # write (see `push: filter` + `refFilterForPush` below).
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      # GHCR rejects uppercase characters in image references. `github.repository`
      # preserves source-of-truth case (e.g. "Owner/RepoName"), so we lowercase it
      # once and reuse the result via `steps.image.outputs.name` below. Doing this
      # in a step rather than hard-coding keeps the workflow portable across forks
      # and renames.
      - name: Compute lowercase image name
        id: image
        run: |
          repo_lower=$(echo "${{ github.repository }}" | tr '[:upper:]' '[:lower:]')
          echo "name=ghcr.io/${repo_lower}-devcontainer" >> "$GITHUB_OUTPUT"

      # Authenticates this job's docker client to ghcr.io using the workflow's
      # built-in GITHUB_TOKEN. Required for both pulling cached layers (cacheFrom)
      # and pushing them on main. No org-level secrets needed.
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      # The backend reads ./config.yml at startup. This step runs on the runner,
      # not inside the container, but devcontainers/ci mounts the workspace, so
      # the file is visible at /workspace/config.yml inside the container.
      - name: Create user config
        run: cp backend/tests/sample_configs/full_config.yml config.yml

      # Builds .devcontainer/Dockerfile (with cache pulled from GHCR) and runs
      # `make test` inside the resulting image. This image is the same one VS Code
      # uses locally for "Reopen in Container", so dev/CI parity is real.
      #
      # cacheFrom + imageName: pull existing layer cache from this image ref before
      #   building; tag the freshly built image with the same ref.
      # push: filter + refFilterForPush: refs/heads/main: only push the new cache
      #   image when the workflow runs on the main branch. PR runs reuse main's
      #   cache without overwriting it, preventing cache thrash from concurrent PRs.
      - name: Run tests in devcontainer
        uses: devcontainers/ci@v0.3
        with:
          imageName: ${{ steps.image.outputs.name }}
          cacheFrom: ${{ steps.image.outputs.name }}
          push: filter
          refFilterForPush: refs/heads/main
          runCmd: make test

      # Separate devcontainers/ci invocation (one for test, one for lint) so that
      # failures attribute distinctly in the GitHub Checks UI. The lint step
      # reuses the image just built by the test step above (cacheFrom hits every
      # layer), so its build phase is near-instant.
      #
      # push: never because the test step already handled this run's cache push;
      # pushing again here would be redundant.
      - name: Run lint in devcontainer
        uses: devcontainers/ci@v0.3
        with:
          imageName: ${{ steps.image.outputs.name }}
          cacheFrom: ${{ steps.image.outputs.name }}
          push: never
          runCmd: make lint
```

Other notes (not in the YAML):
- The 3× Docker-Hub retry loop from the previous workflow is gone because the steady-state warm-cache path doesn't pull base images at all. Cold builds (when the devcontainer files change) still go through Docker Hub for `python:3.10`, `node:24` (via nvm), and `astral-sh/uv`; if those become flaky in the future, escalate by digest-pinning or mirroring those bases to GHCR.

- [ ] **Step 2.2: YAML lint locally if a linter is available, otherwise visual check**

```bash
# If yamllint is installed:
yamllint -d "{extends: default, rules: {line-length: disable, indentation: {spaces: 2}}}" .github/workflows/main_ci.yml || echo "(yamllint not installed; skipping)"

# Always:
cat .github/workflows/main_ci.yml
```

Expected: no syntax errors; the file matches the snippet in Step 2.1.

- [ ] **Step 2.3: Commit**

```bash
git add .github/workflows/main_ci.yml
git commit -m "ci: run main_ci on the devcontainer image with GHCR layer caching

Replaces the Compose-based 'make test' (with 3x Docker Hub retry) and
'make lint' steps with two devcontainers/ci@v0.3 invocations that
build and run inside .devcontainer/Dockerfile. Pulls layer cache from
ghcr.io/<repo>-devcontainer on every run; pushes cache only on main
(push: filter + refFilterForPush). Authenticates via the workflow's
GITHUB_TOKEN with packages: write.

The Docker Hub flake retry loop is removed because steady-state runs
hit cache and don't re-pull base images. Cold runs (e.g. when the
devcontainer files change) still fall through to the bases; if those
flake in the future the next escalation is digest-pinning or
mirroring to GHCR.

Compose stack files are still on disk at this commit; the next commit
removes them now that CI no longer references them."
```

---

## Task 3: Push as a draft PR and verify the cold-cache CI run

**Files:**
- (no edits; CI validation)

**Why:** The CI workflow can only be exercised on GitHub Actions. We push and observe before deleting Compose files, so that if the new CI fails outright we can iterate on `main_ci.yml` without having to re-add deleted files.

- [ ] **Step 3.1: Push the branch**

```bash
git push -u origin feature/strip-down-dockerization
```

Expected: branch published to origin.

- [ ] **Step 3.2: Open a draft PR**

```bash
gh pr create --draft \
  --title "Strip down Dockerization (B): keep devcontainer, drop Compose" \
  --body "$(cat <<'EOF'
Implements the design in `docs/features/strip-down-dockerization/Development/spec.md`.

## Status

- Draft. Compose files still on disk at this point so the new CI can be exercised before deletion (per §8 of the spec).

## Validation receipts (filled in as commits land)

- [ ] Cold-cache CI run duration (this commit, before deletion): _TBD_
- [ ] First `main` run after merge (cache publish): _TBD_
- [ ] Warm-cache PR follow-up: _TBD_
- [ ] Reopen in Container in VS Code still works: _TBD_

## Sequencing

1. Already on branch: spec docs (already on `main`).
2. Already on branch: Makefile collapse.
3. Already on branch: CI rewrite to devcontainers/ci@v0.3.
4. Pending: delete docker-compose.yml, backend/Dockerfile, frontend/Dockerfile.
5. Pending: README + frontend/README rewrites.
EOF
)"
```

Expected: PR created in draft state. Note the PR URL.

- [ ] **Step 3.3: Watch the cold-cache CI run**

```bash
gh pr checks --watch
```

Expected: both `Run tests in devcontainer` and `Run lint in devcontainer` steps complete successfully. The build step inside each invocation will be slow (likely 3–6 minutes for the first run on the test step) because the GHCR cache is empty. The second invocation (`Run lint…`) reuses the just-built image and should be near-instant on the build phase.

If CI fails on:
- **`Compute lowercase image name`** — typo in the shell heredoc; re-check Step 2.1.
- **GHCR `denied: denied`** during cache push — this means `packages: write` is not effective in the org/repo settings. Workaround: change `push: filter` to `push: never` on the test step. Re-push and re-run; cache will not be persisted but CI will still work.
- **`make test` fails** — open the run logs and diff the failure against the local `make test` output from Step 1.4 / 0.3. If the failure is environmental (e.g. `config.yml` missing), confirm the `Create user config` step ran. If the failure is real (an actual test fault), it's not introduced by this change — that's a pre-existing problem on `main` and should be triaged separately.

Record the run duration in the PR description's "Validation receipts" checklist.

- [ ] **Step 3.4: Confirm GHCR image was *not* yet published (filter sanity check)**

This run is on a feature branch, not `main`, so `push: filter` + `refFilterForPush: refs/heads/main` should have suppressed any push. Verify:

```bash
gh api "/users/chriskelly/packages?package_type=container" \
  --jq '.[] | select(.name | endswith("lifefinances-devcontainer")) | .name'
```

Expected: empty output. The `lifefinances-devcontainer` package will only appear after the eventual merge to `main`.

If a package entry is already present, the filter is misconfigured — revisit Step 2.1's `refFilterForPush` value.

- [ ] **Step 3.5: No commit needed for this task**

Validation only.

---

## Task 4: Delete the Compose stack

**Files:**
- Delete: `docker-compose.yml`
- Delete: `backend/Dockerfile`
- Delete: `frontend/Dockerfile`

**Why:** Now that CI no longer references these files (Task 2) and the Makefile no longer uses them (Task 1), they are unreferenced. Deleting them is the actual "strip down."

- [ ] **Step 4.1: Confirm nothing on the branch references the files anymore**

```bash
rg -n "docker-compose\.yml|docker compose|backend/Dockerfile|frontend/Dockerfile" \
  --glob '!docs/features/**' \
  --glob '!docs/ideas/**' \
  --glob '!docs/backlog/**' \
  --glob '!specs/**' \
  --glob '!.git/**' \
  || echo "clean (excluding planning docs and historical specs)"
```

Expected: `clean`. Hits inside `docs/features/strip-down-dockerization/` (this plan and the spec) and inside `docs/features/react-flask-migration/` are expected and intentional — those are documentation about the change and historical record respectively.

- [ ] **Step 4.2: Delete the three files**

```bash
git rm docker-compose.yml backend/Dockerfile frontend/Dockerfile
```

Expected: `rm 'docker-compose.yml'`, `rm 'backend/Dockerfile'`, `rm 'frontend/Dockerfile'`.

- [ ] **Step 4.3: Verify `make test` and `make lint` still pass locally with the files gone**

```bash
make test
make lint
```

Expected: both PASS. The Makefile from Task 1 doesn't reference these files, so deletion has no local effect.

- [ ] **Step 4.4: Verify .dockerignore is still relevant (sanity)**

```bash
cat .dockerignore
ls .devcontainer/Dockerfile
```

Expected: `.dockerignore` still exists with `__pycache__`, `.venv`, etc. The devcontainer Dockerfile build context honors it via `COPY . /workspace`. Do **not** delete `.dockerignore`.

- [ ] **Step 4.5: Commit**

```bash
git commit -m "build: remove docker-compose stack and service Dockerfiles

Deletes docker-compose.yml, backend/Dockerfile, and frontend/Dockerfile
now that nothing in the repo references them. The Makefile no longer
shells out to docker compose (collapsed to single host-direct branch)
and CI no longer builds these images (now runs inside the
devcontainer image via devcontainers/ci@v0.3 with GHCR layer cache).

.devcontainer/Dockerfile, devcontainer.json, post-create.sh, and
.dockerignore are intentionally retained as the single container
artifact, used by both VS Code (Reopen in Container) and CI."
```

- [ ] **Step 4.6: Push and observe a second CI run on the post-deletion state**

```bash
git push
gh pr checks --watch
```

Expected: CI passes. Build duration may be slightly faster than the cold-cache run because the cache was warmed on the test step's build (`push: filter` would have been the only thing skipping cache push, not the build itself; `cacheFrom` always pulls). If duration is identical, that's fine — the warm path proves itself after merge.

---

## Task 5: Rewrite the root `README.md` for devcontainer-first onboarding

**Files:**
- Modify: `README.md`

**Why:** The "Run with Docker" section advertised `docker compose up --build` and is now broken. Promoting "With DevContainer" to the primary developer setup path keeps onboarding documented while removing the dead advice and the Compose-specific port aside.

- [ ] **Step 5.1: Replace the entire `README.md` with the new content**

Write the file:

```markdown
# LifeFInances

A simulator for personal finances and retirement planning. The app is a Python (Flask) backend with a React + TypeScript frontend.

## Developer Setup

### With DevContainer (recommended)

Requires [Docker](https://docs.docker.com/get-docker/), [VS Code](https://code.visualstudio.com/), and the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

**Installation:**
1. Clone the repository and open the folder in VS Code
2. Click **Reopen in Container** when prompted, or run **Dev Containers: Reopen in Container** from the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Wait for the container to build (first time may take a few minutes)

The container provides Python 3.10, Node.js, all dependencies, pre-commit hooks, and a default `config.yml` if none exists. Port **3500** is forwarded for the Python backend (matches `python backend/run.py`, which binds **`0.0.0.0:3500`**) and port **5173** for the React frontend.

**Pre-commit hooks:** Installed automatically. They run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`.

**Common commands (inside the container):**
| Action | Command |
|--------|---------|
| Start the backend | `python backend/run.py` |
| Start the frontend | `cd frontend && npm run dev` |
| Run tests | `make test` |
| Lint and format | `make lint` |

### Without DevContainer

**Installation:**
1. Python 3.10 required. This project uses [uv](https://docs.astral.sh/uv/) for dependencies. From the top-level directory:
   ```bash
   uv sync --project backend
   ```
2. Node.js `^20.19.0 || ^22.12.0 || >=24.0.0` is required by the frontend test stack (jsdom → html-encoding-sniffer → @exodus/bytes needs `require(ESM)` support). The repo pins a default in `.nvmrc`:
   ```bash
   # with nvm
   nvm install   # reads .nvmrc
   nvm use
   ```
   Without nvm, install a compatible Node via your package manager / `fnm` / `volta` / `asdf` / `mise`. The pre-commit wrapper checks the active version and fails fast with a clear message if it is too old.
3. Copy a sample config:
   ```bash
   cp backend/tests/sample_configs/full_config.yml config.yml
   ```
   (Use `min_config_net_worth.yml` or `min_config_income.yml` for smaller examples.)
4. Review allocation options at [`backend/app/data/README.md`](https://github.com/chriskelly/LifeFinances/blob/main/backend/app/data/README.md)

**Pre-commit hooks:**
```bash
pre-commit install
```
Hooks run before each commit (tests, linting). To run manually: `pre-commit run --all-files` or `make`. To skip: `git commit --no-verify`.

> **Note on Node + Cursor IDE:** Cursor Server bundles `node v20.18.2` and prepends it to `$PATH` for git operations launched from the IDE. That version is too old to `require()` ESM modules and will break the frontend test suite. The pre-commit hook is wrapped by [`scripts/precommit.sh`](scripts/precommit.sh), which sources nvm (if installed) and validates the resulting Node version before running `make`. If you don't use nvm, make sure a compatible Node appears on `$PATH` before Cursor's bundled one.

**Common commands:**
| Action | Command |
|--------|---------|
| Start the backend | `uv run --project backend python backend/run.py` |
| Start the frontend | `cd frontend && npm run dev` |
| Run tests | `make test` |
| Lint and format | `make lint` |

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

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/config` | Returns `{ "content": "<yaml string>" }` for the active file. |
| `PUT` | `/api/config` | Body `{ "content": "<yaml string>" }` — validates against the `User` schema, then writes **`config.yml` in the process working directory** (typically the repo root). |
| `POST` | `/api/simulation/run` | Runs the simulator from the on-disk config; returns `success_percentage` and `first_result` (`columns` / `data` in pandas "split" form). |

**Working directory:** Start the backend from the repo root (`python backend/run.py` or `uv run --project backend python backend/run.py`) so `config.yml` resolves next to the checkout. If that file is missing, `GET /api/config` still returns YAML (fallback to `backend/tests/sample_configs/min_config_income.yml` for read-only display); `PUT` always targets `./config.yml` when no custom path is passed.

**Root URL `/`:** Returns **302** to the SPA. Override the target with **`FRONTEND_REDIRECT_URL`** (defaults to `http://localhost:5173/`).
```

Use the `Write` tool with the path `/workspace/README.md` and the contents above.

- [ ] **Step 5.2: Verify no Compose references remain in the new README**

```bash
rg -n "docker compose|docker-compose|:5174|host 5174" README.md || echo "clean"
```

Expected: `clean` *except* for the "Migrating from a previous Docker Compose setup" subsection, which deliberately mentions `docker compose down --remove-orphans` once. If `rg` matches that single line and nothing else, that's correct.

- [ ] **Step 5.3: Verify markdown links still resolve to existing files**

```bash
rg -no '\[[^]]*\]\(([^)]+)\)' -r '$1' README.md \
  | grep -v '^http' \
  | grep -v '^#' \
  | while read -r path; do
      [ -e "$path" ] || echo "MISSING: $path"
    done
echo "(any 'MISSING: ...' lines above are broken links)"
```

Expected: no `MISSING:` lines.

- [ ] **Step 5.4: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for devcontainer-first onboarding

Drops the 'Run with Docker' section that advertised docker compose up
--build (no longer functional). Promotes the DevContainer path to the
primary developer setup. Updates the Monorepo Structure line that
listed Dockerfile/docker-compose.yml in root. Drops the host-port
collision aside about 5174<->5173 and the Compose-specific
FRONTEND_REDIRECT_URL note (the env var still exists in code; only
the Compose-set value goes away).

Adds a short 'Migrating from a previous Docker Compose setup'
subsection with the docker compose down --remove-orphans cleanup
hint."
```

---

## Task 6: Drop the Docker Compose subsection from `frontend/README.md`

**Files:**
- Modify: `frontend/README.md`

**Why:** The subsection explains a Compose-only `API_PROXY_TARGET=http://backend:3500` override that no longer applies. The default fallback in `vite.config.ts` (`http://127.0.0.1:3500`) already handles host-direct and devcontainer-forwarded development.

- [ ] **Step 6.1: Delete the "### Docker Compose" subsection**

Use the `StrReplace` tool on `/workspace/frontend/README.md`.

`old_string` (verbatim, including leading and trailing blank lines):

```
Call the backend from the browser via relative URLs, e.g. `fetch('/api/...')`, so traffic stays on the Vite origin and goes through the proxy.

### Docker Compose

The repo’s `docker-compose.yml` sets **`API_PROXY_TARGET=http://backend:3500`** on the `frontend` service so Vite proxies `/api` to the backend by Docker service name (backend listens on **3500** inside its container; the host maps **3501→3500** for direct API access from the host).

If you run a custom Compose layout without that variable, `localhost` inside the frontend container is **not** the backend — set `API_PROXY_TARGET` to a URL reachable from the frontend container (same idea as the feature [quickstart](../../react-flask-migration/Development/quickstart.md#docker-compose)).

## Scripts
```

`new_string` (verbatim):

```
Call the backend from the browser via relative URLs, e.g. `fetch('/api/...')`, so traffic stays on the Vite origin and goes through the proxy.

## Scripts
```

Note: the apostrophe in "repo's" in the source is the curly Unicode `'` (U+2019), not a straight ASCII `'`. Copy from the existing file rather than retyping to preserve the byte-exact match.

- [ ] **Step 6.2: Verify nothing else in the file references Compose**

```bash
rg -n "docker compose|docker-compose|API_PROXY_TARGET=http://backend" frontend/README.md || echo "clean"
```

Expected: `clean`. The `API_PROXY_TARGET` env var name itself may still appear as part of the surviving "Backend API and the Vite proxy" paragraph (where it's correctly described as an override) — that's fine, the search above only catches the Compose-specific URL form.

- [ ] **Step 6.3: Commit**

```bash
git add frontend/README.md
git commit -m "docs(frontend): drop Docker Compose subsection from README

The subsection described an API_PROXY_TARGET=http://backend:3500
override only meaningful inside docker-compose.yml. With Compose
removed, the default fallback in vite.config.ts
(http://127.0.0.1:3500) already serves both host-direct and
devcontainer-forwarded development."
```

---

## Task 7: Final validation receipts and ready-for-review

**Files:**
- (no edits; PR validation and metadata)

**Why:** Spec §5.4 requires the implementing PR to record three CI-duration receipts and a smoke-check that VS Code's `Reopen in Container` still works. This is the final acceptance gate.

- [ ] **Step 7.1: Push the latest commits and observe the CI run**

```bash
git push
gh pr checks --watch
```

Expected: both `Run tests in devcontainer` and `Run lint in devcontainer` succeed. Record the duration in PR description ("Cold-cache CI run duration"). This is still a feature branch, so cache is read-only — duration may already be slightly improved over Task 3.3 because the lint step was warmed by the test step.

- [ ] **Step 7.2: Smoke-check VS Code DevContainer still works**

This is the only step the engineer must do interactively (it cannot be scripted from the agent's side):

1. Pull the branch locally in VS Code.
2. Run **Dev Containers: Rebuild and Reopen in Container**.
3. After the build finishes, open a terminal inside the container and run `make test && make lint`.

Expected: both succeed. Tick the "Reopen in Container in VS Code still works" box in the PR description.

If this fails, it's almost certainly because `.devcontainer/Dockerfile` was unintentionally affected — but this plan does not modify it, so review the diff before debugging further.

- [ ] **Step 7.3: Mark the PR ready for review**

```bash
gh pr ready
```

- [ ] **Step 7.4: After merge, capture the `main` cache-publish run**

Once a maintainer merges the PR:

```bash
gh run list --workflow=main_ci.yml --branch main --limit 1
```

Take note of the duration of the first `main` run after merge — this is the cold cache publish. Add it to the PR description retroactively as a comment ("First `main` run after merge (cache publish): X minutes").

- [ ] **Step 7.5: Verify GHCR image is now published**

```bash
gh api "/users/chriskelly/packages?package_type=container" \
  --jq '.[] | select(.name | endswith("lifefinances-devcontainer")) | {name, html_url}'
```

Expected: a package entry exists with a `html_url` pointing to the package page. Open that URL in a browser and confirm at least one tag/version is listed.

- [ ] **Step 7.6: Open a trivial follow-up PR to prove warm-cache reuse**

Open a PR that touches a single comment in the README or a different docs file (anything that does **not** invalidate `.devcontainer/Dockerfile`'s layers). Run CI. The build phase of `Run tests in devcontainer` should drop from minutes to seconds.

```bash
git switch main && git pull
git switch -c chore/verify-warm-cache
# Make a trivial edit, e.g.
echo "" >> README.md
git add README.md
git commit -m "chore: trivial edit to verify CI warm-cache reuse"
git push -u origin chore/verify-warm-cache
gh pr create --draft --title "chore: verify CI warm cache" --body "Verification PR for the strip-down-dockerization rollout. Close without merging once the receipts are recorded."
gh pr checks --watch
```

Record the warm-cache duration in the original strip-down PR description. Close the verification PR without merging.

---

## Self-review pointers (not a task — done by the plan author)

- §5 (Acceptance criteria) of the spec maps to: §5.1 → covered by the spec/`.gitignore` commits already on `main`; §5.2 → Tasks 1, 4; §5.3 → Tasks 2, 3, 4, 7; §5.4 → Task 7.
- §6 (Risks): R1 acknowledged in Task 3.3 and Task 7.4; R2 fallback documented in spec §3 (not in this plan because it's a contingency); R3 mitigated by cache hits and by Task 3.3's failure-mode notes; R4 has an explicit workaround in Task 3.3; R5 covered by README's "Migrating…" subsection; R6 covered by audit notes in spec §4.7 and Task 4.1's exclusion-aware ripgrep.

If you reach the end of Task 7 and any acceptance criterion is unmet, **do not** merge the PR.

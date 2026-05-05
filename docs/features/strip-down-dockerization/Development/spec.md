# Spec: Strip down Dockerization

Status: Design approved, awaiting plan
Last updated: 2026-05-04

## 1. Context

The repo currently ships three independent Docker assets:

1. **A Docker Compose stack** (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`) used only for the README's "no-setup" `docker compose up --build` flow. There is no production deployment.
2. **A devcontainer** (`.devcontainer/Dockerfile`, `devcontainer.json`, `post-create.sh`) — the recommended local dev environment in VS Code.
3. **Compose-flavored CI** (`.github/workflows/main_ci.yml` runs `make test` / `make lint`, which invoke the Compose stack on the runner). The job is wrapped in a 3× retry loop explicitly labelled "with retry on Docker Hub errors" — direct evidence of CI flakiness.

The Compose layer is the part that "trips CI" and is the least-justified now that there are no users or deployment. The devcontainer is independent of Compose and is the part contributors and agents still benefit from.

## 2. Trade-off summary

Four options were considered.

| Concern | A: Strip all | **B: Keep devcontainer (chosen)** | C: Keep Compose | D: Status quo |
|---|---|---|---|---|
| Maintenance surface | Lowest | Low | Medium | Highest |
| CI Docker Hub flake | Gone | Gone | Stays | Mitigated |
| "One-command try-it-out" UX | Lost | Lost | Kept | Kept |
| Reproducible dev env | Host-only | Container available | Host-only | Container available |
| Agent / external-tool friendliness | Best | Better | Better | Same as today |
| Makefile complexity | 1 branch | 1 branch | 2 branches | 2 branches |
| Effort to land | Medium | Small | Small | Smallest |

**Option B chosen** because it deletes the part that flakes (Compose) while keeping the part contributors actually use (devcontainer), and it lets CI run on the same image as local dev.

## 3. CI strategy

CI will run inside the devcontainer image via the official [`devcontainers/ci@v0.3`](https://github.com/devcontainers/ci) action, with layer cache pulled from and (on `main` only) pushed to GHCR.

**Why this approach** (vs. native runner with `setup-uv` + `setup-node`, or pre-built GHCR image in a separate workflow):

- Lowest YAML surface — single action wraps the entire build/run flow.
- Genuine dev/CI parity — the same image VS Code uses locally runs CI.
- First-party caching — `cacheFrom`/`imageName` use GHCR transparently.
- One workflow file to maintain (no separate "build and publish" pipeline).
- Authentication is already available via `GITHUB_TOKEN` with `packages: write`.

**Cache behavior** (high-level):

- Each layer in `.devcontainer/Dockerfile` is hashed by its inputs (instruction text + file contents for `COPY`, command string for `RUN`).
- The expensive layers (`apt-get` + nvm install of Node 24, and `uv sync` of the Python venv) almost never change, so steady-state CI hits cache for them and finishes in seconds.
- PRs read cache from GHCR but do not write to it; only `main` pushes new cache. This keeps the cache clean and avoids thrashing from concurrent PRs.

**Fallback** (documented for the reviewer, not adopted unless needed): if `devcontainers/ci@v0.3` regresses, the workflow can be reverted to a native runner using `astral-sh/setup-uv` and `actions/setup-node`. This trades dev/CI parity for simplicity but keeps the project green.

## 4. Repository changes

### 4.1 Files deleted

- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

### 4.2 Files kept (and why)

- `.devcontainer/Dockerfile` — single container artifact, used by VS Code locally and by CI.
- `.devcontainer/devcontainer.json` — drives local devcontainer + read by `devcontainers/ci@v0.3`.
- `.devcontainer/post-create.sh` — still runs on container create for local dev.
- `.dockerignore` — still applies to `COPY . /workspace` in the devcontainer build.

### 4.3 `Makefile` collapse

Today every target has two branches keyed on `USE_DIRECT` (host vs. Compose). After the change, the Compose branch is gone and the Makefile has a single host-direct branch that works identically on a contributor laptop, inside the devcontainer, and inside CI.

Targets removed: `build`, `up`, `down` (Compose-only). Targets retained, simplified: `test`, `ruff-check`, `ruff-format-check`, `pyright`, `lint`, `coverage`, `profile`. Detection blocks (`DOCKER_COMPOSE`, `IN_DEVCONTAINER`, `USE_DIRECT`, `COMPOSE_SERVICE`) all deleted.

### 4.4 `.github/workflows/main_ci.yml` rewrite

- Replace `make test` (with 3× retry) and `make lint` steps with two `devcontainers/ci@v0.3` invocations — one running `make test`, one running `make lint`. Two invocations (not one combined `make all`) so failures attribute correctly in the GitHub Checks UI.
- Add `permissions: contents: read; packages: write`.
- Add a `docker/login-action@v3` step authenticating to `ghcr.io` with `GITHUB_TOKEN`.
- Configure `imageName: ghcr.io/${{ github.repository }}-devcontainer` and `cacheFrom: ghcr.io/${{ github.repository }}-devcontainer` on each invocation.
- Set `push: filter` + `refFilterForPush: refs/heads/main` on the test step (only `main` writes cache).
- Set `push: never` on the lint step (it reuses the just-built image).
- Delete the 3× Docker-Hub-flake retry loop.

### 4.5 `README.md` rewrite

- Drop the entire **"Run with Docker"** section.
- Promote **"With DevContainer"** to the primary developer setup path (largely existing copy, minus references to Compose).
- Keep **"Without DevContainer"** as the secondary path.
- Update the "Monorepo Structure" line that mentions `Dockerfile`/`docker-compose.yml`.
- Drop the host-port-collision aside about 5174 ↔ 5173 and `FRONTEND_REDIRECT_URL` (only existed because of Compose).
- Add a short cleanup note for anyone who previously ran `docker compose up`: `docker compose down --remove-orphans` once.

### 4.6 `frontend/README.md` rewrite

- Delete the **"### Docker Compose"** subsection (lines 48–52 today). It explains a Compose-specific `API_PROXY_TARGET` override that no longer applies.
- The default `API_PROXY_TARGET=http://localhost:3501` already works for both host-direct and devcontainer-forwarded dev; no other edits needed.

### 4.7 Files explicitly *not* edited

- `backend/app/__init__.py` — reads `FRONTEND_REDIRECT_URL` with default `http://localhost:5173/`. The default is correct for both supported dev paths; only the Compose override (`http://localhost:5174/`) goes away with Compose.
- `frontend/vite.config.ts` — reads `API_PROXY_TARGET` with default `http://127.0.0.1:3501`. Same reasoning. Two Docker-flavored comments inside this file remain; they are minor and can be cleaned up as a separate tidy if desired.
- `specs/001-react-flask-migration/*` — historical record; intentionally preserved.
- `.cursor/commands/speckit.implement.md` — Dockerfile-detection logic is harmless when triggered by the remaining `.devcontainer/Dockerfile`.

### 4.8 `.gitignore` addition

Add at the repo root, alongside the existing `docs/ideas/`, `docs/backlog/`, `docs/active/` block:

```
docs/features/*/Research/
```

This mirrors the gitignored-`discovery/` proposal in `docs/backlog/reorg-documentation/_overview.md`. The existing `docs/ideas/`/`docs/backlog/`/`docs/active/` rules are unchanged.

## 5. Acceptance criteria

### 5.1 Repo structure
- `docs/ideas/Consider stripping down Dockerization/` no longer exists.
- `docs/features/strip-down-dockerization/_overview.md` exists and points to `Development/spec.md`.
- `docs/features/strip-down-dockerization/Development/spec.md` exists (this file) along with `plan.md` after the writing-plans phase.
- Root `.gitignore` contains `docs/features/*/Research/`.
- `git ls-files docs/features/strip-down-dockerization/Research` returns nothing.

### 5.2 Stripped artifacts
- `git ls-files docker-compose.yml backend/Dockerfile frontend/Dockerfile` returns nothing.
- `Makefile` has no references to `docker compose`, `USE_DIRECT`, `IN_DEVCONTAINER`, `COMPOSE_SERVICE`, `build`, `up`, or `down` targets.
- `make test` and `make lint` succeed on a fresh host with only `uv` + Node (per `.nvmrc`) installed.
- `make test` and `make lint` succeed inside the devcontainer.
- `rg -i "docker compose|docker-compose" README.md frontend/README.md` returns nothing.

### 5.3 CI behavior
- `.github/workflows/main_ci.yml` uses `devcontainers/ci@v0.3` with `permissions: contents: read; packages: write`, GHCR login, and `cacheFrom`/`imageName` set as described in §4.4.
- Two separate `runCmd` steps for `make test` and `make lint`.
- The 3× Docker-Hub-flake retry loop is gone.
- The first run on `main` after merge publishes a layer-cache image to GHCR, visible under the repo's "Packages" tab.
- A subsequent PR run hits the cache: build step duration drops from minutes to seconds (recorded in the PR description).

### 5.4 Validation receipts (recorded in the implementing PR description)
- Cold-cache PR run duration.
- First `main` run after merge (cache publish) duration.
- Warm-cache follow-up PR duration.
- Confirmation that `Reopen in Container` in VS Code still works against the unchanged devcontainer config.

## 6. Risks & mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | First CI run on `main` is slow (cold GHCR cache). | Certain | Low (one-time) | Accepted; record duration. |
| R2 | `devcontainers/ci@v0.3` regression breaks our Dockerfile. | Low | Medium | Documented fallback to native-runner CI (§3). |
| R3 | Docker Hub rate-limits base image pulls during cold builds. | Medium | Medium | Cache hits avoid this on warm runs. If recurring, escalate by pinning bases by digest or mirroring to GHCR. |
| R4 | GHCR `packages: write` blocked by org policy. | Low | Medium | First push surfaces the issue; downgrade to `push: never` until permissions are sorted. |
| R5 | Stale local `docker compose` containers on a contributor's machine. | Very low | Low | README cleanup note (§4.5). |
| R6 | Hidden Compose-specific assumption surfaces post-merge. | Low | Low | Pre-write audit complete (§4.7); listed exemptions are explicit. |

## 7. Rollback

Single-PR scope. Rollback = revert the merge commit. Deleted Compose files come back from git; the new CI workflow goes back to the prior shape. The published GHCR image is harmless if left in place.

## 8. Sequencing within the PR

Reviewer-friendly commit order, all in one PR:

1. `docs: move strip-down-dockerization into docs/features` — introduces `_overview.md` and `Development/spec.md` net-new (the original `docs/ideas/...` location was gitignored), plus the `.gitignore` rule that excludes `Research/` from tracking.
2. `build: collapse Makefile to single host-direct branch` — Makefile rewrite. Verify the *current* CI still passes since Compose files still exist at this point.
3. `ci: run main_ci on the devcontainer image with GHCR layer caching` — workflow rewrite. The meaningful CI change.
4. `build: remove docker-compose stack and service Dockerfiles` — delete `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`. Safe only after step 3.
5. `docs: rewrite README for devcontainer-first onboarding` — README + `frontend/README.md` edits.

## 9. Out-of-PR follow-ups (noted, not done)

- Decide whether the reorg-documentation backlog should rename its proposed `discovery/` → `Research/` (or vice versa) for project consistency. Track in that backlog item.
- Reassess `docs/backlog/Get gh working in container/` once the devcontainer is the only container path.
- Optional: cleanup of two Docker-flavored comments in `frontend/vite.config.ts`.

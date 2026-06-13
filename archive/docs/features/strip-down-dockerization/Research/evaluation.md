# Consider stripping down Dockerization

Status: Idea — evaluation in progress
Source type: Developer-experience cleanup

## **Description**

How much Docker do we really need with no users or deployed service? Development could go faster without maintaining a lightly used Docker Compose setup that often trips CI. Devcontainer may still be useful, but should be evaluated. It also slows down agentic development since agents are kept in the devcontainer and can't access or run Docker compose outside the devcontainer to help debug.

## Current Docker footprint

What "Dockerization" actually means in this repo today:

- `docker-compose.yml` at the root, wiring two services (`backend`, `frontend`) for a "no-setup" `docker compose up --build` flow advertised as the primary path in the README.
- `backend/Dockerfile` — Python 3.10 + `uv`, mounts app/tests/run.py read-only, runs `python run.py`.
- `frontend/Dockerfile` — Node 24 Vite dev server with a fetch-based healthcheck.
- `.devcontainer/` — a separate `Dockerfile` (Python 3.10 + `uv` + nvm + Node 24), `devcontainer.json`, `post-create.sh` (installs deps, pre-commit, copies sample config). This is the "recommended" dev path in the README.
- `Makefile` — every target (`build`, `up`, `down`, `test`, `ruff-check`, `ruff-format-check`, `pyright`, `coverage`) is **double-implemented**: a `USE_DIRECT` branch (host/devcontainer) and a `docker compose run` branch (host with Compose, no devcontainer).
- `.github/workflows/main_ci.yml` — runs `make test` (which builds the Compose images and runs pytest + Vitest inside them) and `make lint`. The job is wrapped in a 3× retry loop explicitly labeled "with retry on Docker Hub errors" — concrete evidence of the CI flakiness called out in the idea.
- `.dockerignore`.

There is no production image, no registry push, no deploy target. The Compose stack exists purely for local "try it out" and for CI.

## Goals

- Reduce maintenance surface and CI flake rate.
- Keep onboarding simple for someone who just wants to try the app.
- Stop blocking agents/IDEs that operate from outside a container.
- Avoid maintaining the same command twice (host vs. Compose) in the Makefile.

## Options

### Option A — Full strip: remove Compose, both service Dockerfiles, and the devcontainer

Keep only the host-direct toolchain (`uv` + `nvm`/`.nvmrc` + `make`). README's "Without DevContainer" path becomes the only path.

Pros:

- Smallest maintenance surface; deletes ~6 files plus all Makefile branching.
- CI loses the Docker Hub dependency and the retry loop; faster, more reliable runs.
- Agents and editors run commands the same way humans do — no inside/outside split.
- One source of truth for tool versions: `pyproject.toml` / `uv.lock` / `.nvmrc` / `package-lock.json`.

Cons:

- Onboarding for a casual "just run it" user now requires installing `uv`, a compatible Node, and copying a config — currently a single `docker compose up --build`.
- Loses the pinned-OS reproducibility the devcontainer provides (rare but real "works on my machine" fixes).
- The Cursor-bundled-Node footgun (see the README note about `node v20.18.2`) becomes more visible without a container to insulate from it.

### Option B — Keep the devcontainer, drop Compose and the service Dockerfiles

Devcontainer stays as an opt-in reproducible env (it already builds Python + Node + `uv` itself and doesn't depend on Compose). Remove `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`, the Compose retry in CI, and all `USE_DIRECT=false` branches in the Makefile.

Pros:

- Preserves the "single click in VS Code" onboarding for contributors who want it.
- Removes the Compose-specific failure modes (Docker Hub rate limits, port collisions, Vite-in-container quirks documented in the README).
- Makefile collapses to one branch per target.
- CI runs natively on the runner, no Docker Hub pulls.

Cons:

- Still maintains a devcontainer image and `post-create.sh` that few people may use.
- Doesn't fully solve the "agents stuck inside the container" complaint — that's a devcontainer property, not a Compose one. Mitigated only by making host workflows first-class.
- README's "Run with Docker" no-setup path goes away; needs replacement copy.

### Option C — Keep Compose, drop the devcontainer

Keep the user-facing `docker compose up` story; remove the dev container layer.

Pros:

- Preserves the marketed "one-command try-it-out" experience.
- Removes the inside/outside split that blocks agents.

Cons:

- Keeps the exact thing the idea calls out as "trips CI." CI flake stays.
- Keeps the dual-implemented Makefile.
- Loses the most reliably *useful* container (the dev one) while keeping the least-used one.
- Generally inverts the cost/benefit.

### Option D — Status quo with targeted hardening

Pin Compose base images by digest, add a Docker Hub mirror or GHCR-cached base images in CI, simplify the Makefile to a single branch by always running locally and treating Compose as a separate optional target.

Pros:

- Lowest disruption.
- Keeps every onboarding path that exists today.

Cons:

- Doesn't address the core "do we need this at all" question.
- Maintenance surface stays high; future changes (e.g., the planned FastAPI migration in `docs/ideas/Switch to FastAPI...`) have to update three Dockerfiles and the Compose wiring.

## Trade-off summary

| Concern                            | A: Strip all | B: Keep devcontainer | C: Keep Compose | D: Status quo       |
| ---------------------------------- | ------------ | -------------------- | --------------- | ------------------- |
| Maintenance surface                | Lowest       | Low                  | Medium          | Highest             |
| CI Docker Hub flake                | Gone         | Gone                 | Stays           | Mitigated           |
| "One-command try-it-out" UX        | Lost         | Lost                 | Kept            | Kept                |
| Reproducible dev env               | Host-only    | Container available  | Host-only       | Container available |
| Agent / external-tool friendliness | Best         | Better               | Better          | Same as today       |
| Makefile complexity                | 1 branch     | 1 branch             | 2 branches      | 2 branches          |
| Effort to land                     | Medium       | Small                | Small           | Smallest            |

## Recommendation (tentative)

**Option B** looks like the best fit for current reality:

- The Compose stack is the part that "trips CI" (retry loop is the receipt) and is the least-justified now that there are no users or deployment.
- The devcontainer is the part contributors and agents actually still benefit from, and it's independent of Compose.
- It collapses the Makefile, removes the CI Docker Hub dependency, and unblocks tools that run outside containers, while keeping a path for contributors who like reproducible envs.

Option A is the natural follow-up if, after living with B, the devcontainer also turns out to be unused or redundant with `uv` + `.nvmrc`.

## Risks and open questions

- **Onboarding regression.** The README leads with `docker compose up --build`. Removing it needs a replacement quickstart that's honest about installing `uv` and Node. Worth measuring how often that path is actually used (issues, README hits) before deleting.
- **CI parity.** Today CI runs tests inside the same image used to "run the app," giving a small amount of integration coverage. Moving to host-native CI is closer to how unit tests are intended to run anyway, but should be confirmed against the React + Flask integration tests (`specs/001-react-flask-migration/`).
- **Frontend dev server in container.** The README documents non-trivial port-collision workarounds (5174↔5173, `FRONTEND_REDIRECT_URL`, Cursor's bundled Node). Most of that complexity disappears with B/A.
- **Future FastAPI migration.** If `docs/ideas/Switch to FastAPI and React frontend plan` lands, any Docker assets we keep have to be updated then. Lower-cost to delete now and re-add deliberately if/when a deploy target appears.
- **Interaction with `docs/backlog/Get gh working in container`.** That backlog item assumes the container stays. Worth deciding which way this idea points before investing there.

## Suggested next step

Promote to `docs/backlog/strip-down-dockerization/` with a small spec proposing Option B, including:

1. Files to delete (`docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`, Compose branches in `Makefile`, the CI retry loop).
2. README rewrite for a single host-based quickstart plus an optional devcontainer section.
3. CI simplification: install `uv` + Node directly on the runner, drop the retry.
4. A pre-deletion check that no current contributor workflow depends on the Compose stack.
# LifeFinances — Agent Guide

LifeFinances is a personal finances and retirement simulator. The repo is a monorepo with a Python/Flask backend and a React + TypeScript frontend.

This file tells coding agents how to work in this repo. Stack-specific rules live in nested files:

- Editing under `backend/` → also read [backend/AGENTS.md](backend/AGENTS.md)
- Editing under `frontend/` → also read [frontend/AGENTS.md](frontend/AGENTS.md)

The closest `AGENTS.md` to the file you are editing wins for any conflicting rule.

## Tech stack at a glance

| Layer    | Tech                                                            |
| -------- | --------------------------------------------------------------- |
| Backend  | Python 3.10+, Flask 3.1, Pydantic 2.4, NumPy, pandas, PyYAML    |
| Frontend | React 19, TypeScript 5.9 (strict), Vite 7                       |
| Tests    | pytest 9 (backend), Vitest 4 + React Testing Library + MSW 2    |
| Tooling  | uv, ruff, pyright, npm, eslint, pre-commit, Make                |
| Dev env  | VS Code Dev Container (`.devcontainer/`), Python 3.10, Node 20+ |

## Repo map

```
.
├── AGENTS.md                  # this file (root policy)
├── Makefile                   # entry point for tests / lint / coverage / profile
├── README.md                  # human-facing setup
├── config.yml                 # active simulator config (gitignored; do not commit)
├── backend/                   # Python / Flask app — see backend/AGENTS.md
│   ├── AGENTS.md
│   ├── app/
│   │   ├── __init__.py        # Flask app factory; mounts /api blueprint
│   │   ├── routes/            # HTTP routes (api.py, api_json.py)
│   │   ├── models/            # config, controllers, financial, simulator
│   │   ├── data/              # constants, historic_data, variable_statistics.csv
│   │   └── util.py
│   ├── tests/                 # pytest tree; mirrors app/
│   ├── standalone_tools/      # *.ipynb tools NOT imported by app code
│   ├── pyproject.toml         # deps + ruff config
│   ├── pyrightconfig.json
│   └── run.py                 # backend entry point
├── frontend/                  # React + TS SPA — see frontend/AGENTS.md
│   ├── AGENTS.md
│   ├── package.json
│   ├── vite.config.ts
│   ├── vitest.config.ts
│   └── src/
│       ├── App.tsx, main.tsx
│       ├── services/api.ts    # typed API client (single boundary)
│       ├── types/api.ts       # API contract types
│       └── test/              # MSW handlers + test setup
├── specs/                     # LEGACY speckit specs — frozen, do not add new ones
├── docs/                      # canonical documentation home (see "Documentation policy")
└── scripts/                   # repo scripts (e.g. precommit.sh)
```

## Working directory contract

Always run developer and CI commands from the **repo root**. The backend resolves `config.yml` against the process working directory, so running from elsewhere breaks `GET/PUT /api/config` and `POST /api/simulation/run`.

## Cross-stack commands

Run from the repo root.

| Action                             | Command                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------ |
| Run all tests (backend + frontend) | `make test`                                                                                |
| Lint everything                    | `make lint`                                                                                |
| Lint + test (default `make` goal)  | `make`                                                                                     |
| Backend coverage report            | `make coverage`                                                                            |
| Profile the simulator              | `make profile`                                                                             |
| Run pre-commit on all files        | `pre-commit run --all-files`                                                               |
| Start backend (dev)                | `python backend/run.py` (devcontainer) or `uv run --project backend python backend/run.py` |
| Start frontend (dev)               | `cd frontend && npm run dev`                                                               |

`make test` runs both pytest and `npm run test:run`. `make lint` runs ruff check + ruff format check + pyright. The pre-commit hook runs `make` via [scripts/precommit.sh](scripts/precommit.sh), which also validates Node version.

After making substantive changes, you MUST run `make` (or `make test` + `make lint`) and confirm it passes before claiming the task is complete.

## Documentation policy

Documentation conventions focus on `docs/features/`.

### Required feature structure

For any feature that has spec/plan-style implementation artifacts, they MUST live under:

- `docs/features/<feature>/Development/`

Recommended shape for each feature:

- `_overview.md` — short summary of goal, scope, status, next action, and links
- `Development/` — spec/plan artifacts that directly guide implementation
- `Research/` — exploration notes and scratch artifacts

### Optional personal organization

`docs/ideas/` and `docs/backlog/` are optional personal workflow folders. Contributors MAY use them, but they are not required project-wide conventions.

### Hard rules

- DO put new specs/plans under `docs/features/<feature>/Development/`.
- DO keep `_overview.md` in each feature directory as the index for that feature.
- SHOULD keep research and exploration notes under `docs/features/<feature>/Research/`.
- SHOULD NOT commit research scratch notes or generated exploration artifacts unless they are durable project documentation.

## Commit, PR, and workflow conventions

- Keep commits small and reviewable. One logical change per commit.
- Commit messages: imperative mood, concise subject (≤72 chars), body explains *why* not *what*.
- Tests MUST pass locally before commit. The pre-commit hook enforces this; do not skip it with `--no-verify` unless you have a specific reason and call it out.
- New dependencies MUST be added through the package manager (`uv add` for backend, `npm install` for frontend), never by hand-editing lockfiles.
- Never push to `main` directly when a PR is the right vehicle. If unsure, ask.

## Hard guardrails (never do these without explicit confirmation)

- NEVER modify files under `.github/workflows/`.
- NEVER bypass pre-commit silently (`git commit --no-verify`).
- NEVER commit `config.yml` with real personal data; the file is gitignored for a reason.
- NEVER modify `config.yml`; the file contains the user's personal info and is not backed up with **git.**
- NEVER commit secrets, API keys, or `.env` files.
- NEVER edit lockfiles (`uv.lock`, `package-lock.json`) by hand. Use the package manager.
- NEVER add a new top-level `specs/` directory or check new files into the legacy `specs/00X-*/` tree.
- NEVER delete or rewrite `backend/app/data/variable_statistics.csv` or files under `backend/app/data/historic_data/` without confirmation — they encode source-of-truth statistics.
- NEVER introduce plain JavaScript application code in `frontend/`. TypeScript only (tooling configs are exempt).
- NEVER disable a lint or type-check rule to make CI pass; fix the underlying issue.

## When to ask before acting

Stop and ask the user before:

- Adding a heavyweight dependency (anything that materially expands the install footprint or introduces native build steps).
- Changing API contracts under `backend/app/routes/api*.py` in a way that breaks `frontend/src/services/api.ts`.
- Refactoring across both stacks in a single change.
- Large-scale documentation reorganizations across `docs/features/` that could impact active workstreams.
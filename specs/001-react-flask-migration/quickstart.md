# Quickstart: Config UI (React) + Flask API

**Feature**: `001-react-flask-migration`  
**Goal**: Run backend and frontend together and verify load config → save → run simulation.

## Prerequisites

- Repo root contains `config.yml` (or rely on backend fallback to `backend/tests/sample_configs/full_config.yml` when default path is missing — same as today).
- Python env: `uv sync --project backend` (or DevContainer).
- Node: `npm ci` in `frontend/`.

## Ports

| Service   | Port | URL                    |
|-----------|------|------------------------|
| Flask API | 3500 | http://localhost:3500  |
| Vite      | 5173 | http://localhost:5173  |

## Local development (two terminals)

**Terminal 1 – backend** (from repo root, cwd matters for `config.yml`):

```bash
python backend/run.py
```

**Terminal 2 – frontend**:

```bash
cd frontend && npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to `http://127.0.0.1:3500` by default (see `frontend/vite.config.ts`).

## Docker Compose

```bash
docker compose up --build
```

Open **http://localhost:5173**.

**Important**: The frontend container must proxy `/api` to the **backend service hostname**, not `localhost`. Set `API_PROXY_TARGET=http://backend:3500` on the frontend service and read it in `vite.config.ts` (see `research.md`). Until that is implemented, Docker UI may fail to reach the API.

## Connectivity checklist (SC-004 / FR-007)

1. **GET** `/api/config` returns JSON with `content` matching file on disk.
2. **PUT** `/api/config` with valid YAML persists and a subsequent GET reflects changes.
3. **PUT** invalid YAML returns **400** with a clear JSON error.
4. **POST** `/api/simulation/run` (after a successful **PUT** in the same “Save & run” flow) returns `success_percentage` and `first_result` with `columns` / `rows`.
5. From the browser (via proxy): flows succeed without CORS errors; UI has **only** Save and Save & run (no run-only control).

## Performance spot-check

- After opening the app, config visible within **2 seconds** (SC-002) on a typical dev machine.
- With standard sample config, simulation result visible within **10 seconds** (SC-003) or document deviation.

## API contract

OpenAPI description: [contracts/openapi.yaml](./contracts/openapi.yaml)

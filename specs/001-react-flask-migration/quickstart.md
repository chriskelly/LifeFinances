# Quickstart: Config UI (React) + Flask API

**Feature**: `001-react-flask-migration`  
**Goal**: Run backend and frontend together and verify load config → save → run simulation.

## Prerequisites

- Repo root contains `config.yml` (or rely on backend fallback to `backend/tests/sample_configs/full_config.yml` when default path is missing — same as today).
- Python env: `uv sync --project backend` (or DevContainer).
- Node: `npm ci` in `frontend/`.

## Ports

| Service | Port | URL |
|---------|------|-----|
| Flask API (`backend/run.py`) | **3500** | http://localhost:3500 |
| Vite (`npm run dev` in `frontend/`) | **5173** | http://localhost:5173 |

Flask binds **`0.0.0.0:3500`** ([`backend/run.py`](../../backend/run.py)). The Vite dev server proxies browser calls for `/api/*` to **`http://127.0.0.1:3500`** by default ([`frontend/vite.config.ts`](../../frontend/vite.config.ts)); override with **`API_PROXY_TARGET`** only when you deliberately run Flask on another host or port.

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

## Dev Container (same flow)

Use the root [README](../../README.md) to open the repo in the dev container. It forwards **3500** (Flask) and **5173** (Vite). Inside the container, run the same two commands as above from `/workspace`.

### Troubleshooting

- **`ERR_EMPTY_RESPONSE` or blank page on port 5173** — another process may be bound to **`127.0.0.1:5173`** (often another Vite or tooling). Check listeners with `lsof -nP -iTCP:5173 -sTCP:LISTEN` (or your OS equivalent) and stop the conflicting process. This repo sets **`server.host: '0.0.0.0'`** in `frontend/vite.config.ts` so Vite listens on all interfaces inside the container.
- **API calls fail from the browser** — confirm Flask is up: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3500/api/config` should print **`200`** when `config.yml` exists and is readable.
- **Custom proxy target** — set **`API_PROXY_TARGET`** when Vite cannot reach Flask at `127.0.0.1:3500` (unusual for this repo’s supported setups).

> **Historical note:** An optional Docker Compose stack documented **5174 → 5173** and **`API_PROXY_TARGET=http://backend:3500`** was removed in favor of dev-container-only Docker ([PR #175](https://github.com/chriskelly/LifeFinances/pull/175)). If you still have old Compose containers, run **`docker compose down --remove-orphans`** once (see root README).

## Connectivity checklist (SC-004 / FR-007)

1. **GET** `/api/config` returns JSON with `content` matching file on disk.
2. **PUT** `/api/config` with valid YAML persists and a subsequent GET reflects changes.
3. **PUT** invalid YAML returns **400** with a clear JSON error.
4. **POST** `/api/simulation/run` (after a successful **PUT** in the same “Save & run” flow) returns `success_percentage` and `first_result` with `columns` / `data`.
5. From the browser (via proxy): flows succeed without CORS errors; UI has **only** Save and Save & run (no run-only control).

## Performance spot-check

- After opening the app, config visible within **2 seconds** (SC-002) on a typical dev machine.
- With standard sample config, simulation result visible within **10 seconds** (SC-003) or document deviation.

## API contract

OpenAPI description: [contracts/openapi.yaml](./contracts/openapi.yaml)

## Scripted API checks

From the **repository root** (so `config.yml` resolves like the running app):

```bash
PYTHONPATH=backend uv run --project backend pytest backend/tests/test_api_config.py backend/tests/test_api_simulation.py
```

## Validation log

| Environment | Checklist (connectivity) | Date | Outcome |
|-------------|--------------------------|------|---------|
| Local dev container | quickstart “Connectivity checklist” via browser at `http://localhost:5173` | 2026-04-06 | Pass (automated: `make test`, `npm run test:run`, API checks) |

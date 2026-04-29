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
| Flask API | 3501 | http://localhost:3501  |
| Vite (local `npm run dev`) | 5173 | http://localhost:5173  |
| Vite (Docker Compose host → container) | 5174 → 5173 | http://localhost:5174  |

## Local development (two terminals)

**Terminal 1 – backend** (from repo root, cwd matters for `config.yml`):

```bash
python backend/run.py
```

**Terminal 2 – frontend**:

```bash
cd frontend && npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to `http://127.0.0.1:3501` by default (see `frontend/vite.config.ts`).

## Docker Compose

```bash
docker compose up --build
```

Open **http://localhost:5174** (or `http://127.0.0.1:5174` if your browser prefers IPv4). The container still listens on **5173** internally; **5174** is only the host mapping to avoid another process (often **Cursor** or local Vite) already bound to **`127.0.0.1:5173`**, which otherwise produces **empty reply** from the wrong listener.

The Compose file sets **`API_PROXY_TARGET=http://backend:3500`** so the Vite dev server proxies `/api` to the backend container by name (not `localhost` inside the frontend container).

### Expected response from the frontend URL

You should get **HTTP 200** with an HTML document whose body mounts the React app (view source will show a root `div` and a script tag for the Vite client). If the tab shows **ERR_EMPTY_RESPONSE** after switching to **5174**, check **`lsof -nP -iTCP:5174 -sTCP:LISTEN`** for a conflicting process. If in-container checks work but a **5173** URL fails, something on the host may still be bound to **`127.0.0.1:5173`**. This repo sets **`server.host: '0.0.0.0'`** in `frontend/vite.config.ts` and **`--host 0.0.0.0`** in the frontend `Dockerfile` so Vite accepts connections from Docker’s port publish.

### Docker debug steps

1. **Containers running**: `docker compose ps` (frontend should be `running`, not `exited`). Check **health**: if Compose reports `healthy`, the dev server is answering **inside** the container.
2. **Frontend logs**: `docker compose logs -f frontend` — look for Vite “ready” and `Network: http://172.x.x.x:5173/`.
3. **In-container HTTP (isolates Vite vs port publishing)**:
   ```bash
   docker compose exec frontend node -e "fetch('http://127.0.0.1:5173/').then(r=>r.text()).then(t=>console.log(t.slice(0,80)))"
   ```
   You should see HTML starting with `<!doctype` (or similar).  
   - **Works here but `curl` from the Mac/host still says “Empty reply”** → the app is fine inside Docker; the break is often **another listener on the host URL** (see `lsof -nP -iTCP:5174 -sTCP:LISTEN` for the Compose-mapped port) or **Docker Desktop’s userland proxy**. Try: restart Docker Desktop, `curl -v http://127.0.0.1:5174/`, and upgrade Docker Desktop.
   - **Fails inside the container** → inspect logs for Vite/Node errors; rebuild with `docker compose build --no-cache frontend`.
4. **From the host**: `curl -v --max-time 5 http://127.0.0.1:5174/` — expect `HTTP/1.1 200` and HTML.
5. **Rebuild after image/config changes**: `docker compose build --no-cache frontend && docker compose up frontend` (or `up --build`).
6. **Backend health** (optional): `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3501/api/config` — expect `200` when `config.yml` is mounted and readable.

**Image note**: The frontend image uses **Node 22 on `bookworm-slim` (glibc)** instead of Alpine, which avoids several rare **musl + Docker Desktop** combinations that show up as successful TCP connect followed by an empty HTTP response from the host.

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
| Full Docker Compose stack (host) | `docker compose up --build`, browser at `http://localhost:5174`, checklist “Connectivity checklist” | 2026-04-06 | Pass (host connectivity verified after debug; see this quickstart’s **Docker Compose** / **Docker debug steps** if issues recur) |

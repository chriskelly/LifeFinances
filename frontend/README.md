# LifeFinances frontend

React + TypeScript + Vite workspace for the LifeFinances UI. It lives beside `backend/` in the monorepo; run backend and frontend separately during development (see the root [README](../README.md)).

## Prerequisites

- Node.js (the Dev Container and `frontend/Dockerfile` use a current Node LTS; match that or use `nvm`/`fnm` locally)
- A running backend on port **3500** when you need API calls (see below)

## Install

From the repository root:

```bash
npm ci --prefix frontend
```

Or from `frontend/`:

```bash
npm ci
```

## Development server

1. Start the API (from repo root), for example:
   - With uv: `uv run --project backend python backend/run.py`
   - In the Dev Container: `python backend/run.py`
2. Start Vite:

```bash
cd frontend && npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

### Backend API and the Vite proxy

Flask registers the HTTP API under the `/api` prefix (`backend/app/__init__.py`). The dev server proxies browser requests for `/api/*` to the backend using `vite.config.ts`:

- **Default target:** `http://localhost:3500`
- **Override:** set `VITE_API_PROXY_TARGET` before starting Vite (for example `http://backend:3500` when Vite runs in Docker Compose next to a service named `backend`). The repo’s `docker-compose.yml` sets this for the `frontend` service.
- **Who resolves it:** the Node process running Vite, not the browser. The backend must be reachable at that host and port **from wherever Vite runs** (your machine, the Dev Container with port 3500 forwarded, or the frontend container on the Compose network).

Call the backend from the browser via relative URLs, e.g. `fetch('/api/...')`, so traffic stays on the Vite origin and goes through the proxy.

### Docker Compose

`docker compose` builds a separate image for `frontend` and runs `npm run dev` inside that service. The default `localhost:3500` proxy target would point at the frontend container itself, not the `backend` service; the Compose file sets `VITE_API_PROXY_TARGET=http://backend:3500` so `/api` from the browser is proxied correctly. If you customize service names or ports, update that variable (or your override file) to match.

## Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | Typecheck (`tsc -b`) and production build |
| `npm run preview` | Local preview of the production build |
| `npm run lint` | ESLint |

## Quality bar

New UI work should follow the project constitution (see `.specify/memory/constitution.md`), including test-driven development and accessibility-minded tests when a suite is added.

## Boilerplate reference

This project was bootstrapped with Vite’s React + TypeScript template. Upstream template notes (React Compiler, ESLint type-aware presets, etc.) are still valid if you extend tooling; see [Vite](https://vite.dev/) and [React](https://react.dev/) docs for generic Vite/React topics.

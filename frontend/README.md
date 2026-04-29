# LifeFinances frontend

React + TypeScript + Vite workspace for the LifeFinances UI. It lives beside `backend/` in the monorepo; run backend and frontend separately during development (see the root [README](../README.md)).

## Prerequisites

- Node.js `^20.19.0 || ^22.12.0 || >=24.0.0` (also enforced via `engines` in `package.json`). This range is required because `jsdom@29` → `html-encoding-sniffer@6` → `@exodus/bytes` is ESM-only and the test runner does `require()` of those modules, which Node only supports unflagged from those versions onward. The repo pins a default in the root `.nvmrc`; with nvm, run `nvm install && nvm use` from the repo root.
- A running backend on host port **3501** when you need API calls (see below)

> If your shell resolves `node` to Cursor Server's bundled `v20.18.2`, you'll see `ERR_REQUIRE_ESM` from `html-encoding-sniffer` when running tests. Use nvm (or any other version manager) to put a compatible Node first on `$PATH`. The repo's pre-commit wrapper performs this check automatically.

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

- **Target:** `http://localhost:3501` (default fallback in `vite.config.ts`; override with `API_PROXY_TARGET` as needed)
- **Who resolves it:** the Node process running Vite, not the browser. The backend must be reachable at that host and port **from wherever Vite runs** (typically your laptop or the Dev Container with port 3501 forwarded).

Call the backend from the browser via relative URLs, e.g. `fetch('/api/...')`, so traffic stays on the Vite origin and goes through the proxy.

### Docker Compose

The repo’s `docker-compose.yml` sets **`API_PROXY_TARGET=http://backend:3500`** on the `frontend` service so Vite proxies `/api` to the backend by Docker service name (backend listens on **3500** inside its container; the host maps **3501→3500** for direct API access from the host).

If you run a custom Compose layout without that variable, `localhost` inside the frontend container is **not** the backend — set `API_PROXY_TARGET` to a URL reachable from the frontend container (same idea as the feature [quickstart](../../specs/001-react-flask-migration/quickstart.md#docker-compose)).

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

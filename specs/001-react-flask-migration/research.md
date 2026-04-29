# Research: React–Flask split UI migration

**Date**: 2026-04-05  
**Feature**: Split Configuration UI and Simulation Backend  
**Phase**: 0 – Research & technical decisions

## 1. Browser-to-backend connectivity (dev and Docker)

**Question**: How should the React app call Flask without CORS pain in dev and in Docker Compose?

**Decision**: Keep **same-origin API calls** to `/api` from the browser. **Vite dev server** proxies `/api` to the Flask host. Proxy **target must be configurable**: default `http://127.0.0.1:3501` for local laptop dev; in Docker Compose set an environment variable (e.g. `API_PROXY_TARGET=http://backend:3500`) read only in `vite.config.ts` so the frontend container reaches the backend service by name.

**Rationale**:

- Browser only talks to the Vite origin (`:5173`), so no CORS preflight for `/api` during development.
- `frontend/vite.config.ts` currently hardcodes `localhost:3501`, which **fails inside the frontend container** because the backend is a different container.

**Alternatives considered**:

- **flask-cors** for cross-origin browser → `:3501`: Works but duplicates origins and complicates cookie/session story; unnecessary if proxy is correct.
- **Always call absolute `http://localhost:3501` from the client**: Breaks Docker and mixes origins.

**Implementation notes**: Update `docker-compose.yml` `frontend` service with `environment: API_PROXY_TARGET: http://backend:3500` (or equivalent). Document in `quickstart.md`.

---

## 2. API payload shape for the first-result table

**Question**: Should the API return HTML (like `to_html()`) or structured data for React?

**Decision**: Return **structured JSON**: column names plus row arrays (string/number/null), derived from the same pandas DataFrame as today. The React app renders a semantic `<table>`.

**Rationale**:

- Aligns with constitution (typed contracts, no embedding server HTML in JSON for core UI).
- Easier accessibility (roles, headers) and testing than parsing HTML.

**Alternatives considered**:

- **HTML fragment in JSON**: Faster parity with legacy but poor typing, a11y, and test ergonomics.
- **CSV string**: Possible but weaker typing and column consistency for clients.

---

## 3. Simulation endpoint semantics and two-button parity

**Question**: Should “run simulation” accept inline config body or only read from disk? How does that relate to the legacy two-button UI?

**Decision**: **POST `/api/simulation/run`** runs against the **current persisted `config.yml`** only. Inline body / dry-run-from-body is **out of scope**. The **React UI exposes exactly two primary actions**, matching legacy parity: (1) **Save** → **PUT `/api/config`** only; (2) **Save & run** → **PUT `/api/config`** with current editor text, then **POST `/api/simulation/run`** in that order. There is **no** third control that triggers simulation without going through **Save & run** (no “run only”).

**Rationale**: Matches FR-003a and stakeholder direction: same mental model as “Save” vs “Save & Run Simulation”; avoids implying users can refresh results from stale disk while the editor has diverged content. If **PUT** fails (validation), the client must **not** call **POST**.

**Alternatives considered**:

- **Standalone “Run” button** (POST only): Rejected—breaks parity and encourages running without persisting current editor state.
- **Single server endpoint** that saves and runs atomically: Could reduce round-trips; rejected for this iteration in favor of explicit REST steps and a thin backend surface (still valid as a future optimization).

---

## 4. Legacy Flask `/` route

**Question**: How to satisfy “replace legacy UI” without breaking bookmarks?

**Decision**: Remove the server-rendered workflow from the default app factory **or** return **302/303** to the documented frontend URL (`http://localhost:5173/`) in development; production/Docker behavior documented in `quickstart.md`. Root may return **404** with a short JSON message if the app is API-only in some contexts — pick one consistent behavior in implementation and test it.

**Rationale**: Spec says legacy page is not a supported alternative; a redirect preserves discoverability during transition.

**Alternatives considered**:

- **Keep both**: Rejected by spec (FR-005a).

---

## 5. Frontend test stack additions

**Question**: Which packages satisfy constitution TR-003 / TR-011?

**Decision**: Add **Vitest**, **@testing-library/react**, **@testing-library/user-event**, **@testing-library/jest-dom**, **jsdom**, and **MSW** as dev dependencies; add `npm test` script and `vitest.config.ts`.

**Rationale**: Matches constitution and existing spec TR bullets; `frontend/package.json` currently has no test runner.

**Alternatives considered**:

- **Jest instead of Vitest**: Acceptable per constitution; Vitest pairs naturally with Vite and is lighter to configure.

---

## 6. Error response shape

**Question**: How should validation errors from `write_config_file` surface over JSON?

**Decision**: Use consistent JSON errors: `400` for YAML/schema validation failures with a **message** field (and optional **detail** string from Pydantic/YAML). `500` for unexpected server errors with a generic message in production-like mode.

**Rationale**: Aligns with constitution “clear, actionable” and API consistency.

**Alternatives considered**:

- **Plain text body**: Harder for the React client to unify.

---

## 7. Implementation validation (2026-04-06)

### Coverage

- **Backend** (`pytest --cov=app`): overall package **96%** line coverage on full `backend/app/`; new modules `backend/app/routes/api_json.py` at **100%**; `backend/app/routes/api.py` at **75%** (error paths and simulation exception branches under-exercised in tests). Core simulation stack (`app/models/simulator.py` and financial controllers) remains **≥94–100%** in this report, satisfying TR-002 for simulation-heavy code paths in aggregate.
- **Frontend** (`npx vitest run --coverage`): **~98%** line coverage on measured application files (`App.tsx`, `src/services/api.ts`). Pure type modules under `src/types/` are excluded from coverage (no executable lines).

### Latency and profiling

- Interactive `GET/PUT /api/config` through the Flask test client completes in **well under 2s** on the devcontainer (SC-002).
- **POST `/api/simulation/run`** duration is dominated by Monte Carlo work; wall time scales with `trial_quantity` and hardware. It is **not** bounded by a trivial per-trial HTTP budget—PR-002 remains an engine-level target, not a full HTTP SLA for large trial counts.
- A one-off **cProfile** of the HTTP path with **`trial_quantity: 3`** showed top cumulative time in **Werkzeug/Flask dispatch** (`werkzeug/test.py:post`, `flask/app.py:full_dispatch_request`, `app/routes/api.py:run_simulation_route`) because the run finishes in ~50ms. For engine-heavy profiling use `backend/tests/profiling/gen_trials.py` via `make profile`.

### Resource note

- Peak RSS for a representative simulation was not captured in this automated pass; use `/usr/bin/time -v` or container stats around `POST /api/simulation/run` with your production-like `config.yml` when you need an absolute figure.

---
description: "Task list for Split Configuration UI and Simulation Backend (001-react-flask-migration)"
---

# Tasks: Split Configuration UI and Simulation Backend

**Input**: Design documents from `/workspace/specs/001-react-flask-migration/`  
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [research.md](./research.md), [quickstart.md](./quickstart.md)

**Tests**: Required per constitution (TDD: write failing tests before implementation for each story where applicable).

**Organization**: Phases follow user story priority (P1 → P2 → P3), then polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no ordering dependency on incomplete sibling tasks)
- **[Story]**: `[US1]` / `[US2]` / `[US3]` for user-story phases only

---

## Phase 1: Setup (shared infrastructure)

**Purpose**: Tooling and wiring so backend and frontend can be developed and tested per plan.

- [ ] T001 Add Vitest, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, and `msw` devDependencies plus `test` / `test:run` scripts in `frontend/package.json` and refresh `frontend/package-lock.json`
- [ ] T002 Create `frontend/vitest.config.ts` with React plugin, jsdom environment, and setup file path
- [ ] T003 Create `frontend/src/test/setup.ts` for `@testing-library/jest-dom` and optional global MSW lifecycle hooks
- [ ] T004 [P] Read proxy target from `process.env.API_PROXY_TARGET` with fallback `http://127.0.0.1:3500` for `/api` in `frontend/vite.config.ts` per `specs/001-react-flask-migration/research.md`
- [ ] T005 [P] Add `API_PROXY_TARGET=http://backend:3500` (or equivalent) to the `frontend` service in `/workspace/docker-compose.yml` so browser calls via Vite reach Flask in Compose
- [ ] T006 [P] Add TypeScript types for `ConfigDocument`, `ConfigSaveResponse`, `FirstResultTable`, `SimulationResult`, and `ErrorBody` aligned with `specs/001-react-flask-migration/contracts/openapi.yaml` in `frontend/src/types/api.ts`

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: Shared API error shape, app entry behavior, and typed client skeleton before user stories.

**⚠️ No user story implementation until this phase is complete.**

- [ ] T007 Add module `backend/app/routes/api_json.py` with typed helpers to build JSON success/error responses consistent with `specs/001-react-flask-migration/contracts/openapi.yaml`
- [ ] T008 Refactor or extend `backend/app/routes/api.py` to register route handlers (stubs acceptable until US1/US2) and keep blueprint import path stable for `backend/app/__init__.py`
- [ ] T009 Change `backend/app/__init__.py` to remove the legacy server-rendered `/` workflow: return HTTP `302` to `http://localhost:5173/` (documented frontend URL) so bookmarks remain discoverable; update `backend/tests/test_routes.py` expectation to accept `302` from `/` per FR-005a
- [ ] T010 Create `frontend/src/services/api.ts` with typed `getConfig`, `putConfig`, and `postSimulationRun` functions using `fetch('/api/...')` and the types from `frontend/src/types/api.ts` (implementations may throw until US1/US2 fill behavior)

**Checkpoint**: Blueprint wired, legacy index route handled, frontend can import services and types.

---

## Phase 3: User Story 1 – View and edit configuration (Priority: P1) 🎯 MVP

**Goal**: User opens the app, sees YAML text from disk, edits, and **Save** persists via **PUT `/api/config`** without running simulation.

**Independent Test**: Load UI → text matches `read_config_file`; edit → Save → reload GET shows new content; invalid YAML shows clear error.

### Tests for User Story 1 (TDD – write first, ensure red before green)

- [ ] T011 [P] [US1] Add failing pytest tests for `GET /api/config` (200, JSON shape) in `backend/tests/test_api_config.py`
- [ ] T012 [US1] Add failing pytest tests for `PUT /api/config` (200 on valid sample YAML, 400 on invalid) using temp config path or pytest fixtures in `backend/tests/test_api_config.py`
- [ ] T013 [P] [US1] Add failing RTL + user-event tests for load/save flow with MSW handlers in `frontend/src/App.test.tsx` (loading, success, **empty** when config returns blank, and error states for config fetch/save)

### Implementation for User Story 1

- [ ] T014 [US1] Implement `GET /api/config` and `PUT /api/config` in `backend/app/routes/api.py` delegating to `read_config_file` and `write_config_file` from `backend/app/models/config/utils.py` with JSON envelope from `backend/app/routes/api_json.py`
- [ ] T015 [US1] Complete `getConfig` and `putConfig` in `frontend/src/services/api.ts` to match OpenAPI contracts
- [ ] T016 [US1] Implement left-panel editor (**Save** only, no simulation), accessible labels, and explicit loading/success/error UI states in `frontend/src/App.tsx` using `frontend/src/services/api.ts`
- [ ] T017 [US1] Run Ruff check and format on touched backend files (`backend/app/routes/api.py`, `backend/app/routes/api_json.py`, `backend/app/__init__.py`)
- [ ] T018 [US1] Run Pyright on `backend/app/` for changed modules
- [ ] T019 [US1] Run `npm run test:run` and `npm run lint` in `frontend/` and fix issues for US1 files
- [ ] T020 [US1] Confirm new backend tests pass via `pytest backend/tests/test_api_config.py` from repo root with appropriate `cwd` for `config.yml` behavior documented in `specs/001-react-flask-migration/quickstart.md`

**Checkpoint**: MVP – config load/save works through React + API; no simulation yet.

---

## Phase 4: User Story 2 – Save & run and review results (Priority: P2)

**Goal**: **Save & run** performs **PUT `/api/config`** then **POST `/api/simulation/run`**; show success percentage and scrollable first-result table; **FR-003b** – only two primary actions, no standalone run control.

**Independent Test**: Valid YAML → Save & run → PUT then POST order; results render; invalid save blocks POST; exactly two primary buttons.

### Tests for User Story 2 (TDD – write first)

- [ ] T021 [P] [US2] Add failing pytest tests for `POST /api/simulation/run` (200 shape with `success_percentage` and `first_result.columns`/`rows`) in `backend/tests/test_api_simulation.py` (mark slow if full simulation exceeds default integration budget per constitution)
- [ ] T022 [P] [US2] Add failing pytest test that simulation uses on-disk config after PUT in `backend/tests/test_api_simulation.py`
- [ ] T023 [P] [US2] Extend MSW + RTL tests in `frontend/src/App.test.tsx` for **Save & run**: assert `PUT` then `POST` order; busy state during run; results panel shows **empty/placeholder** state before first run; error if PUT fails (no POST); assert no third run-only control (roles/names)

### Implementation for User Story 2

- [ ] T024 [US2] Add helper to convert first simulation DataFrame to `FirstResultTable` JSON in `backend/app/routes/api.py` (inline helper; extract to `backend/app/routes/simulation_payload.py` only if it exceeds ~30 lines) using `gen_simulation_results` from `backend/app/models/simulator.py`
- [ ] T025 [US2] Implement `POST /api/simulation/run` in `backend/app/routes/api.py` calling `gen_simulation_results()` and returning JSON per `specs/001-react-flask-migration/data-model.md`
- [ ] T026 [US2] Add `postSimulationRun` and `saveAndRun` (PUT then POST, abort on PUT error) in `frontend/src/services/api.ts`
- [ ] T027 [US2] Add right-panel results (success percentage heading, scrollable `<table>` with semantic headers) and **Save & run** button in `frontend/src/App.tsx`; match two-panel layout comparable to `backend/app/templates/index.html`
- [ ] T028 [US2] Run Ruff and Pyright on changed backend files
- [ ] T029 [US2] Run `npm run test:run` and `npm run lint` in `frontend/` for US2 changes

**Checkpoint**: Full parity workflow for save, save & run, and results display.

---

## Phase 5: User Story 3 – Connectivity and responsiveness (Priority: P3)

**Goal**: Repeatable verification per `specs/001-react-flask-migration/quickstart.md` and FR-007/SC-004.

**Independent Test**: Follow quickstart checklist (local and Docker); timing notes for SC-002/SC-003.

- [ ] T030 [P] [US3] Add a small scripted smoke check (e.g. `curl` sequence or `pytest` marker) documented to run from repo root in `specs/001-react-flask-migration/quickstart.md` or `backend/tests/test_api_smoke.py` hitting `GET/PUT` and optionally `POST` with `@pytest.mark.slow` for full simulation
- [ ] T031 [US3] Update `/workspace/README.md` “Run with Docker” / developer sections so the **primary** workflow is React at `http://localhost:5173` with two-button behavior and pointer to `specs/001-react-flask-migration/quickstart.md`
- [ ] T032 [US3] Document multi-tab **last-write-wins** on save in `/workspace/README.md` or `specs/001-react-flask-migration/quickstart.md` per spec edge cases

**Checkpoint**: Onboarding and verification paths are explicit.

---

## Phase 6: Polish & cross-cutting concerns

**Purpose**: Remove dead code, consolidate docs, quality gates.

- [ ] T033 [P] Remove legacy server-rendered artifacts `backend/app/templates/index.html` and `backend/app/routes/index.py` (and references) after US2/US3 verification; keep only the `302` redirect behavior in `backend/app/__init__.py`
- [ ] T034 [P] Run full `make test` or documented equivalent from `/workspace/Makefile` across backend and frontend
- [ ] T035 [P] Run Ruff and Pyright on `backend/` for all changed modules
- [ ] T036 [P] Confirm `npm run build` succeeds in `frontend/`
- [ ] T037 [P] Manually execute `specs/001-react-flask-migration/quickstart.md` connectivity checklist for **local dev** (run in-container); **Docker steps must be run by the user outside the dev container** — request handoff and record pass/fail in PR description or `specs/001-react-flask-migration/quickstart.md` “Validation log” subsection
- [ ] T038 [P] Spot-check interactive `GET/PUT` latency vs constitution (<2s) and record peak RSS memory during a simulation call; document any `POST` simulation duration vs SC-003 and PR-002 (<100ms/trial) in `specs/001-react-flask-migration/research.md` or plan notes if exceptions apply
- [ ] T039 [P] Verify pytest-cov reports ≥80% line coverage for all new `backend/app/` modules and run `npx vitest run --coverage` to confirm ≥80% for all new `frontend/src/` modules; save frontend report under `frontend/coverage/` and capture backend+frontend coverage summaries in `specs/001-react-flask-migration/research.md`; confirm simulation-related paths reach ≥95%+ per TR-002
- [ ] T040 [P] Profile the actual `POST /api/simulation/run` request path with `cProfile` by adding and running a dedicated profiler harness in `backend/tests/profiling/profile_simulation_run.py` (using Flask test client or direct route callable), write profile output to `/tmp/sim_run.prof`, and record top-10 hotspots in `specs/001-react-flask-migration/research.md` per PR-004 before merge

---

## Dependencies & execution order

### Phase dependencies

| Phase | Depends on |
|-------|------------|
| Phase 1 Setup | None |
| Phase 2 Foundational | Phase 1 |
| Phase 3 US1 | Phase 2 |
| Phase 4 US2 | Phase 3 (uses config UI + PUT; adds simulation) |
| Phase 5 US3 | Phase 4 (full flow to verify) |
| Phase 6 Polish | US1–US3 complete |

### User story dependency graph

```text
P1 (US1) ──► P2 (US2) ──► P3 (US3) ──► Polish
```

US3 documentation can start after US2 but should reference the final quickstart paths.

### Parallel examples

**Phase 1 (after T002):** T004, T005, T006 in parallel (different files).

**US1 tests:** T011 and T013 in parallel (T012 is sequential — shares file with T011).

**US2 tests:** T021, T022, T023 in parallel.

**Polish:** T034–T040 in parallel where CI allows.

---

## Implementation strategy

### MVP first (User Story 1 only)

1. Complete Phase 1 and Phase 2.  
2. Complete Phase 3 (US1).  
3. Stop and validate: load + **Save** + errors, without simulation.

### Incremental delivery

1. US1 → demo config editing.  
2. US2 → demo full Life Finances parity (save & run + table).  
3. US3 + Polish → production readiness and Docker story.

---

## Task summary

| Phase | Task IDs | Count |
|-------|----------|------:|
| Setup | T001–T006 | 6 |
| Foundational | T007–T010 | 4 |
| US1 | T011–T020 | 10 |
| US2 | T021–T029 | 9 |
| US3 | T030–T032 | 3 |
| Polish | T033–T040 | 8 |
| **Total** | **T001–T040** | **40** |

**Format validation**: Every task uses `- [ ]`, sequential `Tnnn`, includes at least one concrete file path, and `[USn]` only on Phase 3–5 story tasks.

*Resolved analysis findings: C1 (PR-002 target in spec.md), E1 (T039 coverage gate), E2 (T040 cProfile), E3 (T013/T023 empty state), E4 (T038 memory), U1 (T009 302 redirect), D1 (T012 parallel marker removed), I1 (T016 wording), I2 (T024 file path), I3 (T037 Docker user-run).*

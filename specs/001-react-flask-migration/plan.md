# Implementation Plan: Split Configuration UI and Simulation Backend

**Branch**: `001-react-flask-migration` | **Date**: 2026-04-05 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification plus plan refinement: maintain parity with the legacy UI—**only two actions**: **Save** (`PUT /api/config` only) and **Save & run** (`PUT /api/config` then `POST /api/simulation/run`). **No** standalone “run simulation” without saving through the same flow as the second button.

## Summary

Replace the Flask server-rendered index workflow with a **React + TypeScript** client that provides the same two-panel experience: raw YAML editor, **exactly two primary buttons** matching legacy behavior—**Save** (persist only) and **Save & run** (persist then run simulation)—plus success percentage and scrollable first-result table. Extend Flask with **JSON REST** under `/api` delegating to `read_config_file`, `write_config_file`, and `gen_simulation_results`. Do **not** expose a UI control that calls `POST /api/simulation/run` without having performed `PUT /api/config` in that same user action (the second button performs both in order). Implement legacy `/` cutover as an HTTP `302` redirect to `http://localhost:5173/` per tasks/spec decisions. Add **Vitest**, **React Testing Library**, **user-event**, and **MSW** to the frontend; add **pytest** integration tests for new API routes. Fix **Docker dev proxy** so the frontend container can reach the backend by hostname (see `research.md`).

## Technical Context

**Language/Version**: Python 3.10+ (backend), TypeScript 5.x + React 19 (frontend)  
**Primary Dependencies**: Flask 3.x, Pydantic, PyYAML, pandas; Vite 7, React 19  
**Storage**: File-based `config.yml` at repo root (same as `app.data.constants.CONFIG_PATH`); no new database  
**Testing**: pytest + pytest-flask (backend); Vitest + React Testing Library + user-event + MSW (frontend, to be added)  
**Target Platform**: Linux (DevContainer / Docker); local browser at `http://localhost:5173`  
**Project Type**: Web monorepo (`backend/` + `frontend/`)  
**Performance Goals**: Spec SC-002/SC-003 and constitution: interactive config endpoints &lt; 2s; full simulation refresh within 10s for standard sample on reference hardware; simulation engine per-trial targets unchanged  
**Constraints**: Single-user, no auth; simulation input = persisted file after each **Save & run** sequence; no simulation result history persistence; raw text config only; **two-button UX parity** (no run-without-save control)  
**Scale/Scope**: One concurrent user typical; multi-tab behavior documented as last-write-wins or equivalent  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Gates:**

- [x] All code will include type hints for public functions and classes
- [x] All frontend application code will use React + TypeScript (no new plain JavaScript app code)
- [x] Backend code will pass Ruff linting checks as configured in `backend/pyproject.toml`
- [x] Code will pass Ruff formatting checks
- [x] Backend code will pass Pyright type checking as configured in `backend/pyrightconfig.json`
- [x] Frontend code will pass configured linting and TypeScript checks
- [x] All modules will include module-level docstrings
- [x] All public classes and functions will include docstrings
- [x] No circular dependencies will be introduced
- [x] Object models (classes, dataclasses, TypedDict, Pydantic) will be used instead of plain dictionaries for type safety
- [x] Function calls will use named arguments (except single obvious argument cases)
- [x] Frontend API requests will be encapsulated in typed services/hooks instead of scattered across components

**Testing Gates:**

- [x] Test-Driven Development (TDD) will be used: tests written before implementation for all application code
- [x] Test coverage plan achieves minimum 80% (95%+ for financial calculations and high-impact financial journeys) for application code
- [x] Tests will use pytest framework with proper, reusable fixtures (including shared domain fixtures and factories where appropriate)
- [x] Frontend work includes component/interaction test coverage for primary user flows using React Testing Library (or equivalent) with accessibility-first queries (role, name, text); `data-testid` only when necessary
- [x] Frontend interaction tests will use `@testing-library/user-event` (or project equivalent), not `fireEvent`, except where justified
- [x] Frontend HTTP/API mocking will sit at the network boundary (e.g. MSW) or test servers, not by replacing `fetch` inside components under test
- [x] Custom hooks will be tested with `renderHook` (or equivalent) and explicit provider wrappers
- [x] Tests will be designed to be data-driven where feasible (avoiding duplicated “magic numbers” by deriving expectations from shared fixtures, canonical data files, or domain objects)
- [x] Integration tests planned for API endpoints
- [x] Frontend plans include loading, success, empty, and error state tests where data fetching is involved
- [x] Test performance targets defined (&lt;1s unit, &lt;10s integration)
- [x] If feature includes standalone scripts/notebooks: Exception documented per constitution Testing Standards (only for scripts/notebooks NOT used as inputs for the application) — N/A for this feature

**User Experience Gates:**

- [x] API endpoints follow consistent naming conventions
- [x] Error messages will be clear and actionable
- [x] Response time targets defined (&lt;2s for interactive endpoints)
- [x] Configuration validation planned (reuse `write_config_file` validation)
- [x] Frontend interactions are accessible by keyboard and use semantic labels
- [x] Shared UI patterns/components are reused instead of reimplemented ad hoc

**Performance Gates:**

- [x] Performance benchmarks defined for simulation operations (align with SC-003 and existing engine expectations)
- [x] Profiling strategy identified for critical paths (existing cProfile guidance; spot-check API + simulation)
- [x] Memory usage constraints considered
- [x] Scalability considerations documented (single-user; file-backed config)

**Post-Phase 1 re-check**: Design uses typed request/response models, JSON contracts in `contracts/openapi.yaml`, centralized frontend API client, two-button parity documented—no constitutional waivers required.

## Project Structure

### Documentation (this feature)

```text
specs/001-react-flask-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2: /speckit.tasks (not created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   ├── api.py               # GET/PUT config, POST simulation/run
│   │   └── api_json.py          # JSON envelope helpers
│   └── templates/               # (empty; legacy index removed)
frontend/
├── src/
│   ├── App.tsx                  # Two buttons: Save; Save & run (PUT then POST)
│   ├── services/
│   │   └── api.ts
├── vite.config.ts               # Proxy target from env for Docker
└── package.json
```

**Structure Decision**: Existing monorepo `backend/` + `frontend/` per constitution. Frontend implements **only** the two legacy-equivalent actions at the UX level; `POST /api/simulation/run` remains a separate endpoint for a clear contract but must not be reachable from a third button.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations requiring justification.

## Phase 2 (follow-up)

Implementation tasks are produced by **`/speckit.tasks`** (`tasks.md`), not by this plan command.

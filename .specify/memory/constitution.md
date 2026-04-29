<!--
Sync Impact Report:
Version: 1.5.0 → 1.6.0
Type: MINOR - Material expansion of Testing Standards › React Frontend
  Test-Driven Development with concrete quality patterns surfaced by review
  of frontend/src/App.test.tsx
Modified principles:
  - Testing Standards › React Frontend Test-Driven Development: Added nine
    patterns covering network-handler purity, no debug leftovers, queryBy
    for negative presence, shared default handlers and URL constants,
    behavioral input coverage, region-scoped status assertions, asserting
    on rendered data (not just structure), determinism for in-flight UI
    state, and one observable behavior per test.
Added sections: None
Removed sections: None
Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md (Testing Gates: added
    bullets for handler purity, queryBy for negation, behavioral input
    coverage, deterministic in-flight state)
  - ✅ updated: .specify/templates/spec-template.md (added TR-013–TR-016)
  - ⚠ unchanged: .specify/templates/tasks-template.md (existing CONSTITUTION
    callouts reference Testing Library practices generically; new bullets
    are additive and do not change task structure)
  - ⚠ unchanged: README.md (frontend testing line still accurate)
Follow-up TODOs: None
-->

# LifeFInances Project Constitution

**Version:** 1.6.0  
**Ratification Date:** 2025-12-10  
**Last Amended:** 2026-04-27

## Purpose

This constitution establishes the non-negotiable principles governing the
LifeFInances project. All code contributions, architectural decisions, and
development practices **MUST** align with these principles. Violations require
explicit justification and constitutional amendment.

## Principles

### Code Quality Standards

**All code MUST maintain high quality standards through static analysis, type
safety, and documentation.**

- **Static Analysis Compliance**: All backend Python code MUST pass Ruff linting
  and formatting checks as configured in `backend/pyproject.toml`. Backend type
  checking MUST pass via Pyright as configured in
  `backend/pyrightconfig.json`. All frontend React code MUST pass the
  frontend's configured linting and TypeScript checks before merge.
- **Type Safety**: All backend public functions, class methods, and
  module-level functions MUST include type hints. All frontend application code
  MUST be written in TypeScript; new plain JavaScript application code MUST NOT
  be introduced except where required by tooling configuration.
- **Documentation Requirements**: Backend Python modules MUST include
  module-level docstrings. Backend public classes and functions MUST include
  docstrings following Google or NumPy style conventions. Frontend components,
  hooks, and utilities MUST have clear names and SHOULD include TSDoc or brief
  comments when behavior is not self-evident. Complex business logic in any
  layer MUST include comments explaining non-obvious decisions.
- **Code Organization**: Code MUST follow the established monorepo structure:
  `backend/` for Python application code and tooling, `frontend/` for the
  React + TypeScript application, and root-level files for orchestration and
  containerization. Related functionality MUST be grouped logically by feature
  or domain. Circular dependencies MUST be avoided.
- **Object Models Over Dictionaries**: Code MUST favor creating object models
  (classes, dataclasses, TypedDict, Pydantic models, or typed interfaces/types)
  rather than plain dictionaries or untyped objects for type safety. Dynamic
  maps SHOULD only be used when typed models would add unnecessary complexity or
  when interfacing with external APIs that require them. Rationale: typed
  models provide stronger tooling support, clearer contracts, and safer refactors.
- **Named Function Arguments**: Backend function calls MUST use named arguments
  unless there is exactly one obvious argument where positional calling is
  unambiguous. Frontend functions and hooks MUST prefer named option objects
  over long positional parameter lists. Rationale: named inputs make code
  self-documenting and prevent argument order mistakes.
- **Error Handling**: All user-facing code paths MUST handle expected error
  conditions gracefully. Exceptions and surfaced UI errors MUST include
  meaningful messages. Critical errors MUST be logged appropriately. Broad
  exception catching (`except Exception`) or catch-all UI error suppression MUST
  be justified with comments when used.

### Frontend Architecture Standards

**The frontend MUST use React with TypeScript and follow predictable,
maintainable UI architecture practices.**

- **Composition Over Monoliths**: UI MUST be built from small, focused,
  composable components. Components that combine data fetching, state
  orchestration, and presentation in a single file SHOULD be refactored when
  they become difficult to test or reason about.
- **State Management Discipline**: State MUST be kept as local as practical.
  Server state, derived UI state, and transient interaction state MUST be kept
  conceptually separate. Global state MUST only be introduced when local state
  or prop composition is no longer sufficient.
- **API Boundary Clarity**: Frontend API requests MUST be centralized in typed
  clients, services, or hooks rather than scattered directly across components.
  Backend response shapes consumed by the frontend MUST have explicit typed
  contracts.
- **Feature-Oriented Organization**: Frontend code SHOULD be grouped by feature
  or domain, with reusable UI primitives separated from feature-specific
  components. Hooks, components, and services MUST live near the feature they
  support unless they are intentionally shared.
- **Accessibility by Default**: UI implementations MUST use semantic HTML,
  keyboard-accessible interactions, explicit form labels, and visible focus
  states. Accessibility regressions in primary workflows are constitutional
  violations, not cosmetic issues.

### Testing Standards

**All functionality related to the application (simulator, Flask app, and React
frontend) MUST be covered by automated tests that validate correctness, edge
cases, and integration points. Testing requirements remain strict for
application code, with exceptions only for standalone scripts/notebooks not
used as application inputs.**

- **Test-Driven Development**: Where tests are required (all application code),
  Test-Driven Development (TDD) MUST be used. Tests MUST be written before
  implementation code. The TDD cycle (Red-Green-Refactor) MUST be followed:
  write failing tests first, implement minimal code to pass, then refactor.
  Rationale: TDD ensures testability, drives better design, and prevents
  untested code from being merged.
- **React Frontend Test-Driven Development**: For React application code, TDD
  MUST express user-observable behavior and contracts, not implementation
  details.
    - **Testing Library first**: Component and integration-style tests MUST use
      React Testing Library (or a successor endorsed by the same accessibility-
      first querying model). Queries MUST prefer roles, accessible names, and
      visible text over CSS selectors or DOM structure. `data-testid` MUST only be
      used when no user-equivalent query is practical, and MUST be justified.
    - **Realistic interaction**: User gestures MUST be simulated with
      `@testing-library/user-event` (or the project's configured equivalent) rather
      than `fireEvent`, except where user-event cannot model the case.
    - **Runner and environment**: The frontend test runner MUST be Vitest or Jest
      (or a project-adopted equivalent documented in the repo). UI tests MUST run
      in a DOM environment (e.g. jsdom) unless a feature explicitly requires
      browser-based E2E tooling.
    - **Network and API boundaries**: HTTP and backend responses MUST be mocked at
      the network boundary (e.g. Mock Service Worker) or via test servers that
      mirror real contracts—not by spying on or replacing internal `fetch`
      implementations inside components under test. Rationale: stable tests and
      alignment with typed API clients.
    - **Hooks and providers**: Custom hooks MUST be tested with `renderHook` (or
      equivalent) and explicit provider wrappers that match production composition.
      Tests MUST NOT depend on React implementation details (e.g. state
      internals, private component methods).
    - **Async and stability**: Asynchronous UI MUST be asserted with `findBy*`,
      `waitFor`, or async user-event APIs. Arbitrary `setTimeout`-based waits in
      tests MUST NOT be used except when testing time-dependent behavior with fake
      timers.
    - **Snapshots**: Snapshot tests MAY be used only for small, stable
      presentational output. They MUST NOT substitute for behavior-focused tests
      on interactive or data-heavy views.
    - **Co-location**: Frontend test files MUST follow a single repo convention
      (e.g. `*.test.tsx` beside sources or colocated `__tests__` directories) and
      MUST remain discoverable next to the modules they protect.
    - **Network handler purity**: Network-mocking handlers (e.g. MSW
      `http.put`/`http.get` callbacks) MUST be pure response-shapers. Assertions
      about request payloads MUST be performed in the test body against
      captured request data, never raised inside the handler. Rationale: an
      `expect` thrown inside a handler surfaces to the component as an opaque
      network error and obscures the real failure.
    - **No debug leftovers**: Test files MUST NOT contain `screen.debug()`,
      `console.log`, `debugger`, `it.only`, `describe.only`, or other
      interactive-debugging artifacts at merge time. Linting or pre-commit
      enforcement is RECOMMENDED.
    - **Negative-presence assertions**: To assert that an element is *not*
      rendered, tests MUST use `queryBy*(...).not.toBeInTheDocument()` (or an
      equivalent specific query) keyed on role + accessible name. Tests MUST
      NOT count all matches of a role (e.g. `getAllByRole('button')` length)
      as a proxy for "no extra control"; such counts break when unrelated
      accessible elements are added.
    - **Shared defaults over duplicated setup**: Repeated network or render
      setup MUST be hoisted to `beforeEach` (or shared helpers/factories);
      individual tests SHOULD only declare what differs from the default.
      Endpoint URLs, sample payloads, and other repeated literals MUST be
      referenced through named constants rather than re-typed per test.
    - **Behavioral input coverage**: Suites for editable views MUST include at
      least one test that simulates a real user input (typing, clearing,
      selection) and asserts that the resulting request body, derived state,
      or rendered output reflects the edit. Tests MUST NOT rely solely on
      echoing server-provided data back to the server, which would pass even
      if every input were ignored.
    - **Region-scoped status assertions**: When a view contains multiple
      `role="status"` regions (or any duplicated landmark/live region),
      assertions on a status message MUST be scoped to the specific region —
      via `within(...)`, container query, id lookup, or a more specific
      accessible-name match — rather than a global text query that could match
      either region.
    - **Verify rendered data, not only structure**: For data-bearing views
      (tables, lists, charts, forms), tests MUST assert on representative data
      values (e.g. cell contents, list items, summary numbers), not only on
      column headers, container roles, or row counts. Structure-only
      assertions silently pass when the data pipeline is broken.
    - **Determinism over wall-clock waits**: In-flight UI states (disabled
      controls, spinners, loading skeletons) MUST be exercised with deferred
      promises that the test resolves explicitly, or with fake timers.
      Arbitrary `setTimeout` delays inside MSW handlers or test bodies — used
      to "wait long enough" for an assertion to land — MUST NOT be used.
    - **One observable behavior per test**: A test name MUST describe a
      single user-observable outcome. Test titles that concatenate multiple
      behaviors (e.g. via `and`, `;`, or `+`) MUST be split. Rationale: a
      failure should immediately identify which behavior regressed.
- **Test Coverage**: All new application code MUST include corresponding tests.
  Coverage MUST maintain a minimum of 80% for new backend and frontend modules.
  Critical business logic (financial calculations, state transitions,
  simulation logic, and high-impact financial user journeys) MUST achieve 95%+
  coverage or equivalent confidence through focused integration tests.
- **Exception for Standalone Scripts/Notebooks**: Scripts and notebooks that are standalone tools and NOT used as inputs for the application (simulator or Flask app) MAY be exempted from testing requirements. This exception applies only to:
    - Standalone analysis scripts that do not feed data or logic into the application
    - Jupyter notebooks used for exploration or one-off calculations that are not imported or executed by the application
    - Utility scripts that are explicitly documented as experimental or exploratory and are not dependencies of the simulator or Flask app
    - Scripts that are not imported, executed, or referenced by any application code (simulator or Flask app)

  **Note**: If a script or notebook is used as input, imported, executed, or referenced by the application, it MUST follow all testing requirements including TDD.

- **Test Structure**: Backend tests MUST use pytest and mirror the source code
  structure under `backend/tests/`. Frontend tests MUST use React-appropriate
  unit/component and interaction testing tools and live in a predictable
  structure under `frontend/`. Test names MUST describe user-visible behavior
  or domain scenarios rather than implementation details.
- **Test Quality**: Tests MUST be independent and executable in any order.
  Backend tests MUST use fixtures from `conftest.py` where shared setup is
  needed. Frontend tests MUST avoid hidden global state and MUST clean up after
  themselves. Tests in all layers MUST validate both success and failure cases.
- **Test Design & Reuse**: Tests for complex behavior (e.g., financial logic, simulations, controller wiring) SHOULD be structured around reusable, scenario‑focused fixtures and helpers rather than ad‑hoc inline setup. Shared domain concepts (e.g., assets, users, controllers, strategies) SHOULD be modeled as typed fixtures or small dataclasses that mirror production models. Tests SHOULD avoid duplicated “magic numbers” and instead derive expectations from shared data sources (e.g., fixtures, canonical CSVs, or domain objects) so that changes in underlying data do not require manual test rewrites.
- **Explicit Wiring in Tests**: When testing components that depend on other services or controllers, tests MUST construct or obtain those collaborators explicitly (for example, via factories/fixtures that take a `User` or configuration object), rather than relying on hidden globals or implicit default state. This ensures each test clearly documents its assumptions and makes it easy to vary scenarios (for example, different users, configurations, or economic conditions) without copy‑pasting setup code.
- **Integration Testing**: API endpoints MUST have integration tests verifying
  HTTP status codes, response formats, and error handling. The simulation engine
  MUST be tested with multiple configuration scenarios. Frontend primary user
  journeys MUST have interaction or end-to-end style coverage for loading,
  success, empty, and error states. Data loading and transformation MUST be
  tested with representative sample data.
- **Test Performance**: Unit tests MUST complete in under 1 second per test.
  Integration tests MUST complete in under 10 seconds per test. Frontend tests that require browser-style execution MUST be categorized
  clearly and MUST NOT silently slow down the default suite. Test suites MUST
  complete in under 5 minutes total.

### User Experience Consistency

**All user-facing interfaces MUST provide consistent, predictable, and intuitive
experiences across the application.**

- **API Consistency**: All REST API endpoints MUST follow consistent naming
  conventions (snake_case for Python, kebab-case for URLs). Response formats
  MUST be consistent (JSON structure, error message format, status codes). API
  versioning MUST be implemented when breaking changes are introduced.
- **Error Messages**: All user-facing error messages MUST be clear, actionable,
  and non-technical when possible. Error responses MUST include appropriate HTTP
  status codes. Validation errors MUST identify specific fields and provide
  guidance on correction.
- **Response Times**: Interactive API endpoints MUST respond within 2 seconds
  under normal load. Long-running operations (simulations) MUST provide
  progress indicators or asynchronous processing with status endpoints. Timeout
  errors MUST be handled gracefully with informative messages.
- **Configuration Validation**: User configuration files (`config.yml`) MUST be
  validated on load with clear error messages for invalid values. Default values
  MUST be provided where appropriate. Configuration schema MUST be documented.
- **Frontend State Handling**: React views that fetch or derive data MUST render
  explicit loading, success, empty, and error states. Spinners or skeletons
  MUST NOT hide missing empty-state or retry behavior.
- **Accessible Interaction Patterns**: Forms, buttons, dialogs, tables, and
  navigation MUST be operable by keyboard and understandable to assistive
  technologies. Placeholder text MUST NOT be the sole label for inputs.
- **Design Consistency**: Shared UI patterns (buttons, inputs, spacing,
  typography, validation display, and status messaging) MUST be reused through
  common components or documented conventions rather than reimplemented ad hoc.

### Performance Requirements

**The application MUST meet performance benchmarks and be optimized for production workloads.**

- **Simulation Performance**: Single simulation trials MUST complete within reasonable time bounds (target: <100ms per trial for standard configurations). Simulation engines MUST support parallel execution where applicable. Memory usage MUST be bounded and monitored.
- **API Performance**: API endpoints MUST handle concurrent requests without degradation. Database queries (if applicable) MUST be optimized and avoid N+1 problems. Caching MUST be implemented for expensive computations or frequently accessed data.
- **Profiling and Monitoring**: Performance-critical code paths MUST be profiled using cProfile or equivalent tools. Profiling results MUST be reviewed before merging performance-sensitive changes. Memory leaks MUST be identified and resolved.
- **Resource Efficiency**: The application MUST operate within reasonable memory constraints. Large datasets MUST be processed incrementally or streamed when possible. Unnecessary data loading or computation MUST be avoided.

## Governance

### Amendment Procedure

Constitutional amendments require:

1. **Proposal**: A detailed proposal describing the principle change, rationale,
   and impact assessment.
1. **Review**: Review by project maintainers with consideration of backward
   compatibility and migration paths.
1. **Version Update**: Semantic versioning update (MAJOR.MINOR.PATCH) based on change impact:

   - **MAJOR**: Backward-incompatible principle changes, removal of principles, or fundamental redefinitions.
   - **MINOR**: Addition of new principles or significant expansion of existing guidance.
   - **PATCH**: Clarifications, wording improvements, typo fixes, or non-semantic refinements.
1. **Documentation**: Update of all dependent templates and documentation to reflect changes.
1. **Communication**: Clear communication of changes to all contributors.

### Compliance Review

- All pull requests MUST be reviewed for constitutional compliance before merging.
- Automated checks (linting, type checking, tests) MUST pass as a minimum compliance threshold.
- Manual review MUST verify adherence to principles not covered by automation.
- Violations MUST be addressed before merge approval unless explicitly exempted via constitutional amendment.

### Version History

- **1.6.0** (2026-04-27): Expanded Testing Standards › React Frontend
  Test-Driven Development with concrete quality patterns derived from a
  review of `frontend/src/App.test.tsx`: network-handler purity, no debug
  leftovers, `queryBy*` for negative presence, shared default handlers and
  URL constants, behavioral input coverage, region-scoped status
  assertions, asserting on rendered data (not only structure), determinism
  for in-flight UI state via deferred promises or fake timers, and one
  observable behavior per test. Updated plan and spec templates accordingly.
- **1.5.0** (2026-04-05): Expanded Testing Standards with modern React
  test-driven development: React Testing Library and accessibility-first queries,
  user-event, Vitest/Jest + jsdom, MSW-style network mocking, hook testing
  discipline, async patterns, snapshot limits, and test co-location.
- **1.4.0** (2026-03-09): Added governance for a React + TypeScript frontend,
  including frontend architecture, accessibility, typed API boundaries, and
  frontend testing expectations. Updated Speckit templates and README to align
  with the monorepo frontend/backend structure.
- **1.3.0** (2025-12-23): Expanded Testing Standards with guidance on data‑driven, fixture‑based test design, domain‑aligned test models, and explicit controller wiring. Updated plan and task templates to reflect test‑design expectations.
- **1.2.1** (2025-12-21): Updated static analysis tooling from Pylint+Black to Ruff for linting and formatting. Type checking remains Pyright.
- **1.2.0** (2025-12-12): Added principles for object models over dictionaries, named function arguments, and test-driven development. Clarified testing exception applies only to scripts/notebooks not used as application inputs. Testing requirements remain strict for all application code (simulator and Flask app).
- **1.1.0** (2025-12-10): Added exception to testing requirements for standalone scripts/notebooks not used as application inputs. Testing standards remain strict for simulator and Flask app functionality.
- **1.0.0** (2025-12-10): Initial constitution establishing code quality, testing, UX consistency, and performance principles.
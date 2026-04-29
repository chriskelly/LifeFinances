# Feature Specification: Split Configuration UI and Simulation Backend

**Feature Branch**: `001-react-flask-migration`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Migrate from the current Flask web interface defined in the @backend/ directory to a simple React frontend with a similar interface. Define a backend Flask API that can pass the necessary data to the frontend. Connect the two services together and verify connection & performance."

## Assumptions

- The product today offers a single-page experience: editable configuration text, save actions, optional simulation run, display of success percentage, and a scrollable table of the first simulation outcome. This feature preserves that experience while separating what runs in the browser from what runs on the server.
- Trust, deployment, and authentication boundaries stay equivalent to the current application (single-user, local or trusted network use unless a future feature changes that).
- Planning and implementation may choose concrete stacks and integration patterns consistent with the input above and repository standards; this specification defines required outcomes, not file layout or framework versions.
- "Similar interface" means a two-panel layout (configuration editing on one side, results on the other), primary actions for save-only and save-with-simulation, and a bounded scroll area for tabular results comparable to the current layout.
- Configuration editing remains a raw text workflow in this feature; redesigning the configuration into structured forms is out of scope.
- The new browser client becomes the primary interface for configuration editing and simulation review in this workflow; maintaining the legacy server-rendered page as a parallel supported path is out of scope.
- Simulation results are generated from the latest persisted configuration; running simulations against unsaved in-editor changes is out of scope.
- This feature does not introduce persistent simulation result history; users only need to view the latest generated result in the current workflow.

## Clarifications

### Session 2026-04-05

- Q: What access model should this feature support? → A: Single-user tool; no new authentication or multi-user roles.
- Q: What configuration editing mode should this feature support? → A: Raw text editor only, matching today's behavior.
- Q: What is the intended cutover for the legacy UI? → A: Replace the legacy UI for this workflow.
- Q: What configuration should simulation run against? → A: Simulation always runs against the saved persisted configuration.
- Q: What simulation result persistence scope should this feature support? → A: No result history; show only the latest generated result.
- Q: How should Save vs Save & run map to API calls? → A: Only two primary actions: Save → PUT config only; Save & run → PUT config then POST simulation/run. No standalone run without that save sequence.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View and edit configuration (Priority: P1)

A user opens the configuration experience and sees the same financial configuration text they would previously see on the home page. They can edit the text and save their changes without running a simulation.

**Why this priority**: Without reliable configuration viewing and persistence, no other workflow is usable; this is the minimum viable slice.

**Independent Test**: Can be verified by loading the experience, confirming the displayed text matches the authoritative stored configuration, editing text, saving, and confirming a subsequent load shows the saved content. Delivers immediate value for configuration maintenance.

**Acceptance Scenarios**:

1. **Given** stored configuration exists, **When** the user opens the configuration experience, **Then** the user sees the current configuration text ready for editing  
2. **Given** the user has edited the configuration text, **When** they choose save without simulation, **Then** the system persists the changes and confirms success clearly  
3. **Given** invalid or unpersistable configuration content, **When** the user attempts to save, **Then** the user receives a clear, actionable error and the prior authoritative configuration remains unchanged unless partially saved behavior is explicitly defined in implementation  

---

### User Story 2 - Run simulation and review results (Priority: P2)

Using **Save & run**, the user persists the current editor text and then runs the simulation in one intended sequence. The system shows the chance-of-success percentage and a tabular preview of the first simulation result, in line with the prior single-page application’s “Save & Run Simulation” control.

**Why this priority**: This is the primary analytical outcome users get from the tool after configuration work.

**Independent Test**: Can be verified by placing valid configuration in the editor, choosing **Save & run**, and checking that the success percentage and first-result table content appear and match expectations from the existing simulation engine for the same inputs. Delivers the core analytical value.

**Acceptance Scenarios**:

1. **Given** valid configuration text in the editor, **When** the user chooses **Save & run**, **Then** the system persists that text and then runs the simulation so the user sees an updated success percentage and a scrollable table of the first result  
2. **Given** a simulation that cannot complete, **When** the user chooses **Save & run**, **Then** the user sees a clear error and can still edit or use **Save**  
3. **Given** a long-running simulation, **When** the user waits after **Save & run**, **Then** the interface indicates progress or busy state so the user knows work is in flight  
4. **Given** the configuration experience, **When** the user inspects available actions, **Then** there are exactly two primary persistence-related actions—**Save** and **Save & run**—and there is no separate control that runs simulation without performing **Save & run**’s save-then-run sequence  

---

### User Story 3 - Verify connectivity and responsiveness (Priority: P3)

Stakeholders can confirm that the browser experience and the supporting service work together end-to-end, and that typical interactions remain responsive enough for interactive use.

**Why this priority**: Reduces delivery risk and regression risk when replacing the monolithic page; supports confidence before broader rollout.

**Independent Test**: Can be verified with a short, documented checklist (automated or manual) that exercises each required operation and records timing or pass/fail against agreed thresholds. Delivers operational confidence.

**Acceptance Scenarios**:

1. **Given** both client and server processes are running as documented for development, **When** a verifier performs the connectivity checklist, **Then** every required operation (load configuration, save, save & run) succeeds  
2. **Given** normal operating conditions, **When** a verifier measures time-to-display for configuration load and for **Save & run** using the standard sample configuration, **Then** results meet the success criteria for responsiveness  

---

### Edge Cases

- **Invalid configuration text**: Save or simulation fails with a message the user can understand; the system does not silently discard user input without feedback.  
- **Very large configuration or results**: The UI remains usable (scrolling, performance degradation bounded per success criteria); consider caps or warnings if outputs exceed practical display limits.  
- **Concurrent edits**: If multiple sessions or tabs exist, behavior matches a documented rule (last-write-wins, reload warning, or equivalent).  
- **Service unavailable**: The client shows a clear connection or service error; users can retry without losing unsaved local edits where technically feasible.  
- **Partial failure after save**: If persistence succeeds but simulation fails, the user still has saved configuration and understands which step failed.  
- **Reopen behavior**: If the user refreshes or reopens the client without running a new simulation, the feature does not need to restore prior simulation output beyond whatever is available from the latest active session behavior.  

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST present the active financial configuration as editable text to the single user of the tool in the dedicated configuration experience.  
- **FR-001a**: System MUST preserve the current single-user access model and MUST NOT require new authentication, account management, or per-user data separation as part of this feature.  
- **FR-001b**: System MUST provide configuration editing as raw text and MUST NOT require a structured form-based editing experience as part of this feature.  
- **FR-002**: Users MUST be able to persist configuration changes without triggering simulation.  
- **FR-003**: Users MUST be able to persist configuration and request an updated simulation from the same experience.  
- **FR-003a**: Simulation execution MUST use the latest persisted configuration as its source of truth and MUST NOT depend on unsaved in-editor edits.  
- **FR-003b**: The configuration experience MUST expose exactly two primary persistence-related controls matching legacy parity: **Save** (persist only) and **Save & run** (persist then run simulation). The system MUST NOT provide a separate primary control that runs simulation without performing the same persist step used by **Save & run**.  
- **FR-004**: After a successful simulation refresh, the system MUST display a success (or “chance of success”) percentage and a tabular view of the first simulation result, scoped and scrollable in a manner comparable to the prior layout.  
- **FR-004a**: The system MUST support display of the latest generated simulation result only and MUST NOT require persistent simulation history or reopening of prior results as part of this feature.  
- **FR-005**: The supporting backend MUST expose the data and operations the client needs to implement FR-001 through FR-004 without requiring server-rendered HTML for those flows.  
- **FR-005a**: The browser client MUST serve as the supported interface for this workflow once the feature is complete; the legacy server-rendered page is not required to remain a supported alternative for the same workflow.  
- **FR-006**: System MUST validate and handle errors for save and simulation operations with user-visible outcomes (success, validation error, or system error).  
- **FR-007**: Documentation or developer-facing quickstart MUST describe how to run the client and backend together so connectivity verification can be repeated.  

### Key Entities *(include if feature involves data)*

- **Active configuration**: The canonical configuration text used by the simulation; attributes include raw text content and versioning or timestamps only as needed for consistency.  
- **Simulation outcome summary**: The aggregate success metric shown to the user after a run.  
- **First-result preview**: Tabular data derived from the first simulation scenario for display; structure aligns with what users previously saw in HTML table form.  

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete the full flow—open the experience, view configuration, save changes, and obtain one updated simulation result view—in one sitting without using the legacy server-rendered form for those steps.  
- **SC-002**: Under normal conditions, configuration text is visible within 2 seconds of opening the configuration experience after the client is ready.  
- **SC-003**: Under normal conditions, after requesting simulation refresh with the project’s standard sample configuration, users see updated success percentage and first-result preview within 10 seconds on reference hardware, or the deviation is documented with cause.  
- **SC-004**: A repeatable connectivity verification (documented checklist or automated smoke suite) passes for all operations in FR-007 before the feature is considered done.  

### Testing Requirements *(constitution-aligned)*

- **TR-001**: Test-Driven Development (TDD) MUST be used: tests written before implementation for all application code (backend and frontend)  
- **TR-002**: Test coverage MUST achieve minimum 80% for new application modules; critical financial calculations, simulation logic, and high-impact financial user journeys MUST achieve 95%+ coverage or equivalent confidence  
- **TR-003**: Backend tests MUST use pytest with appropriate fixtures; frontend tests MUST use React Testing Library (or equivalent accessibility-first model), Vitest or Jest (or repo-documented equivalent), and a DOM environment (e.g. jsdom)  
- **TR-004**: Unit tests MUST complete in under 1 second per test  
- **TR-005**: Integration tests MUST complete in under 10 seconds per test  
- **TR-006**: API endpoints MUST have integration tests verifying status codes, response formats, and error handling  
- **TR-007**: Frontend features that fetch or derive data MUST test loading, success, empty, and error states  
- **TR-008**: Frontend user flows MUST include accessibility checks for labels, keyboard interaction, and visible focus behavior where applicable  
- **TR-009**: *Exception*: Standalone scripts/notebooks NOT used as inputs, imports, or dependencies for the application MAY be exempted from testing requirements (see constitution Testing Standards section)  
- **TR-010**: Frontend tests MUST query the UI as users perceive it (roles, accessible names, visible text); `data-testid` MUST be a last resort and justified  
- **TR-011**: Frontend user interactions MUST be driven with `@testing-library/user-event` (or project equivalent); HTTP MUST be mocked at the network boundary (e.g. MSW), not by spying on internal fetch in components  
- **TR-012**: Custom hooks MUST be tested with `renderHook` (or equivalent) and production-like provider wiring; tests MUST NOT assert React implementation details  

### Performance Requirements *(constitution-aligned)*

- **PR-001**: Interactive API endpoints MUST respond within 2 seconds under normal load  
- **PR-002**: Simulation operations MUST meet performance targets (<100ms per trial for standard configurations; document deviations with cause per SC-003)  
- **PR-003**: Memory usage MUST be bounded and monitored  
- **PR-004**: Performance-critical code paths MUST be profiled before merge  

# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

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
- **PR-002**: Simulation operations MUST meet performance targets (specify: e.g., <100ms per trial)
- **PR-003**: Memory usage MUST be bounded and monitored
- **PR-004**: Performance-critical code paths MUST be profiled before merge

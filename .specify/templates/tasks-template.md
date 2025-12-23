---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The examples below include test tasks. Tests are OPTIONAL - only include them if explicitly requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools (Ruff)
- [ ] T004 [P] Configure type checking (Pyright)
- [ ] T005 [P] Setup pytest configuration and test structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 1 (REQUIRED per constitution) ⚠️

> **NOTE: TDD REQUIRED - Write these tests FIRST, ensure they FAIL before implementation**
> **CONSTITUTION**: Test-Driven Development (TDD) MUST be used. All new application code (simulator and Flask app) MUST include tests. Test coverage MUST meet minimum 80% (95%+ for financial calculations). Where behavior is complex, tests SHOULD use reusable fixtures, factories, and domain-aligned helper dataclasses instead of ad-hoc inline setup, and SHOULD derive expectations from shared data (fixtures, canonical CSVs, or domain objects) rather than hard-coded magic numbers. *Exception*: Standalone scripts/notebooks NOT used as inputs, imports, or dependencies for the application MAY be exempted.

- [ ] T010 [P] [US1] Unit tests for [component] in tests/unit/test_[name].py
- [ ] T011 [P] [US1] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T012 [P] [US1] Integration test for [user journey] in tests/integration/test_[name].py
- [ ] T013 [US1] Verify test coverage meets constitution requirements (80% minimum, 95%+ for financial logic)

### Implementation for User Story 1

- [ ] T014 [P] [US1] Create [Entity1] model in src/models/[entity1].py (use object model, not dict; with type hints and docstrings)
- [ ] T015 [P] [US1] Create [Entity2] model in src/models/[entity2].py (use object model, not dict; with type hints and docstrings)
- [ ] T016 [US1] Implement [Service] in src/services/[service].py (depends on T014, T015; use named arguments in function calls)
- [ ] T017 [US1] Implement [endpoint/feature] in src/[location]/[file].py (use named arguments in function calls)
- [ ] T018 [US1] Add validation and error handling (with clear, actionable error messages)
- [ ] T019 [US1] Add logging for user story 1 operations
- [ ] T020 [US1] Verify Ruff linting passes
- [ ] T021 [US1] Verify Ruff formatting passes
- [ ] T022 [US1] Verify Pyright type checking passes
- [ ] T023 [US1] Add module and function docstrings per constitution

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 2 (REQUIRED per constitution) ⚠️

> **CONSTITUTION**: Test-Driven Development (TDD) MUST be used. All new application code MUST include tests. *Exception*: Standalone scripts/notebooks NOT used as inputs, imports, or dependencies for the application MAY be exempted.

- [ ] T023 [P] [US2] Unit tests for [component] in tests/unit/test_[name].py
- [ ] T024 [P] [US2] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T025 [P] [US2] Integration test for [user journey] in tests/integration/test_[name].py
- [ ] T026 [US2] Verify test coverage meets constitution requirements (80% minimum, 95%+ for financial logic)

### Implementation for User Story 2

- [ ] T027 [P] [US2] Create [Entity] model in src/models/[entity].py (use object model, not dict; with type hints and docstrings)
- [ ] T028 [US2] Implement [Service] in src/services/[service].py (use named arguments in function calls)
- [ ] T029 [US2] Implement [endpoint/feature] in src/[location]/[file].py (use named arguments in function calls)
- [ ] T030 [US2] Integrate with User Story 1 components (if needed)
- [ ] T031 [US2] Verify Ruff linting passes
- [ ] T032 [US2] Verify Ruff formatting passes
- [ ] T033 [US2] Verify Pyright type checking passes
- [ ] T034 [US2] Add module and function docstrings per constitution

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Tests for User Story 3 (REQUIRED per constitution) ⚠️

> **CONSTITUTION**: Test-Driven Development (TDD) MUST be used. All new application code MUST include tests. *Exception*: Standalone scripts/notebooks NOT used as inputs, imports, or dependencies for the application MAY be exempted.

- [ ] T034 [P] [US3] Unit tests for [component] in tests/unit/test_[name].py
- [ ] T035 [P] [US3] Contract test for [endpoint] in tests/contract/test_[name].py
- [ ] T036 [P] [US3] Integration test for [user journey] in tests/integration/test_[name].py
- [ ] T037 [US3] Verify test coverage meets constitution requirements (80% minimum, 95%+ for financial logic)

### Implementation for User Story 3

- [ ] T038 [P] [US3] Create [Entity] model in src/models/[entity].py (use object model, not dict; with type hints and docstrings)
- [ ] T039 [US3] Implement [Service] in src/services/[service].py (use named arguments in function calls)
- [ ] T040 [US3] Implement [endpoint/feature] in src/[location]/[file].py (use named arguments in function calls)
- [ ] T041 [US3] Verify Ruff linting passes
- [ ] T042 [US3] Verify Ruff formatting passes
- [ ] T043 [US3] Verify Pyright type checking passes
- [ ] T044 [US3] Add module and function docstrings per constitution

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in docs/
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Verify overall test coverage meets 80% minimum (95%+ for financial logic) for application code
- [ ] TXXX [P] Profile performance-critical paths using cProfile
- [ ] TXXX [P] Verify all tests complete within performance targets (<1s unit, <10s integration)
- [ ] TXXX [P] Run Ruff linting on entire codebase
- [ ] TXXX [P] Run Ruff formatting check on entire codebase
- [ ] TXXX [P] Verify Pyright type checking passes across all new code
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation
- [ ] TXXX Verify API response times meet <2s target for interactive endpoints

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together (if tests requested):
Task: "Contract test for [endpoint] in tests/contract/test_[name].py"
Task: "Integration test for [user journey] in tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in src/models/[entity1].py"
Task: "Create [Entity2] model in src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

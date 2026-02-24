# Tasks: Spending Controller

**Input**: Design documents from `/workspace/specs/001-spending-controller/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓

**Tests**: This feature requires TDD per constitution TR-001. All test tasks are included below and MUST be completed before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `app/` for source, `tests/` for tests
- Following established LifeFInances project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify existing project structure supports the spending controller refactoring

- [x] T001 Verify Python 3.10+ environment and dependencies (pydantic, numpy, dataclasses, pytest)
- [x] T002 [P] Verify Ruff linting configuration in pyproject.toml
- [x] T003 [P] Verify Pyright type checking configuration in pyrightconfig.json
- [x] T004 [P] Review existing allocation controller pattern in app/models/controllers/allocation.py for reference
- [x] T005 Review existing config strategy pattern in app/models/config/strategy.py for reference

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Update configuration layer that ALL subsequent work depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 [P] Create reusable test fixtures for spending profiles in tests/conftest.py (sample profiles, users with spending configs)
- [x] T007 [P] Create test fixture for State objects with various dates and inflation values in tests/conftest.py
- [x] T008 Refactor app/models/config/spending.py to implement new config structure (InflationFollowingConfig, SpendingStrategyOptions)
- [x] T009 Update app/models/config/user.py to change from spending: Spending to spending_strategy: SpendingStrategyOptions
- [x] T010 Update tests/sample_configs/full_config.yml to use new spending_strategy format

**Checkpoint**: Configuration layer refactored - controller implementation can now begin

---

## Phase 3: User Story 1 - Basic Inflation-Following Spending (Priority: P1) 🎯 MVP

**Goal**: Implement spending controller with inflation_following strategy that calculates spending based on profiles and inflation

**Independent Test**: Configure spending profiles with different yearly amounts and end dates, run simulation, verify spending calculations are correct for each interval with inflation applied

### Tests for User Story 1 (REQUIRED per constitution - TDD) ⚠️

> **NOTE: TDD REQUIRED - Write these tests FIRST, ensure they FAIL before implementation**
> **CONSTITUTION**: Test-Driven Development (TDD) MUST be used. Test coverage MUST achieve 95%+ for financial calculations. Tests SHOULD use reusable fixtures and derive expectations from shared data.

- [x] T011 [P] [US1] Unit tests for SpendingProfile validation in tests/models/config/test_spending.py (empty list, out-of-order, last profile with end_date, chronological ordering)
- [x] T012 [P] [US1] Unit tests for InflationFollowingConfig validation in tests/models/config/test_spending.py (profile validation delegation, error messages)
- [x] T013 [P] [US1] Unit tests for SpendingStrategyOptions in tests/models/config/test_spending.py (chosen_strategy property, default inflation_following)
- [x] T014 [P] [US1] Unit tests for _InflationFollowingStrategy.calc_spending in tests/models/controllers/test_spending.py (profile selection, inflation application, negative return, boundary conditions)
- [x] T015 [P] [US1] Unit tests for Controller initialization in tests/models/controllers/test_spending.py (strategy selection, invalid strategy name)
- [x] T016 [P] [US1] Unit tests for Controller.calc_spending delegation in tests/models/controllers/test_spending.py
- [x] T017 [US1] Integration tests for StateChangeComponents using spending controller in tests/models/financial/test_state_change.py (replace old _calc_spending tests)
- [x] T018 [US1] Verify test coverage meets 95%+ for spending calculation logic

### Implementation for User Story 1

- [x] T019 [P] [US1] Implement _Strategy ABC in app/models/controllers/spending.py (abstract base class with calc_spending method)
- [x] T020 [P] [US1] Implement _InflationFollowingStrategy in app/models/controllers/spending.py (dataclass, calc_spending with profile selection logic per FR-007, FR-008, FR-009)
- [x] T021 [US1] Implement Controller class in app/models/controllers/spending.py (__init__ with strategy selection, calc_spending delegation per FR-001)
- [x] T022 [US1] Add spending controller to Controllers dataclass in app/models/controllers/__init__.py per FR-010
- [x] T023 [US1] Update StateChangeComponents._calc_spending to use controllers.spending.calc_spending in app/models/financial/state_change.py per FR-011
- [x] T024 [US1] Remove old _calc_spending static method from app/models/financial/state_change.py
- [x] T025 [US1] Add module-level docstring to app/models/controllers/spending.py per constitution
- [x] T026 [US1] Add comprehensive docstrings to all classes and methods in app/models/controllers/spending.py per constitution
- [x] T027 [US1] Verify all type hints are present in app/models/controllers/spending.py per constitution
- [x] T028 [US1] Verify named arguments used in function calls in app/models/controllers/spending.py per constitution
- [x] T029 [US1] Run Ruff linting on modified files (app/models/config/spending.py, app/models/controllers/spending.py, app/models/financial/state_change.py)
- [x] T030 [US1] Run Ruff formatting on modified files
- [x] T031 [US1] Run Pyright type checking on modified files
- [x] T032 [US1] Verify all tests pass with new implementation
- [x] T033 [US1] Profile spending calculation performance (target: <1ms per call) per PR-002

**Checkpoint**: At this point, User Story 1 should be fully functional - spending controller calculates spending correctly, all tests pass, maintains calculation accuracy per SC-001

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and improvements across the feature

- [x] T034 [P] Run full test suite and verify 95%+ coverage for spending calculation logic per TR-002
- [x] T035 [P] Verify all unit tests complete in <1s per test per TR-004
- [x] T036 [P] Verify integration tests complete in <10s per test per TR-005
- [x] T037 [P] Run Ruff linting on entire modified codebase
- [x] T038 [P] Run Ruff formatting check on entire modified codebase
- [x] T039 [P] Run Pyright type checking on entire modified codebase
- [x] T040 [P] Verify no circular dependencies introduced per constitution
- [x] T041 [P] Validate configuration schema matches contracts/spending_config_schema.json
- [x] T042 [P] Review data-model.md accuracy against implementation
- [x] T043 [P] Review quickstart.md examples work correctly
- [x] T044 Compare spending calculation results before/after refactoring to verify SC-001 (identical calculations)
- [x] T045 Verify spending calculation performance remains <1ms per interval per SC-002
- [x] T046 Verify configuration validation catches all invalid scenarios per SC-003 (run validation test suite)
- [x] T047 Verify spending Controller follows allocation Controller pattern per SC-004 (architectural consistency review)
- [x] T048 Update any additional sample configs or documentation as needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS User Story 1
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **Polish (Phase 4)**: Depends on User Story 1 completion

### Within User Story 1

**Test-first flow (TDD)**:
1. T011-T018: Write all tests first (all can run in parallel marked [P])
2. Verify all tests FAIL (no implementation yet)
3. T019-T024: Implement controller and integration (sequential dependencies)
4. T025-T033: Documentation, validation, performance checks
5. Verify all tests PASS

**Implementation dependencies**:
- T019, T020 can run in parallel (different classes)
- T021 depends on T019, T020 (Controller uses _Strategy and _InflationFollowingStrategy)
- T022 depends on T021 (Controllers dataclass imports Controller)
- T023 depends on T022 (StateChangeComponents uses controllers.spending)
- T024 depends on T023 (remove old method after new one works)
- T025-T033 can run in any order after T024

### Parallel Opportunities

**Phase 1 Setup**: All tasks T001-T005 can run in parallel (reviews of different files)

**Phase 2 Foundational**: T006 and T007 can run in parallel (different fixture types), T008 is independent

**Phase 3 Tests**: All test tasks T011-T016 can run in parallel (different test modules/test cases)

**Phase 3 Implementation**: T019 and T020 can run in parallel (different classes in same file, but different logical units)

**Phase 4 Polish**: Most tasks T034-T043 can run in parallel (independent validations)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all test writing tasks together (TDD - write these first):
Task T011: "Unit tests for SpendingProfile validation"
Task T012: "Unit tests for InflationFollowingConfig validation"
Task T013: "Unit tests for SpendingStrategyOptions"
Task T014: "Unit tests for _InflationFollowingStrategy.calc_spending"
Task T015: "Unit tests for Controller initialization"
Task T016: "Unit tests for Controller.calc_spending delegation"

# Then launch implementation of base classes together:
Task T019: "Implement _Strategy ABC"
Task T020: "Implement _InflationFollowingStrategy"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

This feature has only one user story (P1), so MVP = full feature:

1. Complete Phase 1: Setup (verify environment) → ~15 minutes
2. Complete Phase 2: Foundational (config refactoring) → ~1-2 hours
3. Complete Phase 3: User Story 1 (controller implementation) → ~3-4 hours
   - Tests first (T011-T018) → ~1-2 hours
   - Implementation (T019-T024) → ~1-2 hours
   - Validation (T025-T033) → ~30 minutes
4. Complete Phase 4: Polish (final validation) → ~30 minutes
5. **TOTAL ESTIMATED TIME**: ~5-7 hours

### Validation Checkpoints

**After Foundational Phase**:
- [ ] New config format loads successfully
- [ ] Config validation catches all error cases
- [ ] full_config.yml parses correctly

**After User Story 1 Implementation**:
- [ ] All tests pass (100% of tests written)
- [ ] Spending calculations match old implementation exactly
- [ ] Performance <1ms per calculation
- [ ] Type checking passes
- [ ] Linting passes

**After Polish Phase**:
- [ ] Test coverage ≥95% for financial logic
- [ ] All constitution requirements met
- [ ] All success criteria validated
- [ ] Documentation accurate

---

## Notes

### Task Format Compliance

- All tasks follow `- [ ] [ID] [P?] [Story?] Description with file path` format
- [P] marks parallelizable tasks (different files, no dependencies)
- [US1] marks all User Story 1 tasks for traceability
- File paths explicitly stated in all implementation tasks

### TDD Approach

Per constitution TR-001, this feature uses Test-Driven Development:
1. Write tests first (T011-T018)
2. Verify tests FAIL
3. Implement minimum code to pass tests (T019-T024)
4. Refactor and optimize (T025-T033)
5. All application code has corresponding tests

### Key Technical Decisions (from research.md)

- **Architecture**: Controller + Strategy pattern (following allocation.py)
- **Method Signature**: `calc_spending(state: State) -> float`
- **Profile Selection**: `date <= end_date` (profile active through boundary)
- **Validation**: Fail-fast at Pydantic model validation time
- **Return Value**: Negative float (outflow convention)

### Modified Files Summary

**New Files** (2):
- `app/models/controllers/spending.py` (~150 lines)
- `tests/models/controllers/test_spending.py` (~200 lines)

**Modified Files** (6):
- `app/models/config/spending.py` (refactor config classes)
- `app/models/config/user.py` (update spending_strategy field)
- `app/models/controllers/__init__.py` (add spending to Controllers)
- `app/models/financial/state_change.py` (use controller instead of static method)
- `tests/models/config/test_spending.py` (update validation tests)
- `tests/models/financial/test_state_change.py` (update integration tests)
- `tests/sample_configs/full_config.yml` (update config format)

### Success Criteria Mapping

- **SC-001** (identical calculations): Validated by T044
- **SC-002** (performance <1ms): Validated by T033, T045
- **SC-003** (validation catches 100%): Validated by T011-T013, T046
- **SC-004** (follows pattern): Validated by T047

### Constitution Compliance

All tasks ensure:
- ✅ Type hints on all public functions (T027)
- ✅ Ruff linting passes (T029, T037)
- ✅ Ruff formatting passes (T030, T038)
- ✅ Pyright type checking passes (T031, T039)
- ✅ Module and function docstrings (T025, T026)
- ✅ No circular dependencies (T040)
- ✅ Object models over dicts (Pydantic models, dataclasses)
- ✅ Named arguments in function calls (T028)
- ✅ TDD approach (tests T011-T018 before implementation T019-T024)
- ✅ 95%+ test coverage for financial logic (T018, T034)
- ✅ Pytest framework with fixtures (T006, T007)
- ✅ Performance targets defined and validated (T033, T045)


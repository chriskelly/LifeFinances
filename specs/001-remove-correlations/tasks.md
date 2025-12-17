# Tasks: Remove Variable Correlations from Economic Data Generation

**Feature Branch**: `001-remove-correlations`  
**Date**: 2025-12-16  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Summary

This feature removes correlation functionality from economic data generation, simplifying the codebase by generating independent variable data using univariate normal distributions. Tasks are organized by user story to enable independent implementation and testing.

**Total Tasks**: 36  
**Tasks by Story**: Setup: 4 tasks | US1 (P1): 8 tasks | US2 (P2): 11 tasks | US3 (P2): 6 tasks | Polish: 7 tasks

## Implementation Strategy

**MVP Scope**: User Story 1 (P1) - Core economic data generation without correlations. This delivers the primary functionality and can be independently tested.

**Incremental Delivery**:
1. **Phase 3 (US1)**: Core functionality - independent data generation
2. **Phase 4 (US2)**: Code cleanup - remove correlation dependencies
3. **Phase 5 (US3)**: Test updates - ensure all tests pass
4. **Phase 6**: Final polish and validation

**Parallel Opportunities**: 
- Test writing and implementation can be done in parallel within each story phase (TDD approach)
- File deletion tasks (US2) can be done in parallel
- Multiple test updates (US3) can be done in parallel

## Dependencies

**Story Completion Order**:
1. **US1 (P1)** must complete first - core functionality required for all other work
2. **US2 (P2)** can proceed after US1 - removes correlation code/files
3. **US3 (P2)** should follow US2 - updates tests to match new implementation
4. **Polish** - final validation after all stories complete

**Blocking Dependencies**:
- US2 depends on US1 (needs new implementation to remove old code)
- US3 depends on US2 (tests must match final code state)
- Polish depends on all stories

## Phase 1: Setup

**Goal**: Prepare development environment and verify prerequisites

**Independent Test**: Development environment is ready, all dependencies installed, existing tests pass

- [ ] T001 Verify development environment: Python 3.10.19, numpy 1.26.1, pytest available
- [ ] T002 Run existing test suite to establish baseline: `pytest tests/models/controllers/test_economic_data.py`
- [ ] T003 Verify test coverage baseline: `pytest --cov=app/models/controllers/economic_data tests/models/controllers/test_economic_data.py`
- [ ] T003a Profile baseline performance of `_gen_covariated_data()` for comparison: Create a profiling script to measure execution time and memory usage of the current correlated data generation function, save results for comparison in T034

## Phase 2: Foundational

**Goal**: No foundational tasks required - this is a refactoring of existing code

**Independent Test**: N/A

*No foundational tasks - proceed directly to user story phases*

## Phase 3: User Story 1 - Economic Data Generation Without Correlations (P1)

**Goal**: Generate economic simulation data using only variable statistics (mean yield and standard deviation) without correlations. Each variable's data is generated independently.

**Independent Test**: Run economic simulations and verify generated data matches expected statistical properties (mean and standard deviation) for each variable independently, without requiring correlation data files.

**Acceptance Criteria**:
1. VariableMixRepo with only statistics data produces economic data for all variables using only their individual mean yields and standard deviations
2. Generated data matches expected mean and standard deviation within acceptable tolerance
3. Economic simulations complete successfully and produce valid financial projections

### Tests (TDD - Write First)

- [ ] T004 [US1] Write test for `_gen_variable_data()` function signature and return type in `tests/models/controllers/test_economic_data.py`
- [ ] T005 [US1] Write test for `_gen_variable_data()` generates correct shape `(trial_qty, intervals_per_trial, num_variables)` in `tests/models/controllers/test_economic_data.py`
- [ ] T006 [US1] Write test for `_gen_variable_data()` statistical properties: mean within 1% tolerance, stdev within 10% tolerance per variable in `tests/models/controllers/test_economic_data.py`
- [ ] T007 [US1] Write test for `_gen_variable_data()` seeded parameter produces reproducible results in `tests/models/controllers/test_economic_data.py`

### Implementation

- [ ] T008 [US1] Rename `_gen_covariated_data()` to `_gen_variable_data()` in `app/models/controllers/economic_data.py`
- [ ] T009 [US1] Replace `np.random.multivariate_normal()` with independent `np.random.normal()` calls per variable in `_gen_variable_data()` in `app/models/controllers/economic_data.py`
- [ ] T010 [US1] Update `_gen_variable_data()` to use `np.random.default_rng()` for random number generation in `app/models/controllers/economic_data.py`
- [ ] T011 [US1] Update `_gen_variable_data()` docstring to reflect independent generation in `app/models/controllers/economic_data.py`

## Phase 4: User Story 2 - Remove Correlation Data Dependencies (P2)

**Goal**: Remove all correlation data files, correlation-related code, and correlation-related parameters from the codebase.

**Independent Test**: System initializes and runs without any correlation data files, correlation path parameters, or correlation matrix references in the code.

**Acceptance Criteria**:
1. CsvVariableMixRepo only requires statistics path parameter (no correlation path)
2. All correlation CSV files are removed
3. All correlation-related code (correlation matrix, covariance calculations, correlation processing) is removed

### Implementation

- [ ] T012 [US2] Remove `correlation_matrix` attribute from `VariableMix` dataclass in `app/models/controllers/economic_data.py`
- [ ] T013 [US2] Remove `correlation_path` parameter from `CsvVariableMixRepo.__init__()` in `app/models/controllers/economic_data.py`
- [ ] T014 [US2] Remove `_correlation_path` instance variable from `CsvVariableMixRepo` in `app/models/controllers/economic_data.py`
- [ ] T015 [US2] Remove `_process_correlation_data()` method from `CsvVariableMixRepo` in `app/models/controllers/economic_data.py`
- [ ] T016 [US2] Update `_gen_variable_mix()` to remove correlation matrix processing in `app/models/controllers/economic_data.py`
- [ ] T017 [US2] Remove `_gen_covariance_matrix()` function from `app/models/controllers/economic_data.py`
- [ ] T018 [US2] Update `EconomicEngine._gen_data()` to use `_gen_variable_data()` instead of `_gen_covariated_data()` in `app/models/controllers/economic_data.py`
- [ ] T019 [US2] Remove `CORRELATION_PATH` constant from `app/data/constants.py`
- [ ] T020 [US2] Update `CsvVariableMixRepo` initialization in `app/models/simulator.py` to remove `correlation_path` parameter

### File Deletion

- [ ] T021 [US2] Delete `app/data/variable_correlation.csv` file
- [ ] T022 [US2] Delete `tests/models/controllers/test_csv_variable_mix_repo_correlation.csv` file

## Phase 5: User Story 3 - Update Tests to Remove Correlation Dependencies (P2)

**Goal**: Update all tests to work without correlation data. Remove correlation-related test assertions and methods.

**Independent Test**: Test suite executes successfully with all tests passing without requiring correlation CSV files.

**Acceptance Criteria**:
1. All correlation-related test fixtures and assertions are removed
2. All tests pass without requiring correlation CSV files
3. Test coverage remains at or above required minimum (80% overall, 95%+ for financial calculations)

### Test Updates

- [ ] T023 [US3] Remove `correlation_path` from `csv_variable_mix_repo` fixture in `tests/models/controllers/test_economic_data.py`
- [ ] T024 [US3] Remove correlation-related assertions from `test_csv_variable_mix_repo()` in `tests/models/controllers/test_economic_data.py`
- [ ] T025 [US3] Remove `test_correlations()` method from `TestGenerateRates` class in `tests/models/controllers/test_economic_data.py`
- [ ] T026 [US3] Remove `test_all_variables_have_correlation_data()` function from `tests/models/controllers/test_economic_data.py`
- [ ] T027 [US3] Update `TestGenerateRates` class to use `_gen_variable_data()` instead of `_gen_covariated_data()` in `tests/models/controllers/test_economic_data.py`
- [ ] T028 [US3] Update test imports to remove `_gen_covariated_data` and add `_gen_variable_data` in `tests/models/controllers/test_economic_data.py`

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Final validation, code quality checks, and performance verification

**Independent Test**: All code quality gates pass, performance meets targets, full test suite passes

### Validation

- [ ] T029 Run full test suite and verify all tests pass: `pytest tests/models/controllers/test_economic_data.py`
- [ ] T030 Verify test coverage meets requirements (80% overall, 95%+ financial): `pytest --cov=app/models/controllers/economic_data --cov-report=term-missing tests/models/controllers/test_economic_data.py`
- [ ] T031 Verify no correlation references remain: `grep -r "correlation" app/models/controllers/economic_data.py app/data/constants.py app/models/simulator.py`
- [ ] T032 Run pylint and verify score ≥ 8.0: `pylint app/models/controllers/economic_data.py`
- [ ] T033 Run type checking: `pyright app/models/controllers/economic_data.py`
- [ ] T034 Profile `_gen_variable_data()` performance and compare to baseline from T003a to verify equivalent or better performance
- [ ] T035 Run integration tests: `pytest tests/test_simulator.py`

## Parallel Execution Examples

### Within User Story 1 (US1)

**Parallel Group 1** (Tests can be written in parallel):
- T004, T005, T006, T007 can be written simultaneously (different test functions)

**After tests written**:
- T008, T009, T010, T011 can be done sequentially (implementation depends on tests)

### Within User Story 2 (US2)

**Parallel Group 1** (Code removals in same file):
- T012, T013, T014, T015, T016 can be done in parallel (different parts of same class)

**Parallel Group 2** (Different files):
- T017, T019, T020 can be done in parallel (different files)
- T021, T022 can be done in parallel (file deletions)

### Within User Story 3 (US3)

**Parallel Group 1** (Test updates):
- T023, T024, T025, T026, T027, T028 can be done in parallel (different test functions/methods)

## Notes

- **TDD Approach**: Tests (T004-T007) must be written before implementation (T008-T011) per TR-001
- **File Paths**: All file paths are relative to repository root
- **Test Coverage**: Maintain 80% overall, 95%+ for financial calculations per TR-002
- **Performance**: Profile critical paths per PR-004 before merge
- **Code Quality**: All code must pass pylint ≥ 8.0 and type checking per constitution


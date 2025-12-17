# Feature Specification: Remove Variable Correlations from Economic Data Generation

**Feature Branch**: `001-remove-correlations`  
**Created**: 2025-12-16  
**Status**: Draft  
**Input**: User description: "Simplify the codebase by not using correlation between variable stats in @app/models/controllers/economic_data.py . Remove all code related to correlations, including tests and@app/data/variable_correlation.csv data. Economic data should only be based on variable_statistics now."

## Clarifications

### Session 2025-12-16

- Q: What statistical distribution method should be used to generate independent variable data? → A: Univariate normal distribution (one per variable, using its mean yield and standard deviation)
- Q: Should _gen_covariated_data function be renamed to reflect that it no longer generates covariated/correlated data? → A: Rename the function to `_gen_variable_data`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Economic Data Generation Without Correlations (Priority: P1)

The system generates economic simulation data using only variable statistics (mean yield and standard deviation) without considering correlations between variables. Each variable's data is generated independently based on its own statistical properties.

**Why this priority**: This is the core functionality change - economic data generation must work correctly without correlation dependencies. All other changes depend on this working properly.

**Independent Test**: Can be fully tested by running economic simulations and verifying that generated data matches expected statistical properties (mean and standard deviation) for each variable independently, without requiring correlation data files or correlation matrix calculations.

**Acceptance Scenarios**:

1. **Given** a VariableMixRepo with only statistics data, **When** economic data is generated, **Then** the system produces economic data for all variables using only their individual mean yields and standard deviations
2. **Given** economic data is generated, **When** statistical properties are analyzed, **Then** each variable's generated data matches its expected mean and standard deviation within acceptable tolerance
3. **Given** economic simulations are run, **When** results are compared to previous correlated versions, **Then** simulations complete successfully and produce valid financial projections

---

### User Story 2 - Remove Correlation Data Dependencies (Priority: P2)

The system no longer requires correlation data files or correlation-related code. All correlation CSV files, correlation matrix calculations, and correlation-related parameters are removed from the codebase.

**Why this priority**: This simplifies the codebase architecture and removes maintenance burden. The system should work with only statistics data, making it easier to maintain and understand.

**Independent Test**: Can be fully tested by verifying that the system initializes and runs without any correlation data files, correlation path parameters, or correlation matrix references in the code.

**Acceptance Scenarios**:

1. **Given** the system is initialized, **When** CsvVariableMixRepo is created, **Then** it only requires a statistics path parameter (no correlation path)
2. **Given** correlation data files exist in the codebase, **When** the feature is complete, **Then** all correlation CSV files are removed
3. **Given** code references correlation functionality, **When** the feature is complete, **Then** all correlation-related code (correlation matrix, covariance calculations, correlation processing) is removed

---

### User Story 3 - Update Tests to Remove Correlation Dependencies (Priority: P2)

All tests are updated to work without correlation data. Tests that verify correlation behavior are removed, and remaining tests verify that economic data generation works correctly with independent variable generation.

**Why this priority**: Tests must validate the new simplified behavior and ensure no correlation dependencies remain. This prevents regression and confirms the simplification is complete.

**Independent Test**: Can be fully tested by running the test suite and verifying all tests pass without correlation data files or correlation-related test assertions.

**Acceptance Scenarios**:

1. **Given** test files reference correlation data, **When** tests are updated, **Then** all correlation-related test fixtures and assertions are removed
2. **Given** the test suite is run, **When** all tests execute, **Then** all tests pass without requiring correlation CSV files
3. **Given** test coverage is measured, **When** the feature is complete, **Then** test coverage remains at or above the required minimum (80% overall, 95%+ for financial calculations)

---

### Edge Cases

- What happens when variable statistics data is missing or malformed? (System should handle gracefully with appropriate error messages)
- How does the system handle cases where the same variable statistics are used across multiple simulations? (Each simulation should generate independent data)
- What happens if variable statistics contain extreme values (very high/low mean yields or standard deviations)? (System should generate valid data within expected statistical bounds)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate economic data for each variable independently using only its mean yield and standard deviation from variable_statistics.csv
- **FR-002**: System MUST remove the correlation_path parameter from CsvVariableMixRepo initialization
- **FR-003**: System MUST remove correlation_matrix attribute from VariableMix dataclass
- **FR-004**: System MUST remove _process_correlation_data method from CsvVariableMixRepo
- **FR-005**: System MUST remove _gen_covariance_matrix function
- **FR-006**: System MUST rename _gen_covariated_data function to `_gen_variable_data` and modify it to generate independent variable data using univariate normal distribution (one per variable, using each variable's mean yield and standard deviation) without using multivariate normal distribution with covariance matrix
- **FR-007**: System MUST remove CORRELATION_PATH constant from app/data/constants.py
- **FR-008**: System MUST remove app/data/variable_correlation.csv file
- **FR-009**: System MUST remove tests/models/controllers/test_csv_variable_mix_repo_correlation.csv file
- **FR-010**: System MUST remove all correlation-related test assertions and test methods (e.g., test_correlations, test_all_variables_have_correlation_data)
- **FR-011**: System MUST update all code that initializes CsvVariableMixRepo to remove correlation_path parameter
- **FR-012**: System MUST ensure generated economic data maintains correct statistical properties (mean and standard deviation) for each variable independently

### Key Entities *(include if feature involves data)*

- **VariableMix**: Collection of variable statistics and lookup table (correlation_matrix removed)
- **CsvVariableMixRepo**: Repository that reads variable statistics from CSV (correlation_path parameter and correlation processing removed)
- **EconomicSimData**: Economic data for entire simulation (generation method simplified)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All economic simulations complete successfully without correlation data files, with 100% of simulation runs producing valid results
- **SC-002**: Codebase contains zero references to correlation_path, correlation_matrix, or correlation CSV files in application code
- **SC-003**: Test suite executes successfully with all tests passing, maintaining minimum 80% coverage (95%+ for financial calculations)
- **SC-004**: Economic data generation produces variables with statistical properties matching input statistics (mean within 1% tolerance, standard deviation within 10% tolerance) for each variable independently
- **SC-005**: Code simplification reduces complexity: correlation-related functions, methods, and data structures are completely removed (target: 100% removal of correlation code)

### Testing Requirements *(constitution-aligned)*

- **TR-001**: Test-Driven Development (TDD) MUST be used: tests written before implementation for all application code (simulator and Flask app)
- **TR-002**: Test coverage MUST achieve minimum 80% (95%+ for financial calculations and simulation logic) for application code (simulator and Flask app)
- **TR-003**: All tests MUST use pytest framework with appropriate fixtures
- **TR-004**: Unit tests MUST complete in under 1 second per test
- **TR-005**: Integration tests MUST complete in under 10 seconds per test
- **TR-006**: API endpoints MUST have integration tests verifying status codes, response formats, and error handling
- **TR-007**: *Exception*: Standalone scripts/notebooks NOT used as inputs, imports, or dependencies for the application MAY be exempted from testing requirements (see constitution Testing Standards section)

### Performance Requirements *(constitution-aligned)*

- **PR-001**: Interactive API endpoints MUST respond within 2 seconds under normal load
- **PR-002**: Simulation operations MUST meet performance targets: economic data generation completes in equivalent or better time compared to previous correlated version
- **PR-003**: Memory usage MUST be bounded and monitored (removing correlation matrices may reduce memory usage)
- **PR-004**: Performance-critical code paths MUST be profiled before merge

## Assumptions

- Independent variable generation (without correlations) is acceptable for the simulation use case
- Removing correlations will not significantly impact simulation accuracy for the intended use cases
- Variable statistics data (mean yield and standard deviation) is sufficient for generating realistic economic scenarios

## Dependencies

- Variable statistics CSV file (app/data/variable_statistics.csv) must exist and be properly formatted
- All code that initializes CsvVariableMixRepo must be updated to remove correlation_path parameter
- Test fixtures that provide correlation_path must be updated or removed

## Out of Scope

- Modifying how inflation is handled or made cumulative
- Changing the statistical properties or format of variable_statistics.csv
- Adding new variable types or modifying existing variable definitions

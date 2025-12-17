# Research: Remove Variable Correlations from Economic Data Generation

**Date**: 2025-12-16  
**Feature**: Remove Variable Correlations from Economic Data Generation  
**Phase**: 0 - Research & Technical Decisions

## Overview

This research document consolidates technical decisions for removing correlation functionality from economic data generation. The feature involves replacing multivariate normal distribution with independent univariate normal distributions per variable.

## Technical Decisions

### Decision 1: Statistical Distribution Method

**Decision**: Use univariate normal distribution (one per variable) instead of multivariate normal distribution with covariance matrix.

**Rationale**: 
- Clarified in specification: univariate normal distribution per variable using each variable's mean yield and standard deviation
- Simpler implementation: no need for covariance matrix calculations
- Maintains statistical properties: each variable still follows its specified mean and standard deviation
- Reduces computational complexity: O(n) per variable instead of O(n²) for covariance matrix

**Alternatives Considered**:
- **Multivariate normal without correlation**: Would still require covariance matrix (diagonal matrix), but this is equivalent to independent univariate distributions
- **Other distributions**: Uniform, log-normal, etc. - Rejected because normal distribution is standard for financial modeling and matches existing approach
- **Keep correlations but simplify**: Rejected because the goal is to remove correlation functionality entirely

**Implementation Approach**:
- Replace `np.random.multivariate_normal()` with independent `np.random.normal()` calls per variable
- Use `np.random.default_rng()` for random number generation (already in use)
- Maintain seeded parameter for reproducibility in tests

### Decision 2: Function Naming

**Decision**: Rename `_gen_covariated_data` to `_gen_variable_data`.

**Rationale**:
- Clarified in specification: function should be renamed to reflect independent generation
- `_gen_covariated_data` name is misleading after removing correlations
- Better code clarity: function name should match its behavior
- Follows naming conventions: descriptive names improve maintainability

**Alternatives Considered**:
- **Keep existing name**: Rejected because it's misleading and violates code clarity principles
- **Remove function entirely**: Rejected because the function is still needed for data generation, just with different implementation
- **Other names**: `_gen_uncorrelated_data`, `_gen_statistical_data`, `_gen_independent_data` - Considered but `_gen_variable_data` is clearest

**Implementation Approach**:
- Rename function to `_gen_variable_data`
- Update all call sites (currently only called from `EconomicEngine._gen_data()`)
- Update function docstring to reflect independent generation

### Decision 3: Data Structure Changes

**Decision**: Remove `correlation_matrix` attribute from `VariableMix` dataclass.

**Rationale**:
- No longer needed: independent generation doesn't require correlation data
- Simplifies data model: reduces memory usage and complexity
- Cleaner API: `VariableMix` only contains what's actually used

**Alternatives Considered**:
- **Keep attribute but set to None**: Rejected because it adds unnecessary complexity and potential for bugs
- **Keep attribute but ignore it**: Rejected because dead code violates code quality principles

**Implementation Approach**:
- Remove `correlation_matrix: NDArray[np.floating]` from `VariableMix` dataclass
- Remove `_process_correlation_data()` method from `CsvVariableMixRepo`
- Remove `correlation_path` parameter from `CsvVariableMixRepo.__init__()`
- Update `_gen_variable_mix()` to not process correlation data

### Decision 4: Random Number Generation

**Decision**: Use `np.random.default_rng()` for independent normal distributions per variable.

**Rationale**:
- Already in use: `rng = np.random.default_rng()` exists at module level
- Modern NumPy approach: `default_rng()` is recommended over legacy `np.random` functions
- Maintains seeded parameter: can use `rng = np.random.default_rng(seed=0)` when `seeded=True`
- Independent generation: each variable gets its own random samples

**Alternatives Considered**:
- **Legacy np.random.normal()**: Rejected because `default_rng()` is the modern, recommended approach
- **Single RNG instance per trial**: Considered but not necessary; module-level RNG is sufficient
- **Thread-local RNG**: Not needed for this single-threaded application

**Implementation Approach**:
- Use existing `rng` instance or create new `rng = np.random.default_rng(seed=0)` when `seeded=True`
- Generate data per variable: `rng.normal(mean=mean_yield, scale=stdev, size=(trial_qty, intervals_per_trial))`
- Stack results: `np.stack()` or `np.array()` to combine variables into 3D array shape `(trial_qty, intervals_per_trial, num_variables)`

## Dependencies & Integration Points

### Files to Modify

1. **app/models/controllers/economic_data.py**:
   - Remove `correlation_matrix` from `VariableMix`
   - Remove `_process_correlation_data()` method
   - Remove `correlation_path` parameter from `CsvVariableMixRepo`
   - Remove `_gen_covariance_matrix()` function
   - Rename and modify `_gen_covariated_data()` to `_gen_variable_data()`
   - Update `EconomicEngine._gen_data()` to use new function name

2. **app/data/constants.py**:
   - Remove `CORRELATION_PATH` constant

3. **app/models/simulator.py**:
   - Update `CsvVariableMixRepo` initialization to remove `correlation_path` parameter

### Files to Delete

1. **app/data/variable_correlation.csv**: Correlation data file
2. **tests/models/controllers/test_csv_variable_mix_repo_correlation.csv**: Test correlation data file

### Files to Update (Tests)

1. **tests/models/controllers/test_economic_data.py**:
   - Remove `correlation_path` from `csv_variable_mix_repo` fixture
   - Remove correlation-related test assertions
   - Remove `test_correlations()` method
   - Remove `test_all_variables_have_correlation_data()` function
   - Update tests to verify independent generation (statistical properties only)

## Performance Considerations

### Expected Performance Impact

- **Positive**: Removing covariance matrix calculation reduces O(n²) computation
- **Positive**: Simpler random number generation may be faster
- **Neutral**: Overall simulation time should be equivalent or better (per PR-002)

### Memory Impact

- **Positive**: Removing correlation matrices reduces memory usage
- **Positive**: Smaller `VariableMix` dataclass (one less array attribute)

### Profiling Requirements

- Profile `_gen_variable_data()` function to ensure performance meets targets
- Compare before/after performance for economic data generation
- Verify memory usage reduction

## Testing Strategy

### Unit Tests

- Test `_gen_variable_data()` generates correct shape: `(trial_qty, intervals_per_trial, num_variables)`
- Test statistical properties: mean within 1% tolerance, standard deviation within 10% tolerance per variable
- Test seeded parameter: reproducible results when `seeded=True`
- Test `CsvVariableMixRepo` initialization without `correlation_path`

### Integration Tests

- Test `EconomicEngine` generates data successfully without correlation files
- Test full simulation runs complete successfully
- Test API endpoints still work (no API changes expected)

### Test Coverage

- Maintain 80% overall coverage
- Maintain 95%+ coverage for financial calculations (economic data generation)

## Risk Assessment

### Low Risk

- **Code removal**: Removing unused code is low risk
- **Function renaming**: Straightforward refactoring
- **Test updates**: Well-defined test changes

### Medium Risk

- **Statistical accuracy**: Need to verify independent generation maintains statistical properties
- **Performance**: Need to profile to ensure no performance regression

### Mitigation

- Comprehensive testing of statistical properties
- Performance profiling before merge
- TDD approach ensures tests validate behavior before implementation

## Open Questions

None - all technical decisions have been made and clarified in the specification.

## References

- NumPy documentation: `np.random.default_rng()` and `rng.normal()`
- Specification: `specs/001-remove-correlations/spec.md`
- Existing code: `app/models/controllers/economic_data.py`


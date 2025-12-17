# Quickstart: Remove Variable Correlations

**Date**: 2025-12-16  
**Feature**: Remove Variable Correlations from Economic Data Generation

## Overview

This feature removes correlation functionality from economic data generation, simplifying the codebase by generating independent variable data using univariate normal distributions.

## What Changed

### Before
- Economic variables were generated using multivariate normal distribution with correlation matrix
- Required both `variable_statistics.csv` and `variable_correlation.csv` files
- Correlation matrix stored in `VariableMix` dataclass

### After
- Economic variables are generated independently using univariate normal distribution per variable
- Only requires `variable_statistics.csv` file
- No correlation matrix needed

## Key Changes for Developers

### 1. CsvVariableMixRepo Initialization

**Before**:
```python
repo = CsvVariableMixRepo(
    statistics_path=Path("app/data/variable_statistics.csv"),
    correlation_path=Path("app/data/variable_correlation.csv"),  # REMOVED
)
```

**After**:
```python
repo = CsvVariableMixRepo(
    statistics_path=Path("app/data/variable_statistics.csv"),
)
```

### 2. VariableMix Structure

**Before**:
```python
variable_mix = VariableMix(
    variable_stats=[...],
    correlation_matrix=np.array([...]),  # REMOVED
    lookup_table={...},
)
```

**After**:
```python
variable_mix = VariableMix(
    variable_stats=[...],
    lookup_table={...},
)
```

### 3. Data Generation Function

**Before**:
```python
data = _gen_covariated_data(
    variable_mix=variable_mix,
    trial_qty=100,
    intervals_per_trial=40,
)
```

**After**:
```python
data = _gen_variable_data(  # RENAMED
    variable_mix=variable_mix,
    trial_qty=100,
    intervals_per_trial=40,
)
```

## Files Modified

1. **app/models/controllers/economic_data.py**
   - Remove `correlation_matrix` from `VariableMix`
   - Remove `_process_correlation_data()` method
   - Remove `correlation_path` parameter from `CsvVariableMixRepo`
   - Remove `_gen_covariance_matrix()` function
   - Rename `_gen_covariated_data()` to `_gen_variable_data()`
   - Update implementation to use independent univariate normal distributions

2. **app/data/constants.py**
   - Remove `CORRELATION_PATH` constant

3. **app/models/simulator.py**
   - Update `CsvVariableMixRepo` initialization

## Files Deleted

1. **app/data/variable_correlation.csv** - No longer needed
2. **tests/models/controllers/test_csv_variable_mix_repo_correlation.csv** - Test data file removed

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run economic data tests specifically
pytest tests/models/controllers/test_economic_data.py

# Run with coverage
pytest --cov=app/models/controllers/economic_data tests/models/controllers/test_economic_data.py
```

### Test Changes

- Removed correlation-related test assertions
- Removed `test_correlations()` method
- Removed `test_all_variables_have_correlation_data()` function
- Updated tests to verify independent generation (statistical properties only)

### Expected Test Results

- All tests should pass
- Coverage should remain at 80%+ overall, 95%+ for financial calculations
- Statistical property tests verify mean within 1% tolerance, stdev within 10% tolerance

## Verification

### Verify Correlation Removal

```bash
# Search for any remaining correlation references
grep -r "correlation" app/models/controllers/economic_data.py
grep -r "correlation_path" app/
grep -r "correlation_matrix" app/
grep -r "CORRELATION_PATH" app/

# Should return no results (or only in comments/docstrings)
```

### Verify Statistical Properties

Run the test suite and verify:
- Mean of generated data matches input mean_yield within 1% tolerance
- Standard deviation matches input stdev within 10% tolerance
- Each variable is generated independently

## Performance

### Expected Impact

- **Positive**: Removing covariance matrix calculation reduces O(n²) computation
- **Positive**: Simpler random number generation
- **Neutral to Positive**: Overall simulation time should be equivalent or better

### Profiling

```bash
# Profile economic data generation
python -m cProfile -o profile.stats -m pytest tests/models/controllers/test_economic_data.py::TestGenerateRates::test_statistics
```

## Common Issues

### Issue: "correlation_path" parameter error

**Solution**: Update all `CsvVariableMixRepo` initializations to remove `correlation_path` parameter.

### Issue: "correlation_matrix" attribute error

**Solution**: Remove any code that accesses `VariableMix.correlation_matrix`. This attribute no longer exists.

### Issue: Tests failing with correlation assertions

**Solution**: Remove correlation-related test assertions. Tests should only verify statistical properties (mean, standard deviation) per variable independently.

## Next Steps

1. Review the [specification](spec.md) for detailed requirements
2. Review the [data model](data-model.md) for structure changes
3. Review the [research](research.md) for technical decisions
4. Follow TDD approach: write tests first, then implement changes
5. Run full test suite to ensure no regressions
6. Profile performance to verify improvements

## Related Documentation

- [Specification](spec.md) - Feature requirements and success criteria
- [Research](research.md) - Technical decisions and rationale
- [Data Model](data-model.md) - Entity structures and relationships
- [Implementation Plan](plan.md) - Overall planning and structure


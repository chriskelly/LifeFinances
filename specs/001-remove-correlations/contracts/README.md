# API Contracts: Remove Variable Correlations

**Date**: 2025-12-16  
**Feature**: Remove Variable Correlations from Economic Data Generation

## Overview

This feature is a **refactoring** that removes correlation functionality from economic data generation. **No API contracts change** - all external interfaces remain unchanged.

## No API Changes

### REST API Endpoints

- **Status**: No changes
- **Rationale**: This is an internal refactoring of data generation logic. API endpoints are not modified.

### Internal Function Contracts

The following internal functions have **signature changes** (not API contracts):

#### CsvVariableMixRepo.__init__()

**Before**:
```python
def __init__(self, statistics_path: Path, correlation_path: Path):
```

**After**:
```python
def __init__(self, statistics_path: Path):
```

**Impact**: Internal only - all callers must be updated to remove `correlation_path` parameter.

#### _gen_covariated_data() → _gen_variable_data()

**Before**:
```python
def _gen_covariated_data(
    variable_mix: VariableMix,
    trial_qty: int,
    intervals_per_trial: int,
    seeded: bool = False,
) -> np.ndarray:
```

**After**:
```python
def _gen_variable_data(
    variable_mix: VariableMix,
    trial_qty: int,
    intervals_per_trial: int,
    seeded: bool = False,
) -> np.ndarray:
```

**Impact**: Internal only - function renamed and implementation changed, but signature and return type unchanged.

## Data Structure Contracts

### VariableMix (Internal)

**Breaking Change**: `correlation_matrix` attribute removed.

**Impact**: Internal only - not part of public API. Only affects internal code that accesses this attribute.

### EconomicSimData, EconomicTrialData, EconomicStateData (Public)

**Status**: No explicit contract requirements - structures may be modified as needed.

**Contract**:
- Array shapes remain: 3D for EconomicSimData, 2D for EconomicTrialData, 1D for EconomicStateData
- Field types remain: NDArray for rates, float for inflation, dict for lookup

## Migration Impact

### For API Consumers

- **No changes required** - API endpoints unchanged
- **No changes required** - Response formats unchanged

### For Internal Code

- **Must update**: All `CsvVariableMixRepo` initializations
- **Must update**: Any code accessing `VariableMix.correlation_matrix`
- **Must update**: Tests that reference correlation functionality

## Validation

All existing API integration tests should continue to pass without modification, confirming that no API contracts have changed.


# Data Model: Remove Variable Correlations from Economic Data Generation

**Date**: 2025-12-16  
**Feature**: Remove Variable Correlations from Economic Data Generation  
**Phase**: 1 - Design & Contracts

## Overview

This document describes the data model changes for removing correlation functionality from economic data generation. The changes primarily involve removing correlation-related attributes and simplifying the data structures.

## Entity Changes

### VariableMix

**Current Structure**:
```python
@dataclass
class VariableMix:
    variable_stats: list[_StatisticBehavior]
    correlation_matrix: NDArray[np.floating]  # TO BE REMOVED
    lookup_table: dict[str, int]
```

**Updated Structure**:
```python
@dataclass
class VariableMix:
    variable_stats: list[_StatisticBehavior]
    lookup_table: dict[str, int]
```

**Changes**:
- **REMOVED**: `correlation_matrix` attribute
- **UNCHANGED**: `variable_stats` - list of variable statistics (mean yield, standard deviation)
- **UNCHANGED**: `lookup_table` - mapping of variable names to indices

**Validation Rules**:
- `variable_stats` must not be empty
- `lookup_table` keys must match variable names from statistics CSV
- `lookup_table` values must be valid indices into `variable_stats` list

### _StatisticBehavior

**Structure** (unchanged):
```python
@dataclass
class _StatisticBehavior:
    mean_yield: float
    stdev: float
    
    def gen_interval_behavior(self) -> _StatisticBehavior:
        # Returns interval-adjusted statistics
```

**Validation Rules**:
- `mean_yield` must be positive (yield > 1.0 represents growth)
- `stdev` must be non-negative
- `gen_interval_behavior()` returns new instance with interval-adjusted values

### CsvVariableMixRepo

**Current Initialization**:
```python
def __init__(self, statistics_path: Path, correlation_path: Path):
    self._statistics_path = statistics_path
    self._correlation_path = correlation_path  # TO BE REMOVED
    self._lookup_table = {}
    self._variable_mix = self._gen_variable_mix()
```

**Updated Initialization**:
```python
def __init__(self, statistics_path: Path):
    self._statistics_path = statistics_path
    self._lookup_table = {}
    self._variable_mix = self._gen_variable_mix()
```

**Changes**:
- **REMOVED**: `correlation_path` parameter
- **REMOVED**: `_correlation_path` instance variable
- **REMOVED**: `_process_correlation_data()` method
- **UPDATED**: `_gen_variable_mix()` no longer processes correlation data

**Validation Rules**:
- `statistics_path` must point to valid CSV file
- CSV file must have headers: `VariableLabel, AverageYield, StdDeviation`
- All rows must have valid numeric values for AverageYield and StdDeviation

### EconomicSimData, EconomicTrialData, EconomicStateData

**Structure**:
```python
@dataclass
class EconomicSimData:
    asset_rates: NDArray[np.floating]  # 3D: (trial_qty, intervals_per_trial, num_assets)
    inflation: NDArray[np.floating]   # 2D: (trial_qty, intervals_per_trial)
    asset_lookup: dict[str, int]

@dataclass
class EconomicTrialData:
    asset_rates: NDArray[np.floating]  # 2D: (intervals_per_trial, num_assets)
    inflation: NDArray[np.floating]     # 1D: (intervals_per_trial,)
    asset_lookup: dict[str, int]

@dataclass
class EconomicStateData:
    asset_rates: NDArray[np.floating]  # 1D: (num_assets,)
    inflation: float
    asset_lookup: dict[str, int]
```

**Validation Rules**:
- Array shapes must match expected dimensions
- `asset_lookup` keys must match variable names (excluding "Inflation")
- `asset_lookup` values must be valid indices into `asset_rates` arrays
- Inflation values must be positive (cumulative inflation)

## Data Flow

### Before (with correlations)

1. Load statistics CSV → `_process_statistics_data()` → `variable_stats`, `lookup_table`
2. Load correlation CSV → `_process_correlation_data()` → `correlation_matrix`
3. Combine → `VariableMix(variable_stats, correlation_matrix, lookup_table)`
4. Generate covariance matrix → `_gen_covariance_matrix()` → `covariance_matrix`
5. Generate data → `_gen_covariated_data()` with `multivariate_normal()` → `yield_matrix`

### After (independent generation)

1. Load statistics CSV → `_process_statistics_data()` → `variable_stats`, `lookup_table`
2. Combine → `VariableMix(variable_stats, lookup_table)` (no correlation_matrix)
3. Generate data → `_gen_variable_data()` with independent `normal()` per variable → `yield_matrix`

## State Transitions

### VariableMix Creation

**Before**:
```
CSV files → [process statistics] → variable_stats
         → [process correlations] → correlation_matrix
         → VariableMix(variable_stats, correlation_matrix, lookup_table)
```

**After**:
```
CSV file → [process statistics] → variable_stats
        → VariableMix(variable_stats, lookup_table)
```

### Economic Data Generation

**Before**:
```
VariableMix → [gen covariance matrix] → covariance_matrix
           → [multivariate_normal] → yield_matrix (correlated)
```

**After**:
```
VariableMix → [independent normal per variable] → yield_matrix (independent)
```

## Data Validation

### Input Validation (CSV)

- **File existence**: Statistics CSV file must exist
- **Format**: Must be valid CSV with expected headers
- **Data types**: AverageYield and StdDeviation must be parseable as floats
- **Value ranges**: 
  - AverageYield should be positive (typically > 1.0 for growth)
  - StdDeviation should be non-negative

### Output Validation (Generated Data)

- **Shape**: Must match expected dimensions `(trial_qty, intervals_per_trial, num_variables)`
- **Statistical properties**: 
  - Mean within 1% tolerance of input mean_yield
  - Standard deviation within 10% tolerance of input stdev
- **Value ranges**: Generated yields should be positive (no negative yields)

## Relationships

### VariableMix → EconomicSimData

- `VariableMix.variable_stats` provides parameters for generating `EconomicSimData.asset_rates`
- `VariableMix.lookup_table` maps to `EconomicSimData.asset_lookup` (after removing Inflation)

### CsvVariableMixRepo → VariableMix

- `CsvVariableMixRepo` creates and returns `VariableMix` instance
- No longer requires correlation data to create `VariableMix`

## Migration Notes

### Breaking Changes

- **CsvVariableMixRepo.__init__()**: `correlation_path` parameter removed (breaking change for callers)
- **VariableMix**: `correlation_matrix` attribute removed (breaking change if accessed directly)

### Non-Breaking Changes

- **Generated data shape**: Unchanged (same 3D/2D/1D array shapes)
- **Statistical properties**: Maintained (mean and standard deviation per variable)

### Migration Path

1. Update all `CsvVariableMixRepo` initializations to remove `correlation_path` parameter
2. Remove any code that accesses `VariableMix.correlation_matrix`
3. Update tests to remove correlation-related assertions
4. Delete correlation CSV files


# API Contracts: Total Portfolio Allocation Strategy

**Date**: 2025-12-21  
**Feature**: Total Portfolio Allocation Strategy

## Overview

This feature does not introduce new API endpoints. It extends the existing portfolio configuration system and allocation calculation framework. The contracts defined here are internal interfaces and configuration schemas.

## Configuration Schema

### TotalPortfolioStrategyConfig

**Type**: Pydantic Model  
**Location**: `app/models/config/portfolio.py`

**JSON Schema** (for configuration files):

```json
{
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": false,
      "description": "Whether the strategy is enabled"
    },
    "chosen": {
      "type": "boolean",
      "default": false,
      "description": "Whether this strategy is the chosen one"
    },
    "low_risk_allocation": {
      "type": "object",
      "additionalProperties": {
        "type": "number",
        "minimum": 0,
        "maximum": 1
      },
      "default": {"TIPS": 1.0},
      "description": "Low risk allocation percentages by asset (must sum to 1.0)"
    },
    "high_risk_allocation": {
      "type": "object",
      "additionalProperties": {
        "type": "number",
        "minimum": 0,
        "maximum": 1
      },
      "default": {"US_Stock": 1.0},
      "description": "High risk allocation percentages by asset (must sum to 1.0)"
    },
    "RRA": {
      "type": "number",
      "minimum": 0,
      "exclusiveMinimum": true,
      "default": 2.0,
      "description": "Relative Risk Aversion parameter (must be positive)"
    }
  },
  "required": ["low_risk_allocation", "high_risk_allocation", "RRA"],
  "additionalProperties": false
}
```

**YAML Example**:

```yaml
allocation_strategy:
  total_portfolio:
    enabled: true
    chosen: true
    low_risk_allocation:
      TIPS: 1.0
    high_risk_allocation:
      US_Stock: 0.7
      Intl_ex_US_Stock: 0.3
    RRA: 2.0
```

## Internal Interfaces

### _Strategy.gen_allocation() (Modified)

**Signature**:
```python
@abstractmethod
def gen_allocation(
    self, 
    state: State, 
    controllers: Controllers | None = None
) -> np.ndarray:
    """Generate allocation array for a portfolio
    
    Args:
        state: Current simulation state
        controllers: Optional controllers object (required for some strategies)
        
    Returns:
        np.ndarray: Allocation ratios for each asset, sums to 1.0
    """
```

**Contract**:
- Must return `np.ndarray` with length equal to number of assets
- Array must sum to 1.0 (100%)
- All values must be non-negative
- `controllers` parameter is optional for backward compatibility
- `_TotalPortfolioStrategy` requires `controllers` to be non-None

### _TotalPortfolioStrategy.gen_allocation()

**Signature**:
```python
def gen_allocation(
    self, 
    state: State, 
    controllers: Controllers | None = None
) -> np.ndarray:
    """Generate allocation array using total portfolio strategy
    
    Args:
        state: Current simulation state
        controllers: Controllers object (required, must not be None)
        
    Returns:
        np.ndarray: Allocation ratios for each asset, sums to 1.0
        
    Raises:
        ValueError: If controllers is None
    """
```

**Preconditions**:
- `controllers` must not be None
- `controllers.job_income.get_total_income()` must be callable
- `controllers.social_security` MAY be None (no social security benefits); if not None, `controllers.social_security.calc_payment()` must be callable
- `controllers.pension` MAY be None (no pension benefits); if not None, `controllers.pension.calc_payment()` must be callable
- `state.net_worth` must be a valid number (can be zero/negative)
- `state.interval_idx` must be valid

**Postconditions**:
- Returned array has length equal to `len(asset_lookup)`
- Returned array sums to 1.0
- All values in returned array are non-negative

**Side Effects**: None (pure function)

## Error Responses

### Configuration Validation Errors

| Error | HTTP Status | Response Format |
|-------|-------------|-----------------|
| Allocation doesn't sum to 1.0 | 400 (if via API) | `{"error": "low_risk_allocation must sum to 1.0"}` |
| Invalid asset name | 400 (if via API) | `{"error": "{asset} is not allowed in allocation options"}` |
| RRA <= 0 | 400 (if via API) | `{"error": "RRA must be greater than 0"}` |

### Runtime Errors

| Error | Handling |
|-------|----------|
| controllers is None | `ValueError` raised |
| Division by zero | Returns `low_risk_allocation` (graceful fallback) |
| Zero total portfolio | Returns `low_risk_allocation` (graceful fallback) |
| Social security or pension returns zero | Include 0 in income calculation, continue normally |
| Incompatible benefit strategies with TotalPortfolioStrategy | `ValueError` raised during `User` config validation with clear message |

## Integration Points

### With Existing Allocation Framework

- Extends `AllocationOptions` without breaking existing strategies
- Follows same pattern as `FlatAllocationStrategyConfig` and `NetWorthPivotStrategyConfig`
- Uses same validation helpers (`_validate_allocation()`)

### With Simulation Engine

- Integrates seamlessly with existing `Controller.gen_allocation()` flow
- No changes required to simulation engine interface
- `Controller.gen_allocation()` passes entire `controllers` object to strategy

### With Configuration System

- Uses Pydantic validation (same as other config models)
- Follows `StrategyConfig` / `StrategyOptions` pattern
- Automatically handled by `chosen_strategy` validator

## Testing Contracts

### Unit Test Contracts

- Test `TotalPortfolioStrategyConfig` validation
- Test `_TotalPortfolioStrategy.__post_init__()` calculations
- Test `gen_allocation()` with various scenarios
- Test edge cases (zero savings, no income, etc.)

### Integration Test Contracts

- Test full simulation with total portfolio strategy
- Test configuration loading from YAML
- Test allocation changes over time as income decreases

## Performance Contracts

- Allocation calculation: <1ms per interval
- Present value calculation: <10ms per interval
- Strategy initialization: <10ms (one-time cost)
- No significant memory overhead


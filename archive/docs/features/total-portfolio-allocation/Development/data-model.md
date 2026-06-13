# Data Model: Total Portfolio Allocation Strategy

**Date**: 2025-12-21  
**Feature**: Total Portfolio Allocation Strategy  
**Phase**: 1 - Design

## Entity: TotalPortfolioStrategyConfig

**Location**: `app/models/config/portfolio.py`

**Inheritance**: Inherits from `StrategyConfig`

**Purpose**: Configuration model for the total portfolio allocation strategy, containing user-defined allocations and risk aversion parameter.

### Attributes

| Attribute | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `low_risk_allocation` | `dict[str, float]` | `{"TIPS": 1.0}` | Must sum to 1.0, all keys in ALLOWED_ASSETS | Low/risk-free portion of portfolio allocation |
| `high_risk_allocation` | `dict[str, float]` | `{"US_Stock": 1.0}` | Must sum to 1.0, all keys in ALLOWED_ASSETS | High risk portion of portfolio allocation |
| `RRA` | `float` | `2.0` | Must be positive | Relative Risk Aversion parameter |
| `enabled` | `bool` | `False` | Inherited from StrategyConfig | Whether strategy is enabled |
| `chosen` | `bool` | `False` | Inherited from StrategyConfig | Whether strategy is chosen |

### Validation Rules

1. **Allocation Validation**: Both `low_risk_allocation` and `high_risk_allocation` must:
   - Sum to 1.0 (100%) using `_validate_allocation()` helper
   - Contain only assets from `ALLOWED_ASSETS`
   - Have non-negative values (implicit in sum-to-1.0 check)

2. **RRA Validation**: 
   - Must be positive (`> 0`)
   - No upper bound validation or warnings required

### Relationships

- **Part of**: `AllocationOptions` (added as `total_portfolio: TotalPortfolioStrategyConfig | None = None`)
- **Used by**: `_TotalPortfolioStrategy` in `app/models/controllers/allocation.py`

### Example Configuration

```python
TotalPortfolioStrategyConfig(
    enabled=True,
    chosen=True,
    low_risk_allocation={"TIPS": 1.0},
    high_risk_allocation={"US_Stock": 0.7, "Intl_ex_US_Stock": 0.3},
    RRA=2.0
)
```

## Entity: _TotalPortfolioStrategy

**Location**: `app/models/controllers/allocation.py`

**Inheritance**: Inherits from `_Strategy` (abstract base class)

**Purpose**: Implementation of the total portfolio allocation strategy that calculates allocation based on total portfolio value and risk aversion.

### Attributes (Instance Variables)

| Attribute | Type | Source | Description |
|-----------|------|--------|-------------|
| `config` | `TotalPortfolioStrategyConfig` | Constructor parameter | Strategy configuration |
| `asset_lookup` | `dict[str, int]` | Constructor parameter | Lookup table for asset names to indices |
| `high_risk_allocation` | `np.ndarray` | `__post_init__` | High risk allocation as numpy array |
| `low_risk_allocation` | `np.ndarray` | `__post_init__` | Low risk allocation as numpy array |
| `expected_high_risk_return` | `float` | `__post_init__` | Weighted average return of high risk allocation |
| `expected_high_risk_stdev` | `float` | `__post_init__` | Weighted average standard deviation of high risk allocation |
| `expected_low_risk_return` | `float` | `__post_init__` | Weighted average return of low risk allocation (used as discount rate) |
| `merton_share` | `float` | `__post_init__` | Merton Share = (E[High Risk Return] - E[Low Risk Return]) / (RRA * High Risk StDev^2) |
| `job_income_by_interval` | `np.ndarray` | `__post_init__` | Precomputed total job income per future interval (from current trial start) |
| `benefit_income_by_interval` | `np.ndarray` | `__post_init__` | Precomputed total benefit income (social security + pension) per future interval using fake States |
| `future_income_by_interval` | `np.ndarray` | `__post_init__` | Combined future income array (job income + benefit income) per future interval for NPV calculation |

### Calculated Attributes (in `__post_init__`)

1. **Convert allocations to arrays**: Use `_allocation_dict_to_array()` helper
2. **Read variable statistics**: Load from `app/data/variable_statistics.csv`
3. **Calculate expected returns**: 
   - Convert `AverageYield` to return: `return = yield - 1.0`
   - Calculate weighted average: `sum(allocation[asset] * return[asset] for asset in allocation)`
4. **Calculate expected standard deviations**: Weighted average similar to returns
5. **Calculate Merton Share**: `(expected_high_risk_return - expected_low_risk_return) / (RRA * expected_high_risk_stdev ** 2)`
6. **Precompute income arrays**:
   - For each future interval index `i`:
     - Create fake `State` object for interval `i` with:
       - Correct `interval_idx`, `date`, `inflation`, and other non-net-worth fields from user config
       - `net_worth` access raises `RuntimeError` (use property or descriptor pattern to prevent access)
     - `job_income_by_interval[i] = controllers.job_income.get_total_income(i)`
     - `benefit_income_by_interval[i] = sum(controllers.social_security.calc_payment(fake_state_i)) + controllers.pension.calc_payment(fake_state_i)`
     - `future_income_by_interval[i] = job_income_by_interval[i] + benefit_income_by_interval[i]` (combined future income)
   - Store all arrays as numpy arrays for reuse in `gen_allocation()`

### Methods

#### `gen_allocation(state: State, controllers: Controllers | None) -> np.ndarray`

**Parameters**:
- `state`: Current simulation state (contains net_worth, interval_idx, etc.)
- `controllers`: Controllers object (required for this strategy, contains job_income controller and optional social_security and pension controllers)

**Returns**: `np.ndarray` - Allocation ratios for each asset, sums to 1.0

**Algorithm**:
1. Validate `controllers` is not None (raise ValueError with clear message if None). If `controllers.social_security` or `controllers.pension` is None (no benefits configured), treat income from that source as 0 in all calculations.
2. Calculate Future Income PV:
   - Get annualized discount rate: `expected_low_risk_return` (annual return, e.g., 0.092 for 9.2%)
   - Convert to interval rate for NPV:
     - Annual yield = `1 + expected_low_risk_return`
     - Interval yield = `interval_yield(annual_yield)` = `annual_yield ** YEARS_PER_INTERVAL`
     - Interval rate = `interval_yield - 1`
   - Slice precomputed future income array from `state.interval_idx + 1` onward:
     - `future_income = future_income_by_interval[state.interval_idx + 1 :]`
     - `income_array = future_income` (combined job income + benefit income)
   - If `income_array` is empty (no future income), PV = 0
   - Otherwise, calculate PV using: `npf.npv(rate=interval_rate, values=income_array)`
3. Calculate Total Portfolio: `Future Income PV + state.net_worth`
4. Calculate Total Portfolio High Risk Amount: `Merton Share * Total Portfolio`
5. Calculate Savings High Risk Ratio: `min(1.0, Total Portfolio High Risk Amount / Savings)`
   - Handle division by zero: if Savings <= 0, use 0
6. Calculate Savings Low Risk Ratio: `1.0 - Savings High Risk Ratio`
7. Return allocation: `high_risk_allocation * Savings High Risk Ratio + low_risk_allocation * Savings Low Risk Ratio`

**Edge Cases**:
- Zero/negative savings: Use 0 for savings, calculate based on future income only
- Zero total portfolio: Return `low_risk_allocation` (most conservative)
- No future income (retired): Future Income PV = 0, Total Portfolio = Savings only
- Division by zero in Merton Share: Return `low_risk_allocation`
- Negative Merton Share: Cap at 0 (all low risk)

## Entity: AllocationOptions (Modified)

**Location**: `app/models/config/portfolio.py`

**Modification**: Add new attribute

### New Attribute

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `total_portfolio` | `TotalPortfolioStrategyConfig | None` | `None` | Total portfolio allocation strategy configuration |

### Updated Relationships

- Now contains: `flat`, `net_worth_pivot`, `total_portfolio`
- `chosen_strategy` validator automatically handles the new strategy option

## State Transitions

### Configuration Loading
1. User provides configuration in YAML/JSON
2. Pydantic validates `TotalPortfolioStrategyConfig`
3. Validator checks allocations sum to 1.0 and contain only allowed assets
4. Validator checks RRA is positive
5. Configuration stored in `AllocationOptions.total_portfolio`

### Strategy Initialization
1. `Controller.__init__()` detects `total_portfolio` strategy is chosen
2. Creates `_TotalPortfolioStrategy` instance with config and asset_lookup
3. `__post_init__` calculates expected returns, standard deviations, and Merton Share
4. Strategy ready for allocation generation

### Allocation Calculation (per interval)
1. `Controller.gen_allocation(state)` called with current state
2. `_TotalPortfolioStrategy.gen_allocation(state, controllers)` called with entire Controllers object
3. Future income PV calculated using job_income controller and (if present) social_security and pension controllers (missing controllers/strategies contribute 0 income)
4. Total portfolio value = Future Income PV + Savings
5. Merton Share applied to determine high/low risk split
6. Allocation array returned

## Data Flow

```
User Config (YAML)
    ↓
TotalPortfolioStrategyConfig (Pydantic validation)
    ↓
AllocationOptions.total_portfolio
    ↓
Controller.__init__() → _TotalPortfolioStrategy.__init__()
    ↓
__post_init__() calculates:
    - Expected returns from variable_statistics.csv
    - Expected standard deviations
    - Merton Share
    ↓
gen_allocation(state, controllers):
    - Calculate Future Income PV (using controllers.job_income, controllers.social_security, controllers.pension)
    - Calculate Total Portfolio
    - Apply Merton Share
    - Return allocation array
```

## Validation Rules Summary

1. **Allocation dictionaries**: Must sum to 1.0, contain only ALLOWED_ASSETS
2. **RRA**: Must be positive
3. **controllers parameter**: Required for `_TotalPortfolioStrategy.gen_allocation()` (provides access to job_income controller and optional social_security and pension controllers)
4. **User configuration compatibility**:
   - If `TotalPortfolioStrategy` is chosen for allocation:
     - Social security strategy MUST be age-based (e.g., `AgeStrategy`)
     - Pension strategy MUST be `AgeStrategy` or `Cashout` (no net-worth-based triggers)
5. **Final allocation**: Must sum to 1.0 (guaranteed by calculation)

## Error Handling

| Error Condition | Handling |
|-----------------|----------|
| Allocation doesn't sum to 1.0 | Raise `ValueError` in validator |
| Invalid asset in allocation | Raise `ValueError` in validator |
| RRA <= 0 | Raise `ValueError` in validator |
| controllers is None in gen_allocation() | Raise `ValueError` |
| Social security or pension returns zero (no benefits) | Include 0 in income calculation, continue normally |
| Division by zero in Merton Share | Return `low_risk_allocation` |
| Zero/negative total portfolio | Return `low_risk_allocation` |
| Zero/negative savings | Use 0 for savings, continue calculation |
| Incompatible benefit strategies with TotalPortfolioStrategy | Raise `ValueError` in `User` config validation with clear message |


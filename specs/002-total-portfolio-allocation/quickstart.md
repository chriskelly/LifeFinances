# Quickstart: Total Portfolio Allocation Strategy

**Date**: 2025-12-21  
**Feature**: Total Portfolio Allocation Strategy

## Overview

The Total Portfolio Allocation Strategy calculates asset allocation based on your total portfolio value (current savings + present value of future income) and your relative risk aversion. It uses the Merton Share formula to determine the optimal split between high-risk and low-risk assets.

## Configuration

### Basic Configuration

Add the `total_portfolio` strategy to your portfolio configuration:

```yaml
portfolio:
  current_net_worth: 250000
  tax_rate: 0.1
  allocation_strategy:
    total_portfolio:
      enabled: true
      chosen: true
      low_risk_allocation:
        TIPS: 1.0
      high_risk_allocation:
        US_Stock: 1.0
      RRA: 2.0
```

### Configuration Parameters

#### `low_risk_allocation` (dict[str, float])
- **Default**: `{"TIPS": 1.0}`
- **Description**: The low-risk/risk-free portion of your portfolio allocation
- **Requirements**: 
  - Must sum to 1.0 (100%)
  - All asset names must be in `ALLOWED_ASSETS`
  - Values must be between 0 and 1

**Example**:
```yaml
low_risk_allocation:
  TIPS: 0.8
  US_Bond: 0.2
```

#### `high_risk_allocation` (dict[str, float])
- **Default**: `{"US_Stock": 1.0}`
- **Description**: The high-risk portion of your portfolio allocation
- **Requirements**: Same as `low_risk_allocation`

**Example**:
```yaml
high_risk_allocation:
  US_Stock: 0.7
  Intl_ex_US_Stock: 0.3
```

#### `RRA` (float)
- **Default**: `2.0`
- **Description**: Relative Risk Aversion parameter
- **Requirements**: Must be positive (> 0)
- **Typical Range**: 0.5 to 10.0
  - Lower values (0.5-1.5): More risk-tolerant, favors high-risk allocation
  - Moderate values (2.0-4.0): Balanced risk preference
  - Higher values (5.0+): More risk-averse, favors low-risk allocation

## How It Works

### 1. Calculate Present Value of Future Income

The strategy calculates the present value of all your future income streams (user + partner) from the current simulation interval forward. The discount rate is the weighted average return of your low-risk allocation.

### 2. Calculate Total Portfolio

```
Total Portfolio = Current Savings + Present Value of Future Income
```

### 3. Calculate Merton Share

The Merton Share determines what portion of your total portfolio should be allocated to high-risk assets:

```
Merton Share = (Expected High Risk Return - Expected Low Risk Return) / (RRA * High Risk StDev^2)
```

Where:
- Expected returns and standard deviations are calculated from `variable_statistics.csv`
- RRA is your Relative Risk Aversion parameter

### 4. Determine Allocation

The strategy calculates:
- **Total Portfolio High Risk Amount** = Merton Share × Total Portfolio
- **Savings High Risk Ratio** = min(100%, Total Portfolio High Risk Amount / Savings)
- **Savings Low Risk Ratio** = 1 - Savings High Risk Ratio

Final allocation = `high_risk_allocation × Savings High Risk Ratio + low_risk_allocation × Savings Low Risk Ratio`

## Example Scenarios

### Scenario 1: Young Professional with High Future Income

**Configuration**:
- Current Savings: $50,000
- Future Income PV: $2,000,000
- RRA: 2.0
- Low Risk: 100% TIPS
- High Risk: 100% US_Stock

**Result**: 
- Total Portfolio = $2,050,000
- High future income relative to savings → More aggressive allocation to stocks
- Allocation adjusts as future income decreases over time

### Scenario 2: Near Retirement

**Configuration**:
- Current Savings: $1,500,000
- Future Income PV: $200,000 (few years left)
- RRA: 3.0
- Low Risk: 100% TIPS
- High Risk: 100% US_Stock

**Result**:
- Total Portfolio = $1,700,000
- Higher savings relative to future income → More conservative allocation
- Higher RRA → Further reduces stock allocation

### Scenario 3: Already Retired

**Configuration**:
- Current Savings: $2,000,000
- Future Income PV: $0 (retired)
- RRA: 2.0

**Result**:
- Total Portfolio = $2,000,000 (savings only)
- Allocation based solely on savings and RRA
- No future income to consider

## Edge Cases

### Zero or Negative Savings

If savings is zero or negative, the strategy:
- Uses 0 for savings in calculations
- Calculates allocation based on future income only
- Handles gracefully without errors

### No Future Income (Retired)

If there's no future income:
- Present value of future income = 0
- Total portfolio = current savings only
- Allocation calculated normally based on savings and RRA

### Zero Total Portfolio

If total portfolio is zero or negative:
- Returns the low-risk allocation (most conservative)
- Prevents invalid allocations

## Integration with Existing Strategies

The total portfolio strategy works alongside existing strategies:
- **Flat**: Fixed allocation regardless of state
- **Net Worth Pivot**: Allocation changes based on net worth target
- **Total Portfolio**: Allocation changes based on total portfolio (savings + future income) and risk aversion

You can only choose one strategy at a time via the `chosen: true` flag.

## Validation

The configuration is validated when loaded:
- Allocations must sum to 1.0
- All asset names must be in `ALLOWED_ASSETS`
- RRA must be positive
- **Benefit Strategy Compatibility**: When using `total_portfolio` strategy, social security must use an age-based strategy (`early`, `mid`, or `late`), and pension (if configured) must use an age-based strategy or `cash_out`. Net-worth-based benefit strategies are not compatible with total portfolio allocation to avoid circular dependencies.

Invalid configurations will raise clear error messages indicating what needs to be fixed.

### Example Valid Configuration

```yaml
portfolio:
  allocation_strategy:
    total_portfolio:
      chosen: true
      # ... other config ...

social_security_pension:
  strategy:
    mid:  # Age-based strategy (valid)
      chosen: true

admin:
  pension:
    strategy:
      early:  # Age-based strategy (valid)
        chosen: true
      # OR
      cash_out:  # Cash-out strategy (valid)
        chosen: true
```

### Example Invalid Configuration

```yaml
portfolio:
  allocation_strategy:
    total_portfolio:
      chosen: true
      # ... other config ...

social_security_pension:
  strategy:
    net_worth:  # Net-worth-based strategy (INVALID with total_portfolio)
      chosen: true
      net_worth_target: 1000000
```

This will raise a `ValueError` because net-worth-based benefit strategies create circular dependencies with total portfolio allocation.

## Performance

- Allocation calculation: <1ms per simulation interval
- Present value calculation: <10ms per interval
- No significant impact on overall simulation performance

## Dependencies

- `numpy-financial`: For present value calculations (automatically installed)
- Existing economic data from `variable_statistics.csv`
- Existing job income controller for future income streams

## Next Steps

1. Configure your `low_risk_allocation` and `high_risk_allocation` based on your preferences
2. Set your `RRA` based on your risk tolerance
3. Run simulations to see how allocation changes over time
4. Adjust parameters as needed to match your financial goals

## Development Commands

Feature-specific commands are available from this directory:

```bash
cd specs/002-total-portfolio-allocation

# Run feature-specific tests
make test

# Profile allocation performance
make profile

# Run tests with coverage
make coverage

# Show all available commands
make help
```

## See Also

- [Specification](./spec.md) - Full feature specification
- [Data Model](./data-model.md) - Detailed data structures
- [Implementation Plan](./plan.md) - Technical implementation details
- [Profiling Results](./profiling_results.md) - Performance analysis


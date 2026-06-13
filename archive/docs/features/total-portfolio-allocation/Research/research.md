# Research: Total Portfolio Allocation Strategy

**Date**: 2025-12-21  
**Feature**: Total Portfolio Allocation Strategy  
**Phase**: 0 - Research & Technical Decisions

## Research Questions

### 1. numpy-financial Library for Present Value Calculations

**Question**: Should we use numpy-financial for present value calculations, and is it available/appropriate?

**Decision**: Yes, use `numpy-financial` library for present value calculations.

**Rationale**: 
- The user explicitly requested using `numpy_financial.npv()` for present value calculations
- numpy-financial provides standard financial functions including `npv()` which is well-suited for discounting a series of future cash flows
- `npv()` is more efficient than calling `pv()` in a loop for multiple cash flows
- It integrates well with NumPy arrays already used in the codebase
- The library is maintained and provides the exact functionality needed

**Alternatives Considered**:
- Manual PV calculation: More error-prone and less maintainable
- scipy.financial: Less commonly used, numpy-financial is more standard
- Custom implementation: Unnecessary when a well-tested library exists
- Using `pv()` in a loop: Less efficient than `npv()` for multiple cash flows

**Implementation Notes**:
- Add `numpy-financial` to project dependencies (check if already present, add if not)
- Import as `import numpy_financial as npf` or `from numpy_financial import npv`
- Use `npf.npv(rate, values)` for present value calculations where `values` is an array of future cash flows

### 2. Accessing Expected Returns from variable_statistics.csv

**Question**: How to access expected returns and standard deviations from variable_statistics.csv for Merton Share calculations?

**Decision**: Read statistics directly from `variable_statistics.csv` using the existing CSV reading pattern, or access through VariableMix if available.

**Rationale**:
- The CSV file contains `AverageYield` (which represents expected returns as yields, e.g., 1.092 for 9.2% return)
- We need to convert yields to returns: `return = yield - 1` (e.g., 1.092 yield = 0.092 return)
- Standard deviations are directly available in the CSV
- The existing `CsvVariableMixRepo` pattern can be reused or we can read directly for strategy initialization

**Alternatives Considered**:
- Store statistics in config: Would duplicate data and create maintenance burden
- Hardcode values: Not maintainable, values may change
- Access through economic data controller: More complex, statistics are static

**Implementation Notes**:
- Read `variable_statistics.csv` in `__post_init__` of `_TotalPortfolioStrategy`
- Convert `AverageYield` to annual return: `annual_return = yield - 1.0` (e.g., 1.092 → 0.092)
- Use `StdDeviation` directly for standard deviation (already annualized)
- Calculate weighted averages based on allocation percentages
- **Note**: Returns are annualized and will need conversion to interval rates when used in NPV calculations (see Section 5 for conversion details)

### 3. Modifying _Strategy.gen_allocation() Signature

**Question**: How to modify the abstract `gen_allocation()` method to accept Controllers while maintaining backward compatibility?

**Decision**: Update the abstract method signature to accept an optional `controllers` parameter with default `None`, and update all existing strategies to handle the new signature.

**Rationale**:
- Total portfolio strategy needs access to multiple controllers to calculate future income: `controllers.job_income` for job income, `controllers.social_security` for social security payments, and `controllers.pension` for pension payments
- Passing the entire `Controllers` object provides access to all needed controllers in a single parameter
- Making `controllers` optional maintains backward compatibility
- Existing strategies (`_FlatAllocationStrategy`, `_NetWorthPivotStrategy`) can ignore the parameter
- Type hints make it clear which strategies require controllers

**Alternatives Considered**:
- Pass individual controllers (job_income, social_security, pension): More parameters, less clean interface
- Separate interface: Would require more refactoring
- Pass controllers through Controller class: Less flexible, harder to test
- Store controllers in strategy instance: Not appropriate for stateless strategies

**Implementation Notes**:
- Update `_Strategy.gen_allocation()` signature: `def gen_allocation(self, state: State, controllers: Controllers | None = None) -> np.ndarray:`
- Import `Controllers` type: `from app.models.controllers import Controllers`
- Update `_FlatAllocationStrategy.gen_allocation()` to accept but ignore controllers parameter
- Update `_NetWorthPivotStrategy.gen_allocation()` to accept but ignore controllers parameter
- Update `Controller.gen_allocation()` to pass `controllers` object to strategy
- `_TotalPortfolioStrategy.gen_allocation()` will require controllers (raise ValueError if None)

### 4. Risk-Free Rate for Merton Share Calculation

**Question**: What should be used as the risk-free rate in the Merton Share formula?

**Decision**: Use the Expected Low Risk Return Rate as the risk-free rate in the Merton Share formula.

**Rationale**:
- The user specified that the discount rate is the weighted return of the low risk allocation
- In the context of this strategy, the low risk allocation represents the "risk-free" or safe portion
- This aligns with the total portfolio approach where low risk allocation serves as the baseline
- The formula becomes: `Merton Share = (Expected High Risk Return - Expected Low Risk Return) / (RRA * Expected High Risk St Dev^2)`

**Alternatives Considered**:
- Treasury yield: Would require additional data source, less aligned with strategy
- Fixed risk-free rate: Not dynamic, doesn't reflect low risk allocation characteristics
- Zero: Unrealistic, low risk assets still have returns

**Implementation Notes**:
- Risk-free rate = Expected Low Risk Return Rate (calculated from low_risk_allocation)
- Merton Share formula: `(expected_high_risk_return - expected_low_risk_return) / (rra * expected_high_risk_stdev ** 2)`

### 5. Present Value Calculation for Future Income

**Question**: How to calculate present value of future income streams with varying amounts over time?

**Decision**: Calculate present value using `numpy_financial.npv()` with an array of all future income cash flows.

**Rationale**:
- Future income varies by interval (raises, different profiles)
- `npf.npv()` efficiently handles a series of cash flows in a single call
- More efficient than calling `pv()` in a loop for each interval
- Simpler code: collect all future income values into an array and pass to `npv()`
- `npv()` automatically handles the discounting for each period

**Alternatives Considered**:
- Single PV calculation with average income: Less accurate, doesn't account for varying amounts
- Annuity formulas: Income is not constant, so annuity formulas don't apply
- Manual discounting loop: More code, unnecessary when `npv()` handles it
- Using `pv()` in a loop: Less efficient than `npv()` for multiple cash flows

**Implementation Notes**:
- Iterate through future intervals from `state.interval_idx + 1` to retirement
- For each future interval, calculate total income:
  - Job income: `controllers.job_income.get_total_income(interval_idx)`
  - Social security: if `controllers.social_security` is not None, `controllers.social_security.calc_payment(future_state)` returns `(user_payment, partner_payment)`, sum both; otherwise treat social security income as 0
  - Pension: if `controllers.pension` is not None, use `controllers.pension.calc_payment(future_state)`; otherwise treat pension income as 0
  - Total income for interval = job_income + social_security_user + social_security_partner + pension
- Collect all future total income values into a list/array: `[income_1, income_2, ..., income_n]`
- Convert annualized discount rate to interval rate:
  - Variable statistics provide annualized yields (e.g., 1.092 for 9.2% annual return)
  - Convert annual yield to interval yield: `interval_yield = annual_yield ** YEARS_PER_INTERVAL`
  - Convert to interval return (rate): `interval_rate = interval_yield - 1`
  - Use `interval_rate` in `npf.npv()` since it expects rate per period
- Calculate PV using: `npf.npv(rate=interval_rate, values=income_array)`
- `npv()` returns the net present value of the cash flow series
- Handle case where income is zero (retired) by returning 0 or passing empty array
- **Note**: For social security and pension calculations, need to create temporary State objects for future intervals to pass to `calc_payment()` methods. These temporary states should have the same user config, appropriate date/interval_idx, and estimated net_worth/inflation values for the future interval.

**Rate Conversion Details**:
- `variable_statistics.csv` contains annualized `AverageYield` values (e.g., 1.092)
- Annual return = `AverageYield - 1` (e.g., 0.092 = 9.2%)
- Interval yield = `interval_yield(AverageYield)` = `AverageYield ** YEARS_PER_INTERVAL`
- Interval rate for NPV = `interval_yield - 1`
- This ensures NPV discounts each interval correctly (quarterly intervals with quarterly rates)

### 6. Default Values for TotalPortfolioStrategyConfig

**Question**: What should be the default values for low_risk_allocation, high_risk_allocation, and RRA?

**Decision**: 
- `low_risk_allocation`: Default to `{"TIPS": 1.0}` (100% TIPS)
- `high_risk_allocation`: Default to `{"US_Stock": 1.0}` (100% US_Stock)
- `RRA`: Default to `2.0`

**Rationale**:
- User explicitly specified these defaults in the requirements
- TIPS (Treasury Inflation-Protected Securities) are appropriate as low-risk default
- US_Stock represents a typical high-risk asset
- RRA of 2.0 is a common moderate risk aversion value in financial literature

**Alternatives Considered**:
- No defaults: Would require users to always specify, less user-friendly
- Different defaults: User specified these exact defaults

**Implementation Notes**:
- Use Pydantic `Field(default_factory=...)` for dict defaults
- Use `Field(default=2.0)` for RRA
- Ensure defaults are validated like user-provided values

### 7. Handling Edge Cases in Allocation Calculation

**Question**: How to handle edge cases like zero/negative savings, zero total portfolio, or division by zero?

**Decision**: Implement defensive checks with appropriate fallbacks:
- Zero/negative savings: Use 0 for savings, calculate based on future income only
- Zero total portfolio: Return low_risk_allocation (most conservative)
- Division by zero in Merton Share: Return low_risk_allocation
- Negative Merton Share: Cap at 0 (no high risk allocation)

**Rationale**:
- Edge cases must be handled gracefully per specification requirements
- Conservative fallbacks (low_risk_allocation) are safer than errors
- Prevents simulation crashes from invalid states

**Alternatives Considered**:
- Raise exceptions: Would crash simulations, not user-friendly
- Return zero allocation: Invalid (doesn't sum to 1.0)
- Return high_risk_allocation: Too aggressive for edge cases

**Implementation Notes**:
- Check for zero/negative savings before calculations
- Check for zero total portfolio before Merton Share calculation
- Check for division by zero in Merton Share denominator
- Cap Merton Share at 0 and 1 (0 = all low risk, 1 = all high risk)
- Ensure final allocation always sums to 1.0

### 8. Avoiding Circular Dependencies with Net Worth-Based Benefit Strategies

**Question**: How to avoid circular dependencies when social security or pension strategies depend on future net worth while total portfolio allocation depends on future income (including those benefits)?

**Decision**: Disallow net-worth-based benefit strategies when using the total portfolio allocation strategy and precompute future benefit/job income using fake `State` objects during `_TotalPortfolioStrategy.__post_init__`.

**Rationale**:
- Net-worth-based benefit triggers (e.g., "NetWorthStrategy") would require knowledge of future net worth to determine benefit start dates, but future net worth itself depends on allocations chosen by the total portfolio strategy.
- This creates a circular dependency between allocation and benefit timing.
- Restricting benefit strategies to age-based (for social security) and age-based or cashout (for pension) breaks the circular dependency while still supporting realistic user scenarios.
- Precomputing future benefit and job income streams once in `__post_init__` avoids recomputation in every `gen_allocation()` call and keeps allocation calculation fast.
- Using fake `State` objects that raise if `state.net_worth` is accessed enforces the invariant that benefit timing must not depend on net worth during precomputation.

**Alternatives Considered**:
- Support net-worth-based benefit strategies by iterating until convergence between allocation and benefit timing:
  - Rejected as overly complex and potentially unstable; convergence is not guaranteed and would be expensive per trial.
- Approximate future net worth with a heuristic for benefit timing:
  - Rejected due to opacity and difficulty reasoning about correctness and user expectations.
- Compute benefits on the fly in `gen_allocation()`:
  - Rejected due to performance concerns (recomputing full income timelines per interval) and more complicated control flow.

**Implementation Notes**:
- Add a validation rule in `app/models/config/user.py`:
  - If `user.portfolio.allocation_strategy.chosen_strategy` is `TotalPortfolioStrategy`:
    - Social security strategy MUST be an age-based strategy (early, mid, or late - corresponding to `_AgeStrategy` class in social_security.py).
    - Pension strategy MUST be an age-based strategy (early, mid, or late - corresponding to `_AgeStrategy` class in pension.py) or cashout strategy (no net-worth-triggered variants).
  - If this constraint is violated, raise `ValueError` during user config validation with a clear message.
- In `_TotalPortfolioStrategy.__post_init__`:
  - Build a list/array of fake `State` instances, one per future interval, with:
    - Correct `interval_idx`, date, inflation, and other non-net-worth fields from user config.
    - `net_worth` access raises `RuntimeError` (use property or descriptor pattern to prevent access).
  - Use these fake states plus the real controllers to:
    - Precompute arrays of future income per interval:
      - `job_income_by_interval[i] = controllers.job_income.get_total_income(future_interval_idx)`
      - `benefit_income_by_interval[i] = sum(controllers.social_security.calc_payment(fake_state)) + controllers.pension.calc_payment(fake_state)`
      - `future_income_by_interval[i] = job_income_by_interval[i] + benefit_income_by_interval[i]` (combined future income = job income + benefit income)
    - Store the resulting arrays as attributes on `_TotalPortfolioStrategy` for reuse in `gen_allocation()`.
  - In `gen_allocation()`:
    - Slice the precomputed `future_income_by_interval` array from `state.interval_idx + 1` onward to form the `values` array for `npf.npv()`.
    - This keeps `gen_allocation()` focused on discounting and interpolation, not on benefit timing logic.

## Technical Dependencies

### New Dependencies
- `numpy-financial`: For present value calculations
  - Installation: `pip install numpy-financial`
  - Usage: `import numpy_financial as npf`

### Existing Dependencies Used
- `numpy`: For array operations and numerical calculations
- `pydantic`: For configuration validation
- Existing economic data structures
- Existing job income controller

## Implementation Constraints

1. **Backward Compatibility**: Must not break existing allocation strategies (flat, net_worth_pivot)
2. **Type Safety**: All new code must have proper type hints
3. **Performance**: Allocation calculation must be efficient (<1ms per interval)
4. **Testing**: Must achieve 95%+ test coverage for financial calculations
5. **Validation**: All allocations must sum to 1.0, all assets must be in ALLOWED_ASSETS

## Open Questions Resolved

All technical questions have been resolved. The implementation approach is clear and follows existing patterns in the codebase.


# Feature Specification: Total Portfolio Allocation Strategy

**Feature Branch**: `002-total-portfolio-allocation`  
**Created**: 2025-12-21  
**Status**: Draft  
**Input**: User description: "Add the ability for the user to define a portfolio configuration for following a total portfolio allocation strategy where allocation is determined by relative risk aversion and total portfolio (current savings + future income)."

## Clarifications

### Session 2025-12-21

- Q: What are the validation bounds for the RRA (Relative Risk Aversion) parameter? → A: Minimal validation: Only require RRA > 0 (no upper bound or warnings)
- Q: Should the Merton Share formula be included in the spec? → A: Yes, include Merton Share formula: (Expected High Risk Return - Expected Low Risk Return) / (RRA × High Risk StDev²)
- Q: Should the interpolation mechanism be included in the spec? → A: Yes, include interpolation mechanism: Merton Share × Total Portfolio determines high-risk amount, then blend allocations proportionally
- Q: How should retirement date be determined for present value calculations? → A: Reference existing job_income_controller logic without specifying details (assume it handles retirement determination)
- Q: How should Merton Share calculation edge cases be handled? → A: Cap Merton Share at [0, 1] range; if division by zero or invalid calculation, return low_risk_allocation (most conservative)
- Q: How should missing asset data in variable_statistics.csv be handled? → A: Raise ValueError during strategy initialization if any asset in high/low risk allocations is missing from variable_statistics.csv
- Q: How should missing or None controllers in Controllers object be handled? → A: If the `controllers` object itself is None, raise ValueError. If social security or pension controllers/strategies are None (no benefits configured), treat income from that source as 0 without error.
- Q: How should discount rate calculation failures be handled? → A: Raise ValueError if discount rate cannot be calculated (caught by initialization validation, but explicit runtime check for safety)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Total Portfolio Allocation Strategy (Priority: P1)

A user wants to configure their portfolio to use a total portfolio allocation strategy that considers both their current savings and future income when determining asset allocation. They provide their relative risk aversion parameter, a high risk allocation, and a low risk allocation. The system calculates the appropriate allocation based on their total portfolio value, interpolating between the high and low risk allocations based on risk aversion.

**Why this priority**: This is the core functionality - enabling users to configure and use the total portfolio allocation strategy is the foundation for all other scenarios.

**Independent Test**: Can be fully tested by providing a user configuration with total portfolio allocation strategy settings (risk aversion, high risk allocation, low risk allocation), then verifying the system accepts the configuration and uses it to calculate allocations. Delivers value by allowing users to implement a sophisticated allocation approach that considers human capital.

**Acceptance Scenarios**:

1. **Given** a user with current savings and future income profiles configured, **When** they select the total portfolio allocation strategy and provide a relative risk aversion value, high risk allocation, and low risk allocation, **Then** the system accepts the configuration and uses it for allocation calculations
2. **Given** a user configuring the total portfolio allocation strategy, **When** they provide a relative risk aversion value, **Then** the system validates the value is positive (RRA > 0)
3. **Given** a user configuring the total portfolio allocation strategy, **When** they provide high risk and low risk allocations, **Then** the system validates that both allocations sum to 1.0 (100%) and contain only allowed assets
4. **Given** a user with no future income (retired), **When** they configure the total portfolio allocation strategy, **Then** the system calculates allocation based on current savings only (total portfolio equals current savings)

---

### User Story 2 - Calculate Allocation Based on Total Portfolio and Risk Aversion (Priority: P1)

A user wants the system to dynamically calculate their asset allocation at each simulation interval by interpolating between their configured high risk and low risk allocations based on their total portfolio value (current savings + present value of future income) and their relative risk aversion parameter. The interpolation uses the Merton Share formula to determine the optimal split between high and low risk assets.

**Why this priority**: This is the core calculation logic - the allocation must be computed correctly by interpolating between high and low risk allocations based on total portfolio and risk aversion for the strategy to work.

**Independent Test**: Can be fully tested by running a simulation with the total portfolio allocation strategy and verifying that allocations are calculated by interpolating between high and low risk allocations using total portfolio (current savings + future income present value) and the risk aversion parameter. Delivers value by providing dynamic allocation that adapts as the user's financial situation changes.

**Acceptance Scenarios**:

1. **Given** a user with total portfolio allocation strategy configured (high risk and low risk allocations), **When** the system calculates allocation at a simulation interval, **Then** the allocation is determined by: (1) calculating Merton Share from expected returns and risk aversion, (2) applying Merton Share to total portfolio to determine high-risk amount, (3) calculating savings high/low risk ratios, and (4) blending high and low risk allocations proportionally
2. **Given** a user with high relative risk aversion, **When** the system calculates allocation, **Then** the allocation is closer to the low risk allocation compared to a user with low risk aversion
3. **Given** a user with low relative risk aversion, **When** the system calculates allocation, **Then** the allocation is closer to the high risk allocation compared to a user with high risk aversion
4. **Given** a user whose future income decreases over time, **When** the system calculates allocation at different intervals, **Then** the allocation adjusts to reflect the changing total portfolio value

---

### User Story 3 - Calculate Present Value of Future Income (Priority: P2)

A user wants the system to accurately calculate the present value of their future income streams (including job income, social security, and pension for both user and partner) to determine their total portfolio value for allocation calculations.

**Why this priority**: Accurate present value calculation is essential for correct total portfolio valuation, which directly impacts allocation decisions.

**Independent Test**: Can be fully tested by providing income profiles and verifying the system calculates the present value of future income (job income, social security, pension) using appropriate discount rates. Delivers value by ensuring total portfolio includes both financial capital and human capital.

**Acceptance Scenarios**:

1. **Given** a user with income profiles configured for user and optional partner, **When** the system calculates present value of future income, **Then** it includes all future income streams: job income, social security (user and partner), and pension from both user and partner
2. **Given** a user with income that varies over time (raises, different profiles), **When** the system calculates present value of future income, **Then** it accounts for the varying income amounts across different time periods
3. **Given** a user with income that ends at retirement, **When** the system calculates present value of future income, **Then** it only includes income up to the retirement date (job income ends, but social security and pension may continue)
4. **Given** a user at a specific simulation interval, **When** the system calculates present value of future income, **Then** it discounts future income from that interval forward using appropriate discount rates
5. **Given** a user with social security and pension benefits, **When** the system calculates present value of future income, **Then** it includes social security and pension payments in the future income streams

---

### Edge Cases

- **No future income (retired)**: If user has no future income streams, total portfolio equals current savings only. Allocation is calculated based on current savings and risk aversion.
- **Zero or negative current savings**: If current savings is zero or negative, total portfolio equals present value of future income only. System handles this case without errors.
- **Zero or negative total portfolio**: If total portfolio (current savings + future income present value) is zero or negative, system returns low_risk_allocation (most conservative).
- **Merton Share calculation edge cases**: If Merton Share calculation results in division by zero (e.g., zero standard deviation) or produces invalid values, system returns low_risk_allocation. Merton Share is capped at [0, 1] range (negative values become 0, values >1 become 1).
- **Risk aversion at boundaries**: If relative risk aversion is at very low values (close to 0) or very high values, system calculates allocation correctly without errors. Only validation is RRA > 0.
- **Income profiles with gaps**: If income profiles have gaps (periods with no income), present value calculation accounts for these gaps correctly.
- **Very high future income relative to savings**: If present value of future income is much larger than current savings, allocation calculation handles this correctly.
- **Very high savings relative to future income**: If current savings is much larger than present value of future income, allocation calculation handles this correctly.
- **Missing asset data**: If any asset in high or low risk allocations is missing from variable_statistics.csv, strategy initialization raises ValueError with clear error message identifying the missing asset(s).
- **Missing controllers**: If controllers parameter is None, system raises ValueError with clear error message. If social security or pension controllers/strategies are None (no benefits configured), income from that source is treated as 0 and included as such in calculations (no error).
- **Discount rate calculation failure**: If discount rate cannot be calculated (e.g., no valid assets in low risk allocation or missing data), system raises ValueError. This should be caught during strategy initialization (FR-008), but explicit runtime check provides safety.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to configure a total portfolio allocation strategy in their portfolio configuration
- **FR-002**: System MUST accept a relative risk aversion parameter as part of the total portfolio allocation strategy configuration
- **FR-003**: System MUST validate that relative risk aversion parameter is positive (RRA > 0). No upper bound validation or warnings are required.
- **FR-004**: System MUST accept a high risk allocation as part of the total portfolio allocation strategy configuration
- **FR-005**: System MUST accept a low risk allocation as part of the total portfolio allocation strategy configuration
- **FR-006**: System MUST validate that high risk allocation sums to 1.0 (100%) and contains only allowed assets
- **FR-007**: System MUST validate that low risk allocation sums to 1.0 (100%) and contains only allowed assets
- **FR-008**: System MUST validate during strategy initialization that all assets in high risk and low risk allocations have corresponding entries in variable_statistics.csv, raising ValueError if any asset is missing
- **FR-009**: System MUST calculate total portfolio value as the sum of current savings (net worth) and present value of future income at each simulation interval
- **FR-010**: System MUST calculate present value of future income by discounting all future income streams (job income, social security, and pension for both user and partner) from the current simulation interval forward
- **FR-010a**: System MUST raise ValueError if controllers parameter is None when calculating future income. If social security or pension controllers/strategies are None (no benefits configured), system MUST treat income from that source as 0 without raising an error.
- **FR-011**: System MUST calculate discount rate as the weighted average return of the assets in the low risk allocation, using expected asset returns from economic data. If discount rate cannot be calculated (e.g., no valid assets or missing data), system MUST raise ValueError
- **FR-012**: System MUST calculate asset allocation at each simulation interval by interpolating between high risk allocation and low risk allocation based on total portfolio value and relative risk aversion parameter using the Merton Share formula: Merton Share = (Expected High Risk Return - Expected Low Risk Return) / (RRA × Expected High Risk StDev²)
- **FR-012a**: System MUST apply Merton Share to determine allocation as follows: (1) Calculate Merton Share from formula, (2) Cap Merton Share at [0, 1] range (if negative, use 0; if >1, use 1), (3) If division by zero occurs in Merton Share calculation, return low_risk_allocation, (4) Calculate Total Portfolio High Risk Amount = Merton Share × Total Portfolio, (5) Calculate Savings High Risk Ratio = min(1.0, Total Portfolio High Risk Amount / Savings), (6) Calculate Savings Low Risk Ratio = 1.0 - Savings High Risk Ratio, (7) Return final allocation = (high_risk_allocation × Savings High Risk Ratio) + (low_risk_allocation × Savings Low Risk Ratio)
- **FR-013**: System MUST ensure that higher relative risk aversion results in allocation favoring the low risk allocation compared to lower risk aversion
- **FR-014**: System MUST ensure that lower relative risk aversion results in allocation favoring the high risk allocation compared to higher risk aversion
- **FR-015**: System MUST handle cases where user has no future income (retired) by calculating total portfolio as current savings only
- **FR-016**: System MUST handle cases where current savings is zero or negative by calculating total portfolio as present value of future income only
- **FR-017**: System MUST ensure calculated allocation ratios sum to 1.0 (100%) across all assets at each interval
- **FR-018**: System MUST include all future income sources when calculating present value of future income: job income (user and partner), social security (user and partner), and pension
- **FR-019**: System MUST account for varying income amounts over time (raises, different income profiles) when calculating present value
- **FR-020**: System MUST calculate allocation dynamically at each simulation interval as total portfolio value changes
- **FR-021**: System MUST handle edge cases (zero/negative savings, zero/negative total portfolio) without errors
- **FR-022**: System MUST validate that when TotalPortfolioStrategy is chosen, social security uses an age-based strategy (early, mid, or late) and pension uses an age-based strategy (early, mid, or late) or cashout strategy, raising ValueError with clear message if incompatible strategies are configured

### Key Entities *(include if feature involves data)*

- **Total Portfolio Allocation Strategy Configuration**: Represents user's configuration for the total portfolio allocation strategy with attributes: relative risk aversion parameter (positive value, RRA > 0), high risk allocation (dict of asset to ratio, sums to 1.0), and low risk allocation (dict of asset to ratio, sums to 1.0)
- **High Risk Allocation**: Represents the asset allocation that will be favored when risk aversion is low, defined as a dictionary mapping asset names to allocation ratios that sum to 1.0
- **Low Risk Allocation**: Represents the asset allocation that will be favored when risk aversion is high, defined as a dictionary mapping asset names to allocation ratios that sum to 1.0. Also used to calculate the discount rate for present value calculations
- **Total Portfolio Value**: Represents the combined value of current savings (net worth) and present value of future income streams, calculated at each simulation interval
- **Present Value of Future Income**: Represents the discounted value of all future income streams (job income, social security, and pension for both user and partner) from the current simulation interval forward, calculated using discount rate derived from weighted average return of low risk allocation
- **Merton Share**: Represents the optimal proportion of total portfolio to allocate to high-risk assets, calculated as: (Expected High Risk Return - Expected Low Risk Return) / (RRA × Expected High Risk StDev²). This is applied to determine the interpolation between high and low risk allocations: Total Portfolio High Risk Amount = Merton Share × Total Portfolio, then Savings High Risk Ratio = min(1.0, Total Portfolio High Risk Amount / Savings), and final allocation blends high and low risk allocations proportionally.
- **Relative Risk Aversion**: Represents the user's risk preference parameter that determines how allocation interpolates between high risk and low risk allocations via the Merton Share formula, where higher values favor the low risk allocation

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System calculates asset allocation correctly based on total portfolio (current savings + present value of future income) and relative risk aversion at each simulation interval
- **SC-002**: Allocation calculations reflect risk aversion parameter: higher risk aversion results in allocations closer to the low risk allocation, lower risk aversion results in allocations closer to the high risk allocation
- **SC-003**: Present value of future income calculations accurately account for all income streams (job income, social security, and pension for both user and partner) and discount them using the weighted average return of the low risk allocation from the current interval forward
- **SC-004**: System handles edge cases gracefully (no future income, zero/negative savings, zero/negative total portfolio) without errors or invalid allocations
- **SC-005**: Allocation ratios sum to 1.0 (100%) across all assets at every simulation interval
- **SC-006**: Allocation dynamically adjusts as total portfolio value changes over time (e.g., as future income decreases or savings grow)

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
- **PR-002**: Simulation operations MUST meet performance targets (specify: e.g., <100ms per trial)
- **PR-003**: Memory usage MUST be bounded and monitored
- **PR-004**: Performance-critical code paths MUST be profiled before merge
- **PR-005**: Present value calculations MUST complete efficiently without significantly impacting simulation performance

## Assumptions

- Users have already configured their income profiles (user and optional partner), social security settings, and pension settings in the user configuration file. Social security and pension controllers/strategies MAY be None (no benefits configured); in those cases, income from that source is treated as 0 in the total portfolio calculations.
- Relative risk aversion parameter follows standard financial theory where higher values indicate greater risk aversion (preference for safer assets)
- Total portfolio allocation strategy is based on modern portfolio theory principles where allocation depends on total wealth (financial capital + human capital) and risk preferences
- Users define high risk and low risk allocations that represent the bounds of their allocation strategy, and the system interpolates between them based on risk aversion and total portfolio value
- Discount rate for present value calculations is derived from the weighted average return of assets in the low risk allocation, using expected returns from economic data
- Expected asset returns are available from economic data structures for calculating the discount rate
- Allocation interpolation between high and low risk allocations produces valid asset allocation ratios that sum to 1.0 and are within acceptable bounds (non-negative, reasonable values)
- Future income streams are known or can be projected from income profiles (no uncertainty in income amounts, only in discounting)
- The strategy integrates with existing allocation strategy framework (similar to flat and net_worth_pivot strategies)
- Asset lookup and economic data structures remain compatible with the new strategy

## Dependencies

- Existing income profile data structures and calculation logic (user and partner income)
- Existing social security controller for calculating social security payments
- Existing pension controller for calculating pension payments
- Existing portfolio configuration structure and allocation strategy framework
- Existing State object that contains current net worth and simulation interval information
- Existing asset lookup and economic data structures for allocation calculations and expected asset returns
- Existing allocation strategy pattern (flat, net_worth_pivot) for integration consistency
- Economic data that provides expected returns for each asset to calculate discount rate from low risk allocation

## Out of Scope

- Dynamic risk aversion that changes over time (risk aversion is assumed constant for the strategy)
- Uncertainty in future income amounts (income is treated as certain, only discounted)
- Integration with external portfolio optimization tools or APIs
- Recommendations for optimal risk aversion values (user must provide their own risk aversion parameter)
- Handling of income uncertainty or stochastic income streams
- Tax optimization considerations in allocation decisions
- Rebalancing frequency or transaction cost considerations beyond allocation calculation

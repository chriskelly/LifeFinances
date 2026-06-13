# Feature Specification: Spending Controller

**Feature Branch**: `001-spending-controller`  
**Created**: December 31, 2025  
**Status**: Draft  
**Input**: User description: "Adjust spending to be modeled in a Controller similar to allocation. For now, the only strategy will be `inflation_following`, which should use the current Spending Profiles as a configuration input."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Inflation-Following Spending (Priority: P1)

A user defines spending profiles with different yearly amounts over different time periods. The simulation calculates spending for each time interval by applying inflation to the base yearly amount from the active spending profile.

**Why this priority**: This is the core functionality that replaces the existing spending calculation with the Controller pattern. Without this, the simulation cannot calculate spending amounts, making it a critical P1 feature.

**Independent Test**: Can be fully tested by configuring spending profiles with different yearly amounts and end dates, running a simulation, and verifying that spending amounts are calculated correctly for each interval with inflation applied. Delivers a working simulation with predictable spending behavior.

**Acceptance Scenarios**:

1. **Given** a user has three spending profiles (60K until 2035.25, 70K until 2040.25, then 55K indefinitely) and current inflation is 1.05, **When** the simulation calculates spending for a date in 2030, **Then** the spending amount should be -60K/4 * 1.05 (quarterly amount with inflation applied)

2. **Given** a user has multiple spending profiles with different end dates, **When** the simulation transitions from one profile period to another, **Then** the spending amount should change to reflect the new profile's yearly amount while still applying inflation

3. **Given** a user has reached the final spending profile (with no end_date), **When** the simulation continues to any future date, **Then** the spending should continue using that final profile's yearly amount with inflation applied

---

### Edge Cases

All edge cases have been addressed through clarifications and are now resolved in the functional requirements.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a spending Controller class that follows the same pattern as the allocation Controller (with strategy selection and a main calculation method)

- **FR-002**: System MUST implement an `inflation_following` strategy that calculates spending based on spending profiles with inflation adjustment

- **FR-003**: System MUST accept spending profiles as configuration input, where each profile specifies a yearly_amount and optional end_date

- **FR-004**: System MUST validate that spending profiles are in chronological order (each profile's end_date must be greater than the previous profile's end_date) and MUST raise a validation error if profiles are not chronologically ordered

- **FR-005**: System MUST require that all profiles except the last one have an end_date specified

- **FR-006**: System MUST require that the last spending profile has no end_date (indicating it continues indefinitely), enforced during validation to ensure all future dates have a valid profile

- **FR-007**: System MUST select the appropriate spending profile based on the current simulation date, where a profile remains active while date <= end_date (transition to next profile occurs when date > end_date)

- **FR-008**: System MUST calculate spending amount by dividing yearly_amount by intervals per year and multiplying by current inflation (zero or negative inflation values are valid and applied as-is)

- **FR-009**: System MUST return spending as a negative value (representing money going out)

- **FR-010**: System MUST integrate the spending Controller into the Controllers dataclass alongside other controllers

- **FR-011**: System MUST update StateChangeComponents to use the spending Controller instead of the existing _calc_spending static method

- **FR-012**: Configuration MUST support a root-level `spending_strategy` field with nested strategy options (starting with `inflation_following`)

- **FR-013**: The `inflation_following` strategy configuration MUST inherit from StrategyConfig (providing the `chosen` boolean field) and include a `profiles` list as an additional attribute

- **FR-014**: System MUST raise an error if no spending profile matches the current date (indicating misconfiguration)

- **FR-015**: System MUST maintain all existing spending profile validation logic (ordering, end_date requirements) and MUST raise a validation error during controller initialization if the profile list is empty or malformed

### Key Entities *(include if feature involves data)*

- **Spending Controller**: Manages spending strategy selection and delegates spending calculation to the active strategy. Initialized with user configuration and provides a method to calculate spending for a given state.

- **Inflation Following Strategy**: Implements spending calculation by selecting the appropriate profile based on date and applying inflation adjustment. Contains the spending profiles list and logic for profile selection.

- **Spending Profile**: Represents a time period with a specific yearly spending amount. Contains yearly_amount (base spending per year) and optional end_date (when this profile stops applying).

- **Spending Strategy Configuration**: Configuration object that specifies which spending strategy is chosen and contains strategy-specific settings (e.g., profiles for inflation_following strategy).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Simulations calculate spending amounts identically before and after the Controller refactoring (maintaining calculation accuracy)

- **SC-002**: Spending calculation execution time remains under 1 millisecond per interval (no performance degradation)

- **SC-003**: Configuration validation catches 100% of invalid profile configurations (missing end_dates, incorrect ordering, empty lists)

- **SC-004**: The spending Controller follows the same architectural pattern as the allocation Controller (consistent codebase structure and maintainability)

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
- **PR-002**: Spending calculation operations MUST complete in under 1 millisecond per interval
- **PR-003**: Memory usage MUST be bounded and monitored
- **PR-004**: Performance-critical code paths MUST be profiled before merge

## Assumptions

1. **Strategy Pattern**: We assume the allocation Controller pattern is well-established and proven, so we follow its structure (Controller class with strategy selection, abstract strategy base class, concrete strategy implementations).

2. **Quarterly Intervals**: We assume the simulation uses quarterly intervals (4 intervals per year) based on the existing code's use of `INTERVALS_PER_YEAR`.

3. **Inflation Application**: We assume inflation is already calculated and available in the State object, and we apply it as a multiplicative factor to the base spending amount.

4. **Single Strategy**: We assume that starting with only `inflation_following` strategy is sufficient, with the understanding that the architecture should support adding more strategies in the future (e.g., dynamic spending rules, guardrails).

5. **Negative Spending Values**: We assume spending should be returned as negative values to represent outflow, consistent with the existing implementation.

6. **Date Comparison**: We assume that when the current date equals a profile's end_date, we should use the current profile (not transition to the next one yet), using >= comparison logic from the existing code.

## Clarifications

### Session 2026-01-01

- Q: When simulation date equals a profile's end_date, which profile should be active? → A: Current profile remains active (date <= end_date) - transition happens after end_date
- Q: Should the system allow zero or negative inflation values in calculations? → A: Allow zero/negative inflation (apply as-is) - spending adjusted proportionally
- Q: How should the controller respond when initialized with an empty or invalid profile list? → A: Raise validation error during initialization - fail fast at startup
- Q: If the last profile has an end_date (violating FR-006), what happens when simulation date exceeds it? → A: Validation prevents this scenario (caught at initialization per FR-006)
- Q: How should the system respond when profile end_dates are not in ascending order? → A: Raise validation error (reject configuration) - enforce chronological order

## Out of Scope

- Alternative spending strategies (e.g., percentage-based, guardrails, dynamic withdrawal rules) - only `inflation_following` will be implemented
- Changes to the spending profile data structure or validation rules beyond what's necessary for the Controller pattern
- UI changes for spending configuration (this is a backend refactoring)
- Backwards compatibility with old configuration format (users must update to new format)
- Changes to how inflation is calculated or sourced
- Optimization of spending calculation performance (current performance is acceptable)

**Note on Terminology**: The old configuration format used `inflation_only` as the strategy name. This has been renamed to `inflation_following` in the new configuration structure for semantic clarity and consistency with the controller pattern. All references in this specification use the new canonical term `inflation_following`.

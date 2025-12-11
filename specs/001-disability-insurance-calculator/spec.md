# Feature Specification: Disability Insurance Calculator Script

**Feature Branch**: `001-disability-insurance-calculator`  
**Created**: 2025-12-10  
**Status**: Draft  
**Input**: User description: "Build a script that enables a user to calculate the amount of disability insurance they need. The script should use existing values for future income assumptions. It also needs to be able to account for secondary affects of losing job income, such as reduced social security and pension income. The user should be able to input their (and their partner's) existing disability insurance coverage (such as from their job) in a format that matches the typical format given by employers (such as % of income covered for x years). The output should be the total amount of income that would need to be replaced if the user or partner (both cases) cannot work any longer, the income that will be replaced by the existing coverage (taking into account taxes typically applied on workplace provided benefits), and the remaining coverage gap in the format typically used by disability insurance policies (% of income for x years). You can ignore constitutional requirements for testing since this is not going to be part of the simulation application"

## Clarifications

### Session 2025-12-10

- Q: What format should the script output use for presenting results? → A: Structured text output showing: (1) Total income replacement needed, (2) Existing coverage replacement (after taxes), (3) Remaining coverage gap (% of income for x years), plus explanatory notes
- Q: How should users provide existing disability insurance coverage input? → A: Read from user configuration file (same file containing income profiles)
- Q: How should coverage gap be calculated when coverage duration extends beyond working years? → A: Calculate gap to replace total future post-tax income user would have earned until Benefit cutoff age (configurable in script, default value is 65). Total replacement needs = (Baseline post-tax income - Disability post-tax income), where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes lost post-tax job income + reduced post-tax Social Security + reduced post-tax pension (including post-Benefit cutoff age reductions). Coverage gap = Total replacement needs - Existing coverage replacement. Benefit percentage = (Coverage gap / Years until Benefit cutoff age) / Current annual income. Size benefit to make up for missing future income.
- Q: How should coverage percentage over 100% be handled in gap calculation? → A: Cap existing coverage replacement at 100% of income when calculating gap (excess coverage doesn't reduce gap below zero)
- Q: How should "current annual income" be determined for benefit percentage calculation when income varies over time? → A: Use first income profile with income over $0 (user may currently be on sabbatical with $0 income)
- Q: Should coverage gap include income reductions after Benefit cutoff age (such as reduced Social Security)? → A: Yes, coverage gap MUST include post-Benefit cutoff age income reductions (e.g., if Social Security expected $500k but reduced to $400k due to disability, the $100k reduction is included in total income to be replaced, which feeds into the income replacement rate output)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Calculate Disability Insurance Needs for User (Priority: P1)

A user wants to determine how much additional disability insurance they need beyond their existing employer-provided coverage. They provide their existing coverage details and want to see the total income replacement needed, what their existing coverage provides, and the gap that needs to be filled.

**Why this priority**: This is the core functionality - calculating needs for a single person is the foundation for all other scenarios.

**Independent Test**: Can be fully tested by providing user income profile and existing coverage, then verifying the script calculates total replacement needs, existing coverage replacement (after taxes), and remaining gap. Delivers value by helping users understand their coverage adequacy.

**Acceptance Scenarios**:

1. **Given** a user with income profiles configured, **When** the script is run with user's existing disability coverage (e.g., "60% of income for 5 years"), **Then** the script calculates total income replacement needed, existing coverage replacement amount (accounting for taxes), and remaining coverage gap
2. **Given** a user with no existing disability coverage (0% coverage), **When** the script is run, **Then** the script calculates total income replacement needed and shows 100% of income needs to be covered
3. **Given** a user whose existing coverage exceeds their needs, **When** the script is run, **Then** the script indicates no additional coverage is needed

---

### User Story 2 - Account for Secondary Effects on Social Security and Pension (Priority: P1)

A user wants to understand the full financial impact of disability, including how losing job income will reduce their future Social Security and pension benefits, not just the immediate income loss.

**Why this priority**: Secondary effects significantly impact long-term financial security and are essential for accurate coverage calculations.

**Independent Test**: Can be fully tested by comparing Social Security and pension calculations with and without job income, verifying the script accounts for reduced future benefits. Delivers value by providing comprehensive financial impact analysis.

**Acceptance Scenarios**:

1. **Given** a user with job income that contributes to Social Security eligibility, **When** disability eliminates job income, **Then** the script calculates reduced Social Security benefits (including post-Benefit cutoff age income reductions) and includes this reduction in total income replacement needs
2. **Given** a user with a pension that depends on years worked and final compensation, **When** disability stops work early, **Then** the script calculates reduced pension benefits and includes this reduction in total income replacement needs
3. **Given** a user who is already retired (no future income), **When** the script is run, **Then** the script exits with a clear message explaining that no disability insurance is needed

---

### User Story 3 - Calculate Disability Insurance Needs for Partner (Priority: P2)

A user wants to calculate disability insurance needs for their partner, accounting for how the partner's disability would affect household income and future benefits.

**Why this priority**: Many households have two income earners, and both need protection. This extends the core functionality to cover partner scenarios.

**Independent Test**: Can be fully tested by providing partner income profile and existing coverage, then verifying the script calculates partner's total replacement needs, existing coverage replacement, and remaining gap. Delivers value by enabling comprehensive household financial protection planning.

**Acceptance Scenarios**:

1. **Given** a user with a partner who has income profiles configured, **When** the script is run with partner's existing disability coverage, **Then** the script calculates partner's total income replacement needed, existing coverage replacement amount, and remaining coverage gap
2. **Given** a user with a partner who has no existing disability coverage (0% coverage), **When** the script is run for the partner, **Then** the script calculates partner's total income replacement needed and shows 100% of income needs to be covered
3. **Given** a user with no income profiles but a partner with income profiles, **When** the script is run, **Then** the script focuses only on calculating partner's disability insurance needs
4. **Given** a user with no income profiles and a partner with no income profiles, **When** the script is run, **Then** the script exits with a clear message explaining that no disability insurance is needed
5. **Given** a user with a partner whose disability would reduce household Social Security benefits, **When** the script is run for the partner, **Then** the script includes reduced Social Security benefits in the partner's total replacement needs

---

### User Story 4 - Handle Tax Implications of Workplace Disability Benefits (Priority: P2)

A user wants accurate calculations that account for the fact that employer-provided disability insurance benefits are typically taxable, reducing the net benefit amount compared to the gross coverage percentage.

**Why this priority**: Tax treatment significantly affects the actual income replacement provided by existing coverage, making accurate gap calculations essential.

**Independent Test**: Can be fully tested by providing existing coverage and verifying the script applies appropriate tax rates to calculate net benefit amount. Delivers value by ensuring users understand the true value of their existing coverage.

**Acceptance Scenarios**:

1. **Given** a user with employer-provided disability coverage (e.g., "60% of income"), **When** the script calculates existing coverage replacement, **Then** the script applies income tax rates to determine the net after-tax benefit amount
2. **Given** a user with employer-provided coverage where coverage percentage exceeds 100%, **When** the script calculates existing coverage replacement, **Then** the script handles the excess coverage percentage without errors
3. **Given** a user with employer-provided coverage where coverage duration extends beyond expected working years, **When** the script calculates existing coverage replacement, **Then** the script applies coverage for the full duration period (up to Benefit cutoff age if applicable)

---

### Edge Cases

- **No user income profiles**: If user has no income profiles configured, the script focuses only on the partner's disability insurance needs. If user has no income profiles but partner does, calculate only for partner.
- **Neither user nor partner have income profiles**: If neither user nor partner have income profiles configured, the script exits with a clear message explaining that no disability insurance is needed in this case (no future income to protect).
- **Already retired**: If user and/or partner are already retired (zero future income), the script exits with a clear message explaining that no disability insurance is needed in this case.
- **Coverage percentage exceeds 100%**: Existing coverage percentage MAY exceed 100% of income in input. The script MUST handle this case without errors. For gap calculation, existing coverage replacement is capped at 100% of income (excess coverage above 100% is ignored, as disability insurance typically doesn't cover more than 100% of pre-disability income).
- **Coverage duration extends beyond working years**: Long-term disability (LTD) insurance typically covers until Benefit cutoff age (configurable in script, default value is 65). Coverage gap calculation MUST ensure total future post-tax income (including post-Benefit cutoff age income reductions) is protected, regardless of planned early retirement. Total replacement needs = (Baseline post-tax income - Disability post-tax income), where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes: (1) Post-tax income until Benefit cutoff age, (2) Post-Benefit cutoff age income reductions (e.g., if Social Security expected $500k but reduced to $400k, include $100k reduction). Coverage gap = Total replacement needs - Existing coverage replacement. Benefit percentage is calculated as: (Coverage gap / Years until Benefit cutoff age) / Current annual income. Coverage periods do NOT need to align with income profile intervals.
- **Social Security and pension data availability**: Script assumes Social Security and pension calculation data will be available. No special handling needed for missing data scenarios.
- **Tax calculation without state information**: Tax calculation logic handles cases where state information is not provided. Script assumes tax calculation will handle missing state information appropriately.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Script MUST accept user configuration containing income profiles for user and optional partner
- **FR-002**: Script MUST read existing employer-provided disability insurance coverage for user from user configuration file in format: percentage of income covered and duration in years
- **FR-003**: Script MUST read existing employer-provided disability insurance coverage for partner (if partner exists) from user configuration file in format: percentage of income covered and duration in years
- **FR-004**: Script MUST assume all existing coverage is employer-provided (taxable)
- **FR-004a**: Script MUST allow Benefit cutoff age to be configured in the script (default value is 65, but user must be able to set a different Benefit cutoff age). Benefit cutoff age is used for all calculations involving coverage duration and income replacement needs.
- **FR-005**: Script MUST calculate total income replacement needed for user if user becomes disabled, using post-tax income values. Total replacement needs = (Baseline post-tax income - Disability post-tax income), where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes:
  - Lost post-tax job income for remaining working years until Benefit cutoff age (configurable in script, default value is 65)
  - Reduced post-tax Social Security benefits due to lost earnings history (including post-Benefit cutoff age income reductions, e.g., if expected $500k but reduced to $400k, include $100k reduction)
  - Reduced post-tax pension benefits due to fewer years worked and/or lower final compensation (including post-Benefit cutoff age income reductions)
  - Post-Benefit cutoff age income reductions (e.g., reduced Social Security benefits after Benefit cutoff age) must be included in total income to be replaced
- **FR-006**: Script MUST calculate total income replacement needed for partner if partner becomes disabled, using the same calculation method as FR-005 but applied to partner's income profiles and benefits. Total replacement needs = (Baseline post-tax income - Disability post-tax income), where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes:
  - Lost post-tax partner job income for remaining working years until Benefit cutoff age (configurable in script, default value is 65)
  - Reduced post-tax partner Social Security benefits due to lost earnings history (including post-Benefit cutoff age income reductions)
  - Reduced post-tax partner pension benefits due to fewer years worked and/or lower final compensation (including post-Benefit cutoff age income reductions)
  - Post-Benefit cutoff age income reductions must be included in total income to be replaced
- **FR-007**: Script MUST calculate existing coverage replacement amount by:
  - Applying coverage percentage to income for each year within coverage duration
  - Capping coverage percentage at 100% of income (excess coverage above 100% is ignored for gap calculation)
  - Applying income tax rates to employer-provided benefits using the average tax rate from the baseline scenario for the covered intervals. The average tax rate is calculated as: (total income taxes + total Medicare taxes) / total income for the coverage period. All coverage is employer-provided and taxable as ordinary income.
- **FR-008**: Script MUST calculate remaining coverage gap to ensure total future post-tax income (including post-Benefit cutoff age income reductions) is protected. Total replacement needs is calculated as the difference between baseline and disability post-tax income, where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes: (1) Lost post-tax job income until Benefit cutoff age, (2) Reduced post-tax Social Security benefits (lifetime, including post-Benefit cutoff age reductions), and (3) Reduced post-tax pension benefits (lifetime, including post-Benefit cutoff age reductions). For example, if Social Security expected $500k but reduced to $400k, include the $100k reduction in the sum. Coverage gap = Total replacement needs - Existing coverage replacement. Gap calculation formula: Benefit percentage = (Coverage gap / Years until Benefit cutoff age) / Current annual income. Current annual income is determined as the first income profile with income over $0 (user may be on sabbatical with $0 current income). Size benefit to make up for missing future income after accounting for existing coverage replacement (capped at 100% of income). Gap cannot be negative (minimum 0%).
- **FR-009**: Script MUST output structured text results showing: (1) Total income replacement needed, (2) Existing coverage replacement amount (after taxes), (3) Remaining coverage gap in standard disability insurance format (percentage of income for duration in years), plus explanatory notes
- **FR-010**: Script MUST use existing income profile data and disability coverage data from user configuration file without requiring re-entry
- **FR-011**: Script MUST leverage existing Social Security calculation logic (via SimulationEngine) to determine impact of lost job income on future benefits. The script MUST verify that baseline and disability scenarios properly reflect Social Security benefit differences when job income is zeroed out.
- **FR-012**: Script MUST leverage existing pension calculation logic (via SimulationEngine) to determine impact of lost job income on future benefits. The script MUST verify that baseline and disability scenarios properly reflect pension benefit differences when job income is zeroed out.
- **FR-013**: Script MUST handle cases where user or partner has no existing disability coverage (treat as 0% coverage)
- **FR-014**: Script MUST handle cases where existing coverage exceeds replacement needs (indicating no additional coverage needed)
- **FR-015**: Script MUST output results separately for user disability scenario and partner disability scenario
- **FR-016**: Script MUST handle cases where user has no income profiles by focusing only on partner's disability insurance needs
- **FR-017**: Script MUST exit with a clear message if neither user nor partner have income profiles configured, explaining that no disability insurance is needed
- **FR-018**: Script MUST exit with a clear message if user and/or partner are already retired (zero future income), explaining that no disability insurance is needed
- **FR-019**: Script MUST allow coverage percentage to exceed 100% in input without errors, but MUST cap existing coverage replacement at 100% of income for gap calculation purposes
- **FR-020**: Script MUST calculate coverage needs until Benefit cutoff age (configurable in script, default value is 65), regardless of planned early retirement. Coverage gap is sized to replace total future income that would have been earned until Benefit cutoff age, including post-Benefit cutoff age income reductions as specified in FR-008 (e.g., reduced Social Security benefits after Benefit cutoff age).

### Key Entities *(include if feature involves data)*

- **Disability Coverage**: Represents existing employer-provided disability insurance coverage with attributes: coverage percentage (may exceed 100%), duration in years (may extend beyond working years), and person covered (user or partner). All coverage is employer-provided and taxable.
- **Income Replacement Needs**: Represents total post-tax income that needs to be replaced, calculated as (Baseline post-tax income - Disability post-tax income), where post-tax income = (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes). This includes: lost post-tax job income until Benefit cutoff age, reduced post-tax Social Security benefits (including post-Benefit cutoff age reductions), and reduced post-tax pension benefits (including post-Benefit cutoff age reductions). Post-Benefit cutoff age income reductions (e.g., if Social Security expected $500k but reduced to $400k, the $100k reduction) are included in total income to be replaced, which feeds into the income replacement rate output.
- **Existing Coverage Replacement**: Represents the net after-tax income replacement provided by existing disability coverage, calculated per interval over coverage duration
- **Coverage Gap**: Represents the difference between total replacement needs and existing coverage replacement, expressed as percentage of income and duration needed

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a disability insurance needs calculation in under 2 minutes from start to finish
- **SC-002**: Script produces accurate income replacement calculations that account for all income sources (job until Benefit cutoff age, Social Security including post-Benefit cutoff age income reductions, pension including post-Benefit cutoff age income reductions) for both user and partner scenarios
- **SC-003**: Script correctly applies tax treatment to employer-provided benefits, calculating net after-tax replacement amounts
- **SC-004**: Script outputs structured text results including total replacement needs, existing coverage replacement (after taxes), and remaining coverage gap in standard insurance industry format (% of income for x years) that users can directly use when purchasing policies
- **SC-005**: Script handles edge cases gracefully (no income, no coverage, coverage exceeds needs) without errors or misleading outputs
- **SC-006**: Secondary effect calculations (reduced Social Security and pension, including post-Benefit cutoff age income reductions) reflect realistic impact of lost job income on future benefits. Post-Benefit cutoff age income reductions (e.g., reduced Social Security) are included in total income to be replaced.

### Testing Requirements *(constitution-aligned)*

**This feature is a standalone script/utility that is NOT used as input for the simulation application (simulator or Flask app). Per constitution Testing Standards, standalone scripts that do not feed data or logic into the main application MAY be exempted from testing requirements.**

**Testing exemption applies**: This script is a standalone analysis tool that:
- Does not integrate into the simulator or Flask application
- Is not used as input for application functionality
- Is used independently for one-off calculations
- Does not feed data or logic into the main application

**Testing requirements**: None - exempted per constitution Testing Standards exception for standalone scripts/notebooks.

### Performance Requirements *(constitution-aligned)*

**This feature is a standalone script/utility exempted from constitutional performance requirements.**

**Performance requirements**: None - exempted as standalone script not part of the application.

## Assumptions

- Users have already configured their income profiles, Social Security settings, pension settings, and existing disability insurance coverage in the user configuration file
- All existing disability insurance coverage is employer-provided and taxable as ordinary income at the user's marginal tax rate
- Disability is assumed to occur immediately and last until Benefit cutoff age (configurable in script, default value is 65)
- Long-term disability insurance typically covers until Benefit cutoff age (configurable in script, default value is 65), regardless of planned early retirement
- Benefit cutoff age is configurable in the script (default value is 65, but can be set to a different age)
- Coverage gap calculation seeks to replace total future income including post-Benefit cutoff age income reductions (e.g., reduced Social Security benefits after Benefit cutoff age), not just income until Benefit cutoff age. See FR-008 for detailed calculation formula.
- Current annual income for benefit percentage calculation is determined as the first income profile with income over $0 (accounts for users currently on sabbatical with $0 income)
- Coverage percentage applies to gross income before taxes and may exceed 100% in input (though uncommon). For gap calculation, existing coverage is capped at 100% of income (see FR-007, FR-019).
- **Code organization**: The script follows DRY (Don't Repeat Yourself) principles by using helper functions for repeated calculations that are used consistently across baseline, disability, and partner disability scenarios.
- Coverage periods do not need to align with income profile intervals
- Social Security and pension calculation data will be available (no missing data scenarios to handle)
- Tax calculation logic handles cases where state information is not provided

## Dependencies

- Existing income profile data structures and calculation logic
- Existing Social Security calculation logic and controllers
- Existing pension calculation logic and controllers
- Existing tax calculation logic for determining tax rates on disability benefits
- User configuration structure containing income profiles, Social Security settings, pension settings, and existing disability insurance coverage details

**Technical Implementation Notes**: 
- The notebook must handle workspace root path resolution when run from the `standalone_tools` subdirectory (see plan.md Implementation Learnings section)
- The notebook must prevent Flask app initialization when importing app modules to avoid circular import errors (see plan.md Implementation Learnings section)
- These technical requirements are addressed in implementation task T003

## Out of Scope

- Integration with insurance provider APIs or quote systems
- Recommendations for specific insurance policies or providers
- Calculation of insurance premium costs
- Analysis of policy features beyond coverage percentage and duration
- Handling of partial disability scenarios (only total disability is considered)
- Integration into the main simulation application (this is a standalone script)
- Automated testing per constitutional requirements (exempted as standalone script not used as application input)

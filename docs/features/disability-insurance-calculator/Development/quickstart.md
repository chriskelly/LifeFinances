# Quickstart: Disability Insurance Calculator

**Date**: 2025-12-10  
**Feature**: Disability Insurance Calculator Script

## Overview

The Disability Insurance Calculator is a standalone Jupyter notebook that calculates how much additional disability insurance coverage you need beyond your existing employer-provided coverage. It accounts for lost job income, reduced Social Security benefits, and reduced pension benefits due to disability.

## Prerequisites

- Python 3.10+
- Jupyter notebook environment
- User configuration file (YAML) with:
  - Income profiles for user (and optionally partner)
  - Social Security settings
  - Pension settings
  - Existing disability insurance coverage details

## Setup

1. **Navigate to the notebook**:
   ```bash
   cd standalone_tools
   jupyter notebook disability_insurance_calculator.ipynb
   ```

2. **Ensure your config file is in the repository root**:
   - Default: `config.yml`
   - Or specify path in notebook

## Usage

### Step 1: Load Configuration

The notebook will load your user configuration file. Ensure it includes:
- Your age and partner age (if applicable)
- Income profiles for working years
- Social Security and pension settings
- Existing disability insurance coverage:
  ```yaml
  user_disability_coverage:
    percentage: 60.0  # Percentage of income covered
    duration_years: 5  # Duration of coverage in years
  
  partner_disability_coverage:  # Optional
    percentage: 50.0
    duration_years: 10
  ```

### Step 2: Run Baseline Scenario

The notebook runs a baseline simulation with your current income profiles to calculate:
- Expected job income until Benefit cutoff age (configurable, default 65)
- Expected Social Security benefits (lifetime, including post-Benefit cutoff age)
- Expected pension benefits (lifetime, including post-Benefit cutoff age)

**Sanity Check Output**: You'll see a summary of baseline income totals.

### Step 3: Run Disability Scenario

The notebook runs a disability simulation with job income set to zero to calculate:
- Lost job income (baseline - disability = $0)
- Reduced Social Security benefits (baseline SS - disability SS)
- Reduced pension benefits (baseline pension - disability pension)

**Sanity Check Output**: You'll see a comparison showing income reductions.

### Step 4: Calculate Coverage Gap

The notebook calculates:
1. **Total Income Replacement Needs**:
   - Lost job income until Benefit cutoff age (configurable, default 65)
   - Reduced Social Security (including post-Benefit cutoff age reductions)
   - Reduced pension (including post-Benefit cutoff age reductions)

2. **Existing Coverage Replacement**:
   - Coverage percentage applied to job income
   - After-tax benefits (employer-provided coverage is taxable)
   - Capped at 100% of income

3. **Remaining Coverage Gap**:
   - Total needs - Existing coverage
   - Expressed as percentage of income for duration in years

**Sanity Check Output**: You'll see breakdown of coverage replacement calculation.

### Step 5: View Results

The notebook outputs structured results:

```
=== DISABILITY INSURANCE COVERAGE ANALYSIS ===

USER SCENARIO:
Total Income Replacement Needed: $X,XXX,XXX
  - Lost Job Income (until Benefit cutoff age): $X,XXX,XXX
  - Reduced Social Security: $XXX,XXX
  - Reduced Pension: $XXX,XXX

Existing Coverage Replacement (after taxes): $XXX,XXX
  - Coverage: X% of income for Y years
  - Gross benefits: $XXX,XXX
  - Taxes: $XX,XXX
  - Net benefits: $XXX,XXX

Remaining Coverage Gap: $XXX,XXX
Recommended Coverage: X% of income for Y years
```

## Understanding the Results

### Total Income Replacement Needed

This is the total amount of income you would lose if disabled, including:
- **Lost job income**: Income you would have earned until Benefit cutoff age (configurable, default 65)
- **Reduced Social Security**: The difference between your expected Social Security (with full earnings) and what you'd receive (with truncated earnings). Includes post-Benefit cutoff age reductions.
- **Reduced pension**: The difference between your expected pension (with full work history) and what you'd receive (with early disability).

### Existing Coverage Replacement

This is what your current employer-provided disability insurance would actually pay (after taxes):
- Coverage percentage is applied to your job income
- Benefits are taxable (employer-provided coverage)
- Coverage is capped at 100% of income for gap calculation

### Remaining Coverage Gap

This is how much additional coverage you need:
- If gap is $0 or negative: You have adequate coverage
- If gap is positive: You need additional coverage
- Expressed as percentage of income for duration in years (standard insurance format)

## Example Scenarios

### Scenario 1: User with 60% Coverage for 5 Years

**Input**:
- User age: 35
- Current income: $100,000/year
- Existing coverage: 60% for 5 years
- Expected to work until Benefit cutoff age (configurable, default 65)

**Output**:
- Total replacement needs: $3,000,000 (30 years × $100k + reduced SS/pension)
- Existing coverage: $300,000 (60% × $100k × 5 years, after taxes)
- Coverage gap: $2,700,000
- Recommended: 90% of income for 30 years

### Scenario 2: User Already Has Adequate Coverage

**Input**:
- User age: 40
- Current income: $80,000/year
- Existing coverage: 100% for 25 years
- Expected to work until Benefit cutoff age (configurable, default 65)

**Output**:
- Total replacement needs: $2,000,000
- Existing coverage: $2,000,000 (100% × $80k × 25 years, after taxes)
- Coverage gap: $0
- **No additional coverage needed**

## Edge Cases Handled

### No Income Profiles

If neither you nor your partner have income profiles configured, the notebook will exit with:
```
No disability insurance needed - no future income to protect
```

### Already Retired

If you're already retired (no future income), the notebook will exit with:
```
No disability insurance needed - already retired
```

### User on Sabbatical

If your current income is $0 (sabbatical), the notebook uses your first future income profile with income > $0 for benefit percentage calculations.

### Coverage Exceeds 100%

If your existing coverage percentage exceeds 100%, it's capped at 100% for gap calculation purposes (disability insurance typically doesn't cover more than 100% of pre-disability income).

## Troubleshooting

### "No income profiles configured"

**Solution**: Ensure your config file includes `income_profiles` for user or partner.

### "Social Security calculation failed"

**Solution**: Ensure Social Security settings are configured in your config file.

### "Coverage gap is negative"

**Solution**: This means your existing coverage exceeds your needs. The notebook will display "No additional coverage needed".

## Next Steps

After running the calculator:

1. **Review the results** to understand your coverage gap
2. **Shop for disability insurance** using the recommended percentage and duration
3. **Re-run periodically** as your income or circumstances change
4. **Update your config** if you purchase additional coverage

## Notes

- The calculator assumes disability occurs immediately and lasts until Benefit cutoff age (configurable in script, default 65)
- All existing coverage is assumed to be employer-provided (taxable)
- Post-Benefit cutoff age income reductions (reduced Social Security) are included in total needs
- The calculator uses SimulationEngine to ensure accurate income and benefit projections

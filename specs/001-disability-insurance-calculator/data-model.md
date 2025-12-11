# Data Model: Disability Insurance Calculator

**Date**: 2025-12-10  
**Feature**: Disability Insurance Calculator Script

## Overview

This is a standalone Jupyter notebook that processes existing user configuration and SimulationEngine results. No new persistent data structures are created. The notebook operates on:

1. **Input**: User configuration (YAML) with income profiles, Social Security settings, pension settings, and existing disability coverage
2. **Processing**: SimulationEngine results (DataFrames) from baseline and disability scenarios
3. **Output**: Calculated coverage gap and benefit percentage (displayed in notebook)

## Data Flow

```
User Config (YAML)
    ↓
[Load Config]
    ↓
SimulationEngine(config_path) → gen_all_trials() → Baseline Results (DataFrame)
    ↓
[Modify engine._user_config.income_profiles] (zero job income)
    ↓
engine.results = Results() → gen_all_trials() → Disability Results (DataFrame)
    ↓
[Compare Results]
    ↓
[Calculate Coverage Gap]
    ↓
[Output Results]
```

## Key Data Structures

### Input: User Configuration

Uses existing `User` model from `app.models.config`:

- **User.age**: Current age (int)
- **User.income_profiles**: List of IncomeProfile objects
- **User.partner**: Optional Partner object with income_profiles
- **User.social_security_pension**: SocialSecurity configuration
- **User.partner.social_security_pension**: Partner SocialSecurity configuration (if partner exists)
- **Disability Coverage** (to be added to config):
  - `user_disability_coverage`: Dict with `percentage` (float) and `duration_years` (int)
  - `partner_disability_coverage`: Optional dict with `percentage` and `duration_years`

### Processing: SimulationEngine Results DataFrame

Columns from `results.as_dataframes()[0]`:

- **Date** (float): Date in decimal years
- **Job Income** (float): Job income per interval (quarterly)
- **SS User** (float): Social Security for user per interval
- **SS Partner** (float): Social Security for partner per interval
- **Pension** (float): Pension income per interval
- **Inflation** (float): Cumulative inflation factor per interval
- Additional columns (Income Taxes, Medicare Taxes, etc.) available but not primary focus

### Processing: RealFinancialData Class

The notebook uses a `RealFinancialData` class to encapsulate income stream extraction, conversion to real values, and post-tax calculations:

**Initialization**: `RealFinancialData(df: pd.DataFrame)`
- Extracts income streams and tax columns from simulation results DataFrame
- Converts all values from nominal to real (inflation-adjusted) by dividing by inflation
- Stores dates for filtering operations

**Properties**:
- `post_tax_income`: Post-tax income series (Job + SS User + SS Partner + Pension) + (Income Taxes + Medicare Taxes). Note: Taxes are already negative in the DataFrame, so addition is correct.
- `post_tax_total_lifetime`: Sum of post-tax income over all intervals
- `pre_tax_job_total_lifetime`: Sum of job income over all intervals
- `pre_tax_ss_total_lifetime`: Sum of Social Security (user + partner) over all intervals
- `pre_tax_pension_total_lifetime`: Sum of pension over all intervals
- `pre_tax_total_lifetime`: Sum of all pre-tax income components
- `dates`: Date series for filtering operations
- Individual real income series: `job_real_q`, `ss_user_real_q`, `ss_partner_real_q`, `pension_real_q`, `income_taxes_real_q`, `medicare_taxes_real_q`

**Usage**: 
- `baseline = RealFinancialData(baseline_df)`
- `disability = RealFinancialData(disability_df)`
- `partner_disability = RealFinancialData(partner_disability_df)`

### Calculated Values (in-memory)

- **baseline.post_tax_total_lifetime**: Total post-tax income from baseline scenario (lifetime)
- **disability.post_tax_total_lifetime**: Total post-tax income from disability scenario (lifetime)
- **total_replacement_needs**: Baseline post-tax income - Disability post-tax income (per FR-005, FR-008)
- **existing_coverage_replacement**: Net after-tax benefits from existing coverage
- **coverage_gap**: Total needs - Existing coverage
- **benefit_percentage**: (Coverage gap / Years until Benefit cutoff age) / Current annual income
- **years_until_benefit_cutoff_age**: Benefit cutoff age - user_age (or partner_age for partner scenario, using configurable Benefit cutoff age, default 65)
- **current_annual_income**: First income profile with income > $0, annualized

## Data Transformations

### 1. Engine Data Modification for Disability Scenario

**Input**: SimulationEngine instance (after baseline run)  
**Output**: Modified engine with zeroed job income

```python
# Create engine with config_path (following tpaw_planner.ipynb pattern)
engine = SimulationEngine(config_path=config_path, trial_qty=1)
engine.gen_all_trials()  # Run baseline scenario
baseline_results = engine.results

# Modify engine._user_config.income_profiles directly (like tpaw_planner modifies engine._economic_sim_data.inflation)
if engine._user_config.income_profiles:
    for profile in engine._user_config.income_profiles:
        profile.starting_income = 0.0

# Clear results and run disability scenario
engine.results = Results()
engine.gen_all_trials()  # Run disability scenario
disability_results = engine.results
```

### 2. Income Stream Extraction and Conversion

**Input**: Results DataFrame  
**Output**: `RealFinancialData` instance with processed income streams

```python
# Use RealFinancialData class to extract, convert, and process income streams
baseline = RealFinancialData(baseline_df)
disability = RealFinancialData(disability_df)

# Filter until Benefit cutoff age (using dates from RealFinancialData)
benefit_cutoff_age_date = BENEFIT_CUTOFF_AGE - user_config.age + TODAY_YR_QT
mask_until_benefit_cutoff_age = baseline.dates <= benefit_cutoff_age_date

# Access pre-tax and post-tax totals via properties
baseline_pre_tax_job_total_lifetime = baseline.pre_tax_job_total_lifetime
baseline_pre_tax_ss_total_lifetime = baseline.pre_tax_ss_total_lifetime
baseline_pre_tax_pension_total_lifetime = baseline.pre_tax_pension_total_lifetime
baseline_post_tax_total_lifetime = baseline.post_tax_total_lifetime

# Calculate total replacement needs (post-tax)
total_replacement_needs = baseline.post_tax_total_lifetime - disability.post_tax_total_lifetime
```

### 3. Coverage Replacement Calculation

**Input**: Baseline job income, coverage percentage, coverage duration, tax rates  
**Output**: Net after-tax coverage replacement

```python
# Extract job income for coverage period
coverage_start = dates.iloc[0]
coverage_end = coverage_start + coverage_duration_years
coverage_mask = (dates >= coverage_start) & (dates <= coverage_end)

# Apply coverage percentage (capped at 100%)
coverage_per_interval = min(coverage_percentage, 100.0) / 100.0 * job_income[coverage_mask]

# Calculate taxes (simplified - use average tax rate or extract from results)
# For accuracy, could extract tax rates from baseline scenario results
tax_rate = 0.25  # Example - should be calculated from actual tax data
net_coverage = coverage_per_interval * (1 - tax_rate)

# Sum total coverage replacement
total_coverage_replacement = net_coverage.sum()
```

### 4. Gap Calculation

**Input**: Total replacement needs, existing coverage replacement  
**Output**: Coverage gap and benefit percentage

```python
# Calculate gap
coverage_gap = total_replacement_needs - existing_coverage_replacement
coverage_gap = max(0, coverage_gap)  # Cannot be negative

# Calculate benefit percentage
years_until_benefit_cutoff_age = calculate_years_until_benefit_cutoff_age(user_config.age)
current_annual_income = get_current_annual_income(user_config, is_partner=False)
coverage_gap = total_replacement_needs - existing_coverage_replacement
benefit_percentage = (coverage_gap / years_until_benefit_cutoff_age) / current_annual_income * 100
```

## Validation Rules

### Input Validation

- User config must have at least one income profile (user or partner)
- User age must be < Benefit cutoff age (configurable, default 65, or exit with message if already retired)
- Coverage percentage must be >= 0 (can exceed 100%, but capped at 100% for calculation)
- Coverage duration must be > 0

### Calculation Validation

- Total replacement needs >= 0
- Coverage gap >= 0 (cannot be negative)
- Benefit percentage >= 0
- Years until Benefit cutoff age > 0

### Sanity Checks (Periodic Outputs)

- Display baseline vs disability income totals for verification
- Display Social Security totals (baseline vs disability) to verify reductions
- Display pension totals (baseline vs disability) to verify reductions
- Display coverage replacement calculation breakdown
- Display final gap and benefit percentage

## Edge Cases

### No Income Profiles

**Detection**: `user_config.income_profiles is None or empty` AND `partner.income_profiles is None or empty`  
**Action**: Exit with message "No disability insurance needed - no future income to protect"

### Already Retired

**Detection**: All income profiles have `starting_income == 0`  
**Action**: Exit with message "No disability insurance needed - already retired"

### User Has No Income, Partner Has Income

**Detection**: `user_config.income_profiles is None or empty` AND `partner.income_profiles exists`  
**Action**: Calculate only for partner scenario

### Coverage > 100%

**Detection**: `coverage_percentage > 100`  
**Action**: Cap at 100% for gap calculation, but display actual percentage in output

### Coverage Duration Beyond Benefit Cutoff Age

**Detection**: `coverage_start + coverage_duration_years > benefit_cutoff_age_date`  
**Action**: Apply coverage until Benefit cutoff age (coverage naturally ends at LTD age limit, configurable, default 65)

## Data Persistence

**None** - This is a standalone notebook with no persistent storage. All data is:
- Read from user config file (input)
- Processed in-memory (calculations)
- Displayed in notebook (output)

No database, no file writes (except optional export of results).

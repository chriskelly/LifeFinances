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
- **Disability Coverage**: Uses `DisabilityInsuranceCalculator` model from `app.models.config`:
  - `User.disability_insurance_calculator`: Optional `DisabilityInsuranceCalculator` object
  - `DisabilityInsuranceCalculator.user_disability_coverage`: `DisabilityCoverage` object with `percentage` (float, defaults to 0.0) and `duration_years` (int, defaults to 0)
  - `DisabilityInsuranceCalculator.partner_disability_coverage`: `DisabilityCoverage` object with `percentage` (float, defaults to 0.0) and `duration_years` (int, defaults to 0)
  - `DisabilityCoverage` is a Pydantic BaseModel with attributes:
    - `percentage`: float (defaults to 0.0)
    - `duration_years`: int (defaults to 0)

### Processing: SimulationEngine Results DataFrame

Columns from `results.as_dataframes()[0]`:

- **Date** (float): Date in decimal years
- **Job Income** (float): Job income per interval (quarterly)
- **SS User** (float): Social Security for user per interval
- **SS Partner** (float): Social Security for partner per interval
- **Pension** (float): Pension income per interval
- **Inflation** (float): Cumulative inflation factor per interval
- Additional columns (Income Taxes, Medicare Taxes, etc.) available but not primary focus

### Processing: RealFinancialData Class and CoverageResults

The notebook uses a `RealFinancialData` class to encapsulate income stream extraction, conversion to real values, and post-tax calculations. Coverage calculations return a `CoverageResults` dataclass:

**`CoverageResults` dataclass**:
- `gross_benefits`: Total gross coverage benefits (before taxes)
- `taxes`: Total taxes on benefits
- `total_net_replacement`: Net after-tax coverage replacement

**`RealFinancialData` class**:

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
- **Methods**:
  - `get_coverage_results(coverage: DisabilityCoverage, benefit_cutoff_date: float)`: Calculates existing coverage replacement (net after taxes). Takes a `DisabilityCoverage` Pydantic model object (from `app.models.config`) with `percentage` and `duration_years` attributes. Returns a `CoverageResults` dataclass containing `gross_benefits`, `taxes`, and `total_net_replacement`. Handles zero coverage internally by returning `CoverageResults(0.0, 0.0, 0.0)` if `coverage.percentage == 0` or `coverage.duration_years == 0`. Coverage end date is capped at `benefit_cutoff_date` using `min(coverage_start + coverage.duration_years, benefit_cutoff_date)`. Coverage percentage is capped at 100% for calculation using `min(coverage.percentage, 100.0)`. Uses average tax rate from baseline scenario.

**Additional helper functions and classes** (for DRY principles, eliminating duplication between user and partner scenarios):

- **`build_engine()`**: Creates and configures a `SimulationEngine` instance with fixed inflation. Used for both baseline and partner scenario engine creation.

- **`build_mask_until_benefit_cutoff_age(benefit_cutoff_date: float) -> pd.Series`**: Creates a pandas Series mask for filtering dates up to the benefit cutoff age. Used consistently for both user and partner scenarios.

- **`IncomeComparison` class**: Encapsulates income comparison calculations between baseline and disability scenarios. Properties:
  - `total_replacement_needs`: Post-tax income replacement needed (baseline - disability)
  - `lost_pre_tax_job_income`: Lost job income (pre-tax, for reference)
  - `reduced_pre_tax_ss`: Reduced Social Security (pre-tax, for reference)
  - `reduced_pre_tax_pension`: Reduced pension (pre-tax, for reference)
  Used for both user and partner scenarios.

- **`calculate_coverage_gap(total_replacement_needs: float, total_net_replacement: float) -> float`**: Calculates remaining coverage gap as `max(0, total_replacement_needs - total_net_replacement)`. Used for both user and partner scenarios.

- **`calculate_benefit_percentage(coverage_gap: float, years_until_benefit_cutoff_age: float, current_annual_income: float) -> float`**: Calculates recommended benefit percentage using formula: `(coverage_gap / years_until_benefit_cutoff_age) / current_annual_income * 100`. Returns 0.0 if years or income is 0. Used for both user and partner scenarios.

**Usage**: 
- `baseline = RealFinancialData(baseline_df)`
- `disability = RealFinancialData(disability_df)`
- `partner_disability = RealFinancialData(partner_disability_df)`
- `coverage_results = baseline.get_coverage_results(user_disability_coverage, benefit_cutoff_date)`
  - Where `user_disability_coverage` is a `DisabilityCoverage` object from `user_config.disability_insurance_calculator.user_disability_coverage`

### Calculated Values (in-memory)

- **baseline.post_tax_total_lifetime**: Total post-tax income from baseline scenario (lifetime)
- **disability.post_tax_total_lifetime**: Total post-tax income from disability scenario (lifetime)
- **total_replacement_needs**: Baseline post-tax income - Disability post-tax income (per FR-005, FR-008)
- **coverage_results**: `CoverageResults` object from `baseline.get_coverage_results()` containing:
  - `gross_benefits`: Total gross coverage benefits (before taxes)
  - `taxes`: Total taxes on benefits
  - `total_net_replacement`: Net after-tax coverage replacement
- **existing_coverage_replacement**: Net after-tax benefits from existing coverage (from `coverage_results.total_net_replacement`)
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

# Use helper functions and classes for calculations
benefit_cutoff_date = BENEFIT_CUTOFF_AGE - user_config.age + TODAY_YR_QT
mask_until_benefit_cutoff_age = build_mask_until_benefit_cutoff_age(benefit_cutoff_date)

# Use IncomeComparison class to encapsulate income comparison calculations
user_income_comparison = IncomeComparison(baseline, disability)
# Access properties: total_replacement_needs, lost_pre_tax_job_income, reduced_pre_tax_ss, reduced_pre_tax_pension

# Calculate coverage gap and benefit percentage using helper functions
coverage_gap = calculate_coverage_gap(
    user_income_comparison.total_replacement_needs,
    coverage_results.total_net_replacement
)
benefit_percentage = calculate_benefit_percentage(
    coverage_gap,
    years_until_benefit_cutoff_age,
    current_annual_income
)

### 3. Coverage Replacement Calculation

**Input**: `RealFinancialData` instance (baseline), `DisabilityCoverage` object, benefit cutoff date  
**Output**: `CoverageResults` object with gross_benefits, taxes, and total_net_replacement

```python
# Use RealFinancialData method to calculate coverage replacement
benefit_cutoff_date = BENEFIT_CUTOFF_AGE - user_config.age + TODAY_YR_QT
user_disability_coverage = user_config.disability_insurance_calculator.user_disability_coverage
coverage_results = baseline.get_coverage_results(
    user_disability_coverage, benefit_cutoff_date
)

# CoverageResults contains:
# - gross_benefits: Total gross coverage benefits (before taxes)
# - taxes: Total taxes on benefits
# - total_net_replacement: Net after-tax coverage replacement

existing_coverage = coverage_results.total_net_replacement
```

**Implementation details** (inside `get_coverage_results`):
- Coverage period: `coverage_start` to `min(coverage_start + coverage.duration_years, benefit_cutoff_date)`
- Coverage percentage capped at 100% for calculation: `min(coverage.percentage, 100.0) / 100.0`
- Average tax rate calculated from baseline scenario: `(total income taxes + total Medicare taxes) / total income` for coverage period
- Net benefits: `coverage_benefits - taxes_on_benefits`

### 4. Gap Calculation

**Input**: Total replacement needs, existing coverage replacement  
**Output**: Coverage gap and benefit percentage

```python
# Calculate gap using helper function
coverage_gap = calculate_coverage_gap(
    user_income_comparison.total_replacement_needs,
    coverage_results.total_net_replacement
)

# Calculate benefit percentage using helper function
years_until_benefit_cutoff_age = calculate_years_until_benefit_cutoff_age(user_config.age)
current_annual_income = get_current_annual_income(user_config, is_partner=False)
benefit_percentage = calculate_benefit_percentage(
    coverage_gap,
    years_until_benefit_cutoff_age,
    current_annual_income
)
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

### Final Summary Section

The notebook includes a "Final Summary" section at the end that consolidates all results using the `display_insurance_results()` helper function. This section:
- Displays user disability insurance calculation results separately (per FR-015)
- Displays partner disability insurance calculation results separately (per FR-015)
- Provides structured output per FR-009 requirements:
  1. Total income replacement needed (with component breakdown)
  2. Existing coverage replacement (after taxes, with breakdown)
  3. Remaining coverage gap in standard disability insurance format (% of income for x years)

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

**Detection**: `coverage_start + coverage_duration_years > benefit_cutoff_date`  
**Action**: Apply coverage until Benefit cutoff age (coverage naturally ends at LTD age limit, configurable, default 65)

## Data Persistence

**None** - This is a standalone notebook with no persistent storage. All data is:
- Read from user config file (input)
- Processed in-memory (calculations)
- Displayed in notebook (output)

No database, no file writes (except optional export of results).

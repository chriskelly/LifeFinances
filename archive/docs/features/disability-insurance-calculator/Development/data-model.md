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
  - `get_coverage_results(coverage: DisabilityCoverage, insured_age: int, *, current_annual_income: float)`: Calculates existing coverage replacement (net after taxes). Takes a `DisabilityCoverage` Pydantic model object (from `app.models.config`) with `percentage`, `duration_years`, and/or `age_limit`. Returns a `CoverageResults` dataclass containing `gross_benefits`, `taxes`, and `total_net_replacement`. Handles zero coverage internally by returning `CoverageResults(0.0, 0.0, 0.0)` if `coverage.percentage == 0` or `current_annual_income <= 0`. Benefit base is flat real quarterly income from `current_annual_income` (not projected future job income). Coverage end date is `coverage_policy_end_date(coverage, insured_age, coverage_start, simulation_end_date=last simulation quarter)`. Coverage percentage is capped at 100% for calculation using `min(coverage.percentage, 100.0)`. Uses average tax rate from baseline earning quarters (`job_real_q > 0`).

**Additional helper functions and classes** (for DRY principles, eliminating duplication between user and partner scenarios):

- **`build_engine()`**: Creates and configures a `SimulationEngine` instance with fixed inflation. Used for both baseline and partner scenario engine creation.

- **`coverage_policy_end_date(coverage, insured_age, coverage_start, *, simulation_end_date=None) -> float`**: Policy-end date from config: `age_limit` → date when insured reaches that age; `duration_years` → `coverage_start + duration_years`. When `simulation_end_date` is set, returns `min(configured_end, simulation_end_date)` so lifetime or very long durations cap at the simulation horizon (`calculate_til` / last trial quarter).

- **`years_until_policy_end(end_date) -> float`**: Calendar years from `TODAY_YR_QT` until policy end.

- **`format_disability_coverage_period(coverage) -> str`** / **`policy_end_duration_label(...)`**: Human-readable policy period for output.

- **`IncomeComparison` class**: Encapsulates income comparison calculations between baseline and disability scenarios. Properties:
  - `total_replacement_needs`: Post-tax income replacement needed (baseline - disability)
  - `lost_pre_tax_job_income`: Lost job income (pre-tax, for reference)
  - `reduced_pre_tax_ss`: Reduced Social Security (pre-tax, for reference)
  - `reduced_pre_tax_pension`: Reduced pension (pre-tax, for reference)
  Used for both user and partner scenarios.

- **`calculate_coverage_gap(total_replacement_needs: float, total_net_replacement: float) -> float`**: Calculates remaining coverage gap as `max(0, total_replacement_needs - total_net_replacement)`. Used for both user and partner scenarios.

- **`calculate_benefit_percentage(coverage_gap: float, years_until_policy_end: float, current_annual_income: float) -> float`**: Calculates recommended benefit percentage using formula: `(coverage_gap / years_until_policy_end) / current_annual_income * 100`. Returns 0.0 if years or income is 0. Used for both user and partner scenarios.

**Usage**: 
- `baseline = RealFinancialData(baseline_df)`
- `disability = RealFinancialData(disability_df)`
- `partner_disability = RealFinancialData(partner_disability_df)`
- `coverage_results = baseline.get_coverage_results(user_disability_coverage, user_config.age, current_annual_income=get_current_annual_income(user_config))`
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
- **benefit_percentage**: (Coverage gap / years until policy end) / Current annual income
- **years_until_policy_end**: `coverage_policy_end_date(...) - TODAY_YR_QT` (per person, from their `DisabilityCoverage`)
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

user_coverage_start = float(baseline.dates.iloc[0])
simulation_end = float(baseline.dates.iloc[-1])
user_policy_end_date = coverage_policy_end_date(
    user_disability_coverage,
    user_config.age,
    user_coverage_start,
    simulation_end_date=simulation_end,
)

user_income_comparison = IncomeComparison(baseline, disability)

coverage_gap = calculate_coverage_gap(
    user_income_comparison.total_replacement_needs,
    coverage_results.total_net_replacement
)
years_until_policy_end_user = years_until_policy_end(user_policy_end_date)
benefit_percentage = calculate_benefit_percentage(
    coverage_gap,
    years_until_policy_end_user,
    current_annual_income,
)

### 3. Coverage Replacement Calculation

**Input**: `RealFinancialData` instance (baseline), `DisabilityCoverage` object, insured age  
**Output**: `CoverageResults` object with gross_benefits, taxes, and total_net_replacement

```python
user_disability_coverage = user_config.disability_insurance_calculator.user_disability_coverage
coverage_results = baseline.get_coverage_results(
    user_disability_coverage,
    user_config.age,
    current_annual_income=get_current_annual_income(user_config),
)

# CoverageResults contains:
# - gross_benefits: Total gross coverage benefits (before taxes)
# - taxes: Total taxes on benefits
# - total_net_replacement: Net after-tax coverage replacement

existing_coverage = coverage_results.total_net_replacement
```

**Implementation details** (inside `get_coverage_results`):
- Coverage period: `coverage_start` to capped `coverage_policy_end_date(..., simulation_end_date=last simulation quarter)`
- Gross benefits: `(current_annual_income / INTERVALS_PER_YEAR) * min(coverage.percentage, 100%) * num_quarters_in_window`
- Average tax rate from baseline earning quarters only (`job_real_q > 0`): `(total income taxes + total Medicare taxes) / total job income`
- Net benefits: `gross_benefits - taxes`

### 4. Gap Calculation

**Input**: Total replacement needs, existing coverage replacement  
**Output**: Coverage gap and benefit percentage

```python
# Calculate gap using helper function
coverage_gap = calculate_coverage_gap(
    user_income_comparison.total_replacement_needs,
    coverage_results.total_net_replacement
)

years_until_policy_end_user = years_until_policy_end(user_policy_end_date)
current_annual_income = get_current_annual_income(user_config, is_partner=False)
benefit_percentage = calculate_benefit_percentage(
    coverage_gap,
    years_until_policy_end_user,
    current_annual_income,
)
```

## Validation Rules

### Input Validation

- User config must have at least one income profile (user or partner)
- When `percentage > 0`, config must set `age_limit` or `duration_years` (Pydantic validation on `DisabilityCoverage`)
- Coverage percentage must be >= 0 (can exceed 100%, but capped at 100% for calculation)
- Coverage duration must be > 0

### Calculation Validation

- Total replacement needs >= 0
- Coverage gap >= 0 (cannot be negative)
- Benefit percentage >= 0
- Years until policy end > 0 when recommending additional coverage

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

### Policy end from config

**Detection**: `age_limit` or `duration_years` on `DisabilityCoverage`  
**Action**: Employer benefits and gap % denominator use the same capped `coverage_policy_end_date()` — `age_limit` until that age, or `coverage_start + duration_years` when only duration is set, capped at simulation end

### Policy extends past simulation (lifetime / long duration)

**Detection**: Configured policy end (e.g. `age_limit: 100` or `duration_years: 100`) exceeds `calculate_til` / last simulation quarter  
**Action**: Cap policy end at `simulation_end_date` so benefits stop at estimated death horizon, not an unbounded calendar date

## Data Persistence

**None** - This is a standalone notebook with no persistent storage. All data is:
- Read from user config file (input)
- Processed in-memory (calculations)
- Displayed in notebook (output)

No database, no file writes (except optional export of results).

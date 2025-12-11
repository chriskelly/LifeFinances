# Research: Disability Insurance Calculator

**Date**: 2025-12-10  
**Feature**: Disability Insurance Calculator Script

## Research Questions & Findings

### Q1: How to use SimulationEngine for baseline vs disability scenarios?

**Decision**: Use a single SimulationEngine instance and modify engine data directly (following `tpaw_planner.ipynb` pattern):
1. **Baseline scenario**: Create SimulationEngine with `config_path`, run `gen_all_trials()` to get baseline results
2. **Disability scenario**: Modify `engine._user_config.income_profiles` directly to zero out job income, clear results with `engine.results = Results()`, run `gen_all_trials()` again

**Rationale**: 
- SimulationEngine takes `config_path` (Path), not `user_config` object
- Follows pattern from `tpaw_planner.ipynb` which modifies `engine._economic_sim_data.inflation` directly
- Avoids tight coupling with individual controllers
- Can reuse same engine instance for both scenarios by modifying internal state
- Can compare results DataFrames directly to calculate differences

**Alternatives considered**:
- Using individual controllers (job_income, social_security, pension) - **Rejected** due to tight coupling concerns mentioned in requirements
- Creating separate SimulationEngine instances with modified configs - **Rejected** because SimulationEngine doesn't accept `user_config` parameter
- Creating modified config file - **Rejected** as unnecessary when engine data can be modified directly

**Implementation approach**:
- Load user config from file (for validation and disability coverage extraction)
- Create SimulationEngine with `config_path=config_path, trial_qty=1`
- Run baseline: `engine.gen_all_trials()`, save baseline results
- Modify `engine._user_config.income_profiles` to zero out job income for disability scenario
- Clear results: `engine.results = Results()`
- Run disability: `engine.gen_all_trials()` again
- Compare results DataFrames to calculate income replacement needs

### Q2: How to extract income streams and Social Security from SimulationEngine results?

**Decision**: Use `results.as_dataframes()` method to get trial DataFrames with columns:
- "Job Income" - job income per interval
- "SS User" - Social Security for user per interval
- "SS Partner" - Social Security for partner per interval  
- "Pension" - pension income per interval
- "Inflation" - inflation factor per interval
- "Date" - date per interval

**Rationale**:
- Matches pattern used in `tpaw_planner.ipynb`
- Provides all needed income streams in structured format
- Includes inflation for real value calculations
- Includes dates for age-based calculations (until Benefit cutoff age, configurable, default 65)

**Alternatives considered**:
- Accessing controllers directly - **Rejected** due to tight coupling
- Custom result extraction - **Rejected** as unnecessary when DataFrame API exists

### Q3: How to handle post-Benefit cutoff age income reductions (reduced Social Security)?

**Decision**: Calculate Social Security for both scenarios and compare:
- Baseline scenario: Full Social Security based on complete earnings history
- Disability scenario: Reduced Social Security based on truncated earnings history (no job income after disability)
- Difference = post-Benefit cutoff age reduction amount to include in total replacement needs

**Rationale**:
- SimulationEngine automatically calculates Social Security based on earnings history
- Disability scenario will have reduced earnings history, resulting in lower Social Security
- Can extract SS User and SS Partner columns from both scenarios and sum differences
- Post-Benefit cutoff age reductions are naturally included in the lifetime Social Security totals

**Alternatives considered**:
- Manual Social Security calculation - **Rejected** as SimulationEngine handles this correctly
- Ignoring post-Benefit cutoff age reductions - **Rejected** per spec requirement

### Q4: How to calculate existing coverage replacement with taxes?

**Decision**: 
1. Extract job income from baseline scenario
2. Apply coverage percentage (capped at 100%) to each interval within coverage duration
3. Calculate taxes on disability benefits using existing tax calculation logic
4. Sum net after-tax benefits over coverage duration

**Rationale**:
- Need to apply taxes to employer-provided benefits (all coverage is employer-provided)
- Can use existing tax calculation from SimulationEngine results or calculate separately
- Coverage duration may extend beyond working years (until Benefit cutoff age, configurable, default 65)
- Must cap coverage at 100% of income for gap calculation

**Implementation approach**:
- Extract "Job Income" column from baseline scenario
- For each interval within coverage duration: `coverage_amount = min(coverage_percentage, 100%) * job_income`
- Calculate income tax on coverage_amount (employer-provided benefits are taxable)
- Sum net after-tax benefits: `net_benefit = coverage_amount - income_tax`

### Q5: How to calculate coverage gap and benefit percentage?

**Decision**: 
1. Calculate total income replacement needs:
   - Lost job income until Benefit cutoff age (configurable, default 65)
   - Reduced Social Security (baseline SS - disability SS, including post-Benefit cutoff age)
   - Reduced pension (baseline pension - disability pension, including post-Benefit cutoff age)
2. Calculate existing coverage replacement (net after taxes)
3. Coverage gap = Total needs - Existing coverage
4. Benefit percentage = (Coverage gap / Years until Benefit cutoff age) / Current annual income
   - Current annual income = first income profile with income > $0

**Rationale**:
- Matches spec requirements for gap calculation
- Includes post-Benefit cutoff age reductions in total needs
- Uses standard LTD benefit percentage formula
- Accounts for sabbatical scenarios (current income = 0)

**Implementation approach**:
- Sum all income differences (job + SS + pension) from baseline vs disability scenarios
- Calculate years until Benefit cutoff age from user age (using configurable Benefit cutoff age, default 65)
- Find first income profile with income > $0 for current annual income
- Apply formula: `benefit_pct = (total_needs / years_until_benefit_cutoff_age) / current_annual_income`

### Q6: How to handle edge cases (no income profiles, already retired)?

**Decision**: 
- Check if user and partner have income profiles before running simulations
- If neither have income profiles: Exit with clear message
- If user has no income but partner does: Only calculate for partner
- If already retired (no future income): Exit with clear message

**Rationale**:
- Prevents unnecessary simulation runs
- Provides clear user feedback
- Matches spec requirements for edge case handling

**Implementation approach**:
- Validate config before creating SimulationEngine instances
- Check `user_config.income_profiles` and `user_config.partner.income_profiles`
- Check if all income profiles have zero income (already retired)
- Display appropriate messages and exit early if needed

## Technology Choices

### SimulationEngine
- **Chosen**: Use existing SimulationEngine class
- **Rationale**: Provides complete income, Social Security, and pension calculations without tight coupling to individual controllers
- **Source**: `app.models.simulator.SimulationEngine`

### Jupyter Notebook
- **Chosen**: Jupyter notebook format
- **Rationale**: 
  - Enables periodic outputs for sanity checks
  - Follows pattern from `tpaw_planner.ipynb`
  - Interactive exploration and debugging
- **Location**: `/standalone_tools/disability_insurance_calculator.ipynb`

### pandas/numpy
- **Chosen**: Use pandas DataFrames and numpy for calculations
- **Rationale**: 
  - SimulationEngine results are already in DataFrame format
  - Efficient time-series calculations
  - Standard data manipulation tools
- **Already in use**: Project already uses pandas/numpy

## Integration Points

### User Configuration
- **Source**: YAML config file (same as main application)
- **Fields needed**:
  - Income profiles (user and partner)
  - Social Security settings
  - Pension settings
  - Existing disability insurance coverage (percentage, duration)
  - User age
  - Partner age (if applicable)

### SimulationEngine
- **Usage**: Create single instance with `config_path`, modify `engine._user_config.income_profiles` directly for disability scenario
- **Output**: Results DataFrames with income streams, Social Security, pension, inflation, dates
- **Modification**: Modify `engine._user_config.income_profiles` directly (following `tpaw_planner.ipynb` pattern of modifying engine data)

### Q7: How to handle workspace root path resolution when notebook is in subdirectory?

**Decision**: Implement workspace root detection and path management before any app module imports:
1. Detect if notebook is in `standalone_tools` subdirectory
2. Add workspace root to `sys.path` at position 0
3. Change working directory to workspace root using `os.chdir(workspace_root)`

**Rationale**:
- Python resolves relative paths during module import time, not at runtime
- If working directory is not workspace root when `app` modules are imported, relative file paths within those modules (e.g., `constants.STATISTICS_PATH`) will fail with `FileNotFoundError`
- Must be done BEFORE any `from app...` imports

**Implementation pattern**:
```python
import sys
import os
from pathlib import Path

# Determine workspace root directory
notebook_dir = Path.cwd()
workspace_root = notebook_dir.parent if notebook_dir.name == "standalone_tools" else notebook_dir

# Add workspace root to path FIRST, before any imports
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

# Change working directory to workspace root so relative paths work
# This is critical - must be done before any app module imports
os.chdir(workspace_root)
```

**Alternatives considered**:
- Using absolute paths in app modules - **Rejected** as it would require modifying existing app code
- Running notebook from workspace root - **Rejected** as it's less intuitive for users and doesn't match project structure

### Q8: How to prevent Flask app initialization when importing app modules in standalone notebook?

**Decision**: Use environment variable `SKIP_FLASK_INIT=1` to conditionally skip Flask route imports in `app/__init__.py`.

**Rationale**:
- When importing `app.models.simulator` from a notebook, Python executes `app/__init__.py`
- `app/__init__.py` imports Flask routes, which import other app modules, creating circular import errors
- By conditionally skipping Flask initialization when `SKIP_FLASK_INIT=1`, we avoid this issue
- The `app/__init__.py` file was modified to check this environment variable before importing Flask routes

**Implementation pattern**:
```python
# Set environment variable to skip Flask app initialization
# This prevents circular import issues when importing app modules
os.environ["SKIP_FLASK_INIT"] = "1"

# Now safe to import app modules
from app.models.simulator import SimulationEngine
```

**Modification to app/__init__.py**:
```python
import os
_skip_flask_init = os.environ.get("SKIP_FLASK_INIT", "0") == "1"

if not _skip_flask_init:
    from flask import Flask, request
    from app.routes.api import api as api_blueprint
    from app.routes.index import IndexPage
```

**Alternatives considered**:
- Creating separate import paths for standalone scripts - **Rejected** as it would duplicate code
- Modifying app structure to avoid circular imports - **Rejected** as it would require significant refactoring

## Open Questions Resolved

All technical questions resolved. Ready to proceed to Phase 1 design.

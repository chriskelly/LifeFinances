# Implementation Plan: Disability Insurance Calculator Script

**Branch**: `001-disability-insurance-calculator` | **Date**: 2025-12-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-disability-insurance-calculator/spec.md`

## Summary

Build a standalone Jupyter notebook that calculates disability insurance coverage needs by comparing baseline income projections (with job income) against disability scenarios (without job income). The script uses SimulationEngine to calculate income streams and Social Security benefits, avoiding direct use of individual controllers due to tight coupling. The notebook outputs structured results showing total replacement needs, existing coverage replacement (after taxes), and remaining coverage gap in standard disability insurance format.

**Technical Approach**: 
- Use SimulationEngine (like `tpaw_planner.ipynb`) to run baseline and disability scenarios
- Create single engine with `config_path`, set fixed inflation rate using `set_fixed_inflation()` helper function (following `tpaw_planner.ipynb` pattern)
- Run baseline scenario with fixed inflation
- Modify `engine._user_config.income_profiles` directly to zero out job income (following `tpaw_planner.ipynb` pattern of modifying engine data)
- Clear results and run disability scenario with same engine (fixed inflation already set)
- Compare results DataFrames to calculate income replacement needs using post-tax income values
- Calculate post-tax income for each scenario: (Job Income + Social Security + Pension) - (Income Taxes + Medicare Taxes)
- Total replacement needs = Baseline post-tax income - Disability post-tax income
- Include post-Benefit cutoff age income reductions (e.g., reduced Social Security benefits after Benefit cutoff age) in total needs (see FR-005, FR-006, FR-008)
- Calculate existing coverage replacement with tax adjustments
- Output structured text results with coverage gap and benefit percentage

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: 
- SimulationEngine (from `app.models.simulator`)
- interval_yield (from `app.util`) for fixed inflation rate calculation
- pandas, numpy (for data processing)
- Jupyter notebook environment
- Existing user configuration structure (YAML config files)

**Storage**: N/A (standalone script reads from config file)  
**Testing**: N/A (exempted per constitution - standalone script/notebook)  
**Target Platform**: Jupyter notebook environment (local or cloud)  
**Project Type**: standalone analysis tool  
**Performance Goals**: Complete calculation in under 2 minutes per user  
**Constraints**: 
- Must use SimulationEngine (not individual controllers) to avoid tight coupling
- Must handle edge cases: no income profiles, already retired, coverage > 100%
- Must account for post-Benefit cutoff age income reductions (e.g., reduced Social Security benefits after Benefit cutoff age)
- Must allow Benefit cutoff age to be configured in the script (default value is 65, but user must be able to set a different Benefit cutoff age)
- Must handle workspace root path resolution (notebook is in subdirectory)
- Must prevent Flask app initialization when importing app modules (circular import prevention)
**Scale/Scope**: Single-user calculations, one-off analysis tool

## Implementation Learnings

### Workspace Root Path Handling

When running a notebook from a subdirectory (`/standalone_tools`), the following steps are **critical** and must be executed **before any app module imports**:

1. **Determine workspace root**: Detect if notebook is in `standalone_tools` subdirectory, set workspace root to parent directory
2. **Add to sys.path**: Insert workspace root at the beginning of `sys.path` to enable `from app...` imports
3. **Change working directory**: Call `os.chdir(workspace_root)` so relative paths within `app` modules (e.g., `constants.STATISTICS_PATH`) resolve correctly

**Rationale**: Python resolves relative paths during module import time, not at runtime. If the working directory is not the workspace root when `app` modules are imported, relative file paths within those modules will fail.

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

### Flask App Initialization Skipping

When importing `app` modules in a standalone notebook/script, Flask route imports can cause circular import errors. The solution is to conditionally skip Flask initialization:

1. **Set environment variable**: Set `SKIP_FLASK_INIT=1` before importing any `app` modules
2. **Conditional imports in app/__init__.py**: The Flask app initialization code checks this environment variable and skips route imports when the flag is set

**Rationale**: The `app/__init__.py` file imports Flask routes, which in turn import other app modules. When a notebook imports `app.models.simulator`, it triggers `app/__init__.py` execution, which tries to import routes, creating a circular dependency. By skipping Flask initialization in standalone contexts, we avoid this issue.

**Implementation pattern**:
```python
# Set environment variable to skip Flask app initialization
# This prevents circular import issues when importing app modules
os.environ["SKIP_FLASK_INIT"] = "1"

# Now safe to import app modules
from app.models.simulator import SimulationEngine
from app.util import interval_yield
```

**Note**: The `app/__init__.py` file was modified to support this pattern by checking `os.environ.get("SKIP_FLASK_INIT", "0") == "1"` before importing Flask routes.

### Fixed Inflation Rate Setting

When running simulations for deterministic analysis (like disability insurance calculations), it's often desirable to use a fixed inflation rate rather than simulated random inflation. This ensures stable real income levels for downstream processing and makes results more predictable.

**Implementation pattern** (following `tpaw_planner.ipynb`):
```python
def set_fixed_inflation(engine: SimulationEngine, inflation_rate: float) -> None:
    """Set fixed inflation rate for all trials in the simulation engine.
    
    This function overrides the simulated cumulative inflation path with a
    deterministic one based on the specified annual inflation rate, ensuring
    stable real income levels for downstream processing.
    
    Args:
        engine: SimulationEngine instance
        inflation_rate: Annual inflation rate as a decimal (e.g., 0.02 for 2%)
    """
    user_config = engine._user_config
    interval_inflation_yield = interval_yield(1 + inflation_rate)
    intervals = user_config.intervals_per_trial
    # Cumulative inflation series starting at 1.0
    cumulative = np.array([interval_inflation_yield ** i for i in range(intervals)], dtype=float)
    # `_economic_sim_data.inflation` has shape (trial_qty, intervals_per_trial)
    engine._economic_sim_data.inflation[:, :] = cumulative

# Usage:
engine = SimulationEngine(config_path=config_path, trial_qty=1)
set_fixed_inflation(engine, 0.02)  # Set 2% annual inflation
engine.gen_all_trials()
```

**Rationale**: The `SimulationEngine` generates random inflation paths by default. For deterministic analysis where we want consistent real income values, we override the inflation data with a fixed cumulative inflation series. This is done before calling `gen_all_trials()` so all simulation trials use the same inflation path.

### Income Timeline Handling

**CRITICAL**: The SimulationEngine returns income values that are already quarterly (per interval). Each interval in the timeline represents one quarter, and the income value for that interval is the income for that quarter. When summing income across the timeline, **DO NOT annualize** by multiplying by `INTERVALS_PER_YEAR`. 

**Rationale**: Annualizing would multiply quarterly income by 4, making totals 4x larger than actual. Since we're summing quarterly values directly, the sum already represents the total income over the time period.

**Implementation pattern**:
```python
# Convert to real values (adjust for inflation)
baseline_job_real_q = baseline_job_q / baseline_inflation
baseline_ss_user_real_q = baseline_ss_user_q / baseline_inflation

# Sum quarterly values directly (no annualization - each interval is already quarterly income)
baseline_job_total = baseline_job_real_q[mask].sum()
baseline_ss_total = baseline_ss_user_real_q.sum()
```

**Note**: The only place where annual income is needed is for the benefit percentage calculation, which uses `get_current_annual_income()` that extracts the annualized starting income from the first income profile (which is already annualized in the config).

### Helper Functions for DRY Principles

To follow DRY (Don't Repeat Yourself) principles, the notebook uses a `RealFinancialData` class to encapsulate repeated calculations for extracting, converting, and processing income streams from simulation results.

**`RealFinancialData` class**:
- **Initialization**: Takes a simulation results DataFrame and automatically:
  - Extracts income streams and tax columns (Job Income, SS User, SS Partner, Pension, Income Taxes, Medicare Taxes)
  - Converts all values from nominal to real (inflation-adjusted) by dividing by the inflation column
  - Stores dates for filtering operations
- **Properties**:
  - `post_tax_income`: Calculates post-tax income as (Job + SS User + SS Partner + Pension) + (Income Taxes + Medicare Taxes). Note: Taxes are already negative in the DataFrame, so addition is correct.
  - `post_tax_total_lifetime`: Sum of post-tax income over all intervals
  - `pre_tax_job_total_lifetime`: Sum of job income over all intervals
  - `pre_tax_ss_total_lifetime`: Sum of Social Security (user + partner) over all intervals
  - `pre_tax_pension_total_lifetime`: Sum of pension over all intervals
  - `pre_tax_total_lifetime`: Sum of all pre-tax income components
  - `dates`: Date series for filtering operations
  - Individual real income series: `job_real_q`, `ss_user_real_q`, `ss_partner_real_q`, `pension_real_q`, `income_taxes_real_q`, `medicare_taxes_real_q`
- **Methods**:
  - `get_coverage_results(coverage_percentage, coverage_duration_years, benefit_cutoff_date)`: Calculates existing coverage replacement (net after taxes). Returns a `CoverageResults` dataclass containing `gross_benefits`, `taxes`, and `total_net_replacement`. Coverage end date is capped at `benefit_cutoff_date` using `min(coverage_start + coverage_duration_years, benefit_cutoff_date)`. Coverage percentage is capped at 100% for calculation. Uses average tax rate from baseline scenario for covered intervals: `(total income taxes + total Medicare taxes) / total income` for the coverage period.

**Usage pattern**:
```python
baseline = RealFinancialData(baseline_df)
disability = RealFinancialData(disability_df)
total_replacement_needs = baseline.post_tax_total_lifetime - disability.post_tax_total_lifetime

# Calculate existing coverage
benefit_cutoff_date = BENEFIT_CUTOFF_AGE - user_config.age + TODAY_YR_QT
coverage_results = baseline.get_coverage_results(
    coverage_percentage, coverage_duration_years, benefit_cutoff_date
)
existing_coverage = coverage_results.total_net_replacement
```

This class-based approach is used consistently across baseline, disability, and partner disability scenarios to eliminate code duplication and ensure consistent calculations.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Gates:**
- [x] All code will include type hints for public functions and classes
- [x] Code will pass pylint with minimum score of 8.0/10.0
- [x] All modules will include module-level docstrings
- [x] All public classes and functions will include docstrings
- [x] No circular dependencies will be introduced (standalone notebook)

**Testing Gates:**
- [x] Test coverage plan achieves minimum 80% (95%+ for financial calculations) for application code (simulator and Flask app)
- [x] Tests will use pytest framework with proper fixtures
- [x] Integration tests planned for API endpoints
- [x] Test performance targets defined (<1s unit, <10s integration)
- [x] If feature includes standalone scripts/notebooks: Exception documented per constitution Testing Standards
  - **Exception applies**: This is a standalone Jupyter notebook used for one-off calculations, not integrated into the application. Testing requirements are exempted per constitution Testing Standards.

**User Experience Gates:**
- [x] API endpoints follow consistent naming conventions (N/A - no API)
- [x] Error messages will be clear and actionable (notebook will display clear error messages)
- [x] Response time targets defined (<2s for interactive endpoints) (N/A - notebook execution)
- [x] Configuration validation planned (config validation handled by existing system)

**Performance Gates:**
- [x] Performance benchmarks defined for simulation operations (complete in under 2 minutes)
- [x] Profiling strategy identified for critical paths (N/A - standalone script)
- [x] Memory usage constraints considered (uses existing SimulationEngine, bounded)
- [x] Scalability considerations documented (single-user calculations)

## Project Structure

### Documentation (this feature)

```text
specs/001-disability-insurance-calculator/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
standalone_tools/
└── disability_insurance_calculator.ipynb  # Jupyter notebook for disability insurance calculations
```

**Structure Decision**: Single standalone Jupyter notebook in `/standalone_tools` directory, following the pattern established by `tpaw_planner.ipynb`. The notebook will use SimulationEngine to run baseline and disability scenarios, then calculate coverage gaps.

## Phase 0: Research Complete

**Status**: ✅ Complete  
**Output**: `research.md`

All technical questions resolved:
- ✅ How to use SimulationEngine for baseline vs disability scenarios
- ✅ How to extract income streams and Social Security from results
- ✅ How to handle post-Benefit cutoff age income reductions
- ✅ How to calculate existing coverage replacement with taxes
- ✅ How to calculate coverage gap and benefit percentage
- ✅ How to handle edge cases

## Phase 1: Design Complete

**Status**: ✅ Complete  
**Outputs**: 
- ✅ `data-model.md` - Data structures and transformations
- ✅ `quickstart.md` - User guide for the notebook

**Key Design Decisions**:
1. **Architecture**: Standalone Jupyter notebook using SimulationEngine (not individual controllers)
2. **Location**: `/standalone_tools/disability_insurance_calculator.ipynb`
3. **Approach**: Use single SimulationEngine instance, modify `engine._user_config.income_profiles` directly (following `tpaw_planner.ipynb` pattern), run baseline then disability scenarios
4. **Output**: Structured text results with periodic sanity check outputs

**Contracts**: N/A - No API contracts needed for standalone notebook

## Phase 2: Implementation Ready

**Status**: Ready for `/speckit.tasks`

The plan is complete and ready for task breakdown. Key implementation steps:
1. Create `/standalone_tools` directory
2. Create Jupyter notebook following `tpaw_planner.ipynb` pattern
3. **CRITICAL**: Implement workspace root path handling and Flask initialization skipping in imports cell (see Implementation Learnings section)
4. Implement config loading and validation
5. Implement Benefit cutoff age configuration (configurable in script, default value is 65)
6. Implement `set_fixed_inflation()` helper function (following `tpaw_planner.ipynb` pattern) to set deterministic inflation rate
7. Implement helper functions for DRY principles to eliminate repeated calculations
8. Implement baseline scenario (SimulationEngine with `config_path`, set fixed inflation, run `gen_all_trials()`, use helper functions to extract and process income streams)
9. Implement disability scenario (modify `engine._user_config.income_profiles` directly to zero job income, clear results, run `gen_all_trials()` again - fixed inflation already set, use helper functions to extract and process income streams)
10. Implement income comparison and gap calculation (including post-Benefit cutoff age income reductions, using post-tax income values)
11. Implement coverage replacement calculation with taxes
12. Implement structured output formatting
13. Add periodic sanity check outputs throughout notebook

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all gates pass with appropriate exceptions documented.

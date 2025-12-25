# Implementation Plan: Total Portfolio Allocation Strategy

**Branch**: `002-total-portfolio-allocation` | **Date**: 2025-12-21 | **Spec**: `/specs/002-total-portfolio-allocation/spec.md`
**Input**: Feature specification from `/specs/002-total-portfolio-allocation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add the ability for users to configure a total portfolio allocation strategy where allocation is determined by relative risk aversion and total portfolio value (current savings + present value of future income). The strategy uses the Merton Share formula to interpolate between user-defined high-risk and low-risk allocations based on total portfolio value and risk aversion. Present value of future income is calculated using `numpy-financial.npv()` with discount rates derived from the weighted average return of assets in the low-risk allocation. The strategy integrates with the existing allocation framework by extending the `_Strategy` abstract base class and updating the `Controller` to pass the `Controllers` object for accessing income, social security, and pension controllers.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: 
- `numpy`: Array operations and numerical calculations
- `numpy-financial`: Present value calculations (`npf.npv()`)
- `pydantic`: Configuration validation
- Existing controllers: `job_income`, `social_security`, `pension`, `economic_data`

**Storage**: N/A (in-memory calculations, reads from `variable_statistics.csv` for asset statistics)  
**Testing**: pytest framework with reusable, domain-aligned fixtures and factories from `conftest.py` (e.g., shared asset statistics, controller factories, and canonical CSV-backed data)  
**Target Platform**: Linux server (Python application)  
**Project Type**: Single project (simulator application)  
**Performance Goals**: 
- Allocation calculation: <1ms per interval
- Present value calculation: <10ms per interval
- Strategy initialization: <10ms (one-time cost)

**Constraints**: 
- Must maintain backward compatibility with existing allocation strategies (`flat`, `net_worth_pivot`)
- Must pass Ruff linting, Ruff formatting, and Pyright type checking
- Test coverage: 80% minimum, 95%+ for financial calculations
- All allocations must sum to 1.0, all assets must be in `ALLOWED_ASSETS`

**Scale/Scope**: 
- New strategy class: `_TotalPortfolioStrategy` (dataclass)
- New config class: `TotalPortfolioStrategyConfig` (Pydantic model)
- Modification to `_Strategy` abstract base class: add optional `controllers` parameter
- Modification to `Controller.gen_allocation()`: pass `Controllers` object to strategy
- Modification to `AllocationOptions`: add `total_portfolio` attribute
- Integration with existing controllers: `job_income`, `social_security`, `pension`
- New validation in `User` config to disallow net-worth-based social security/pension strategies when `TotalPortfolioStrategy` is chosen, to avoid circular dependencies
- Precomputation of future job income and benefit income (social security + pension) arrays in `_TotalPortfolioStrategy.__post_init__` using fake `State` objects that prevent access to `state.net_worth`, with `gen_allocation()` reusing these arrays for NPV

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Gates:**
- [x] All code will include type hints for public functions and classes
- [x] Code will pass Ruff linting checks as configured in pyproject.toml
- [x] Code will pass Ruff formatting checks
- [x] Code will pass Pyright type checking as configured in pyrightconfig.json
- [x] All modules will include module-level docstrings
- [x] All public classes and functions will include docstrings
- [x] No circular dependencies will be introduced
- [x] Object models (classes, dataclasses, TypedDict, Pydantic) will be used instead of plain dictionaries for type safety
- [x] Function calls will use named arguments (except single obvious argument cases)

**Testing Gates:**
- [x] Test-Driven Development (TDD) will be used: tests written before implementation for all application code
- [x] Test coverage plan achieves minimum 80% (95%+ for financial calculations) for application code (simulator and Flask app)
- [x] Tests will use pytest framework with proper, reusable fixtures and factories (including shared domain fixtures such as asset statistics and controller factories)
- [x] Tests will be designed to be data-driven where feasible, deriving expectations from shared fixtures, canonical CSV data, or domain objects instead of hard-coded magic numbers
- [x] Integration tests planned for API endpoints (N/A - no new API endpoints)
- [x] Test performance targets defined (<1s unit, <10s integration)
- [x] If feature includes standalone scripts/notebooks: Exception documented per constitution Testing Standards (N/A - no standalone scripts/notebooks)

**User Experience Gates:**
- [x] API endpoints follow consistent naming conventions (N/A - no new API endpoints)
- [x] Error messages will be clear and actionable (ValueError with descriptive messages)
- [x] Response time targets defined (<2s for interactive endpoints) (N/A - no API endpoints)
- [x] Configuration validation planned (Pydantic validation with clear error messages)

**Performance Gates:**
- [x] Performance benchmarks defined for simulation operations (<1ms allocation, <10ms PV calculation)
- [x] Profiling strategy identified for critical paths (allocation and PV calculations)
- [x] Memory usage constraints considered (in-memory calculations, bounded by simulation intervals)
- [x] Scalability considerations documented (efficient array operations, no external dependencies)

## Project Structure

### Documentation (this feature)

```text
specs/002-total-portfolio-allocation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) - COMPLETE
├── data-model.md        # Phase 1 output (/speckit.plan command) - COMPLETE
├── quickstart.md        # Phase 1 output (/speckit.plan command) - COMPLETE
├── contracts/           # Phase 1 output (/speckit.plan command) - COMPLETE
│   └── README.md        # Internal API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── models/
│   ├── config/
│   │   └── portfolio.py          # Add TotalPortfolioStrategyConfig, update AllocationOptions
│   └── controllers/
│       ├── __init__.py            # Controllers dataclass (already exists)
│       └── allocation.py          # Add _TotalPortfolioStrategy, update _Strategy, Controller
├── data/
│   └── variable_statistics.csv    # Read for expected returns/stdev (already exists)
└── util.py                        # interval_yield() helper (already exists)

tests/
├── models/
│   ├── config/
│   │   └── test_portfolio.py      # Test TotalPortfolioStrategyConfig validation
│   └── controllers/
│       └── test_allocation.py     # Test _TotalPortfolioStrategy, edge cases
└── integration/
    └── test_total_portfolio_strategy.py  # Integration tests with full simulation
```

**Structure Decision**: Single project structure. New code integrates into existing `app/models/config/portfolio.py` (configuration) and `app/models/controllers/allocation.py` (strategy implementation). Tests follow existing structure under `tests/models/`. No new API endpoints or external services required.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. All constitution gates pass. Implementation follows existing patterns and maintains backward compatibility.

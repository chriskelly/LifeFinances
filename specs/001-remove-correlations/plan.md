# Implementation Plan: Remove Variable Correlations from Economic Data Generation

**Branch**: `001-remove-correlations` | **Date**: 2025-12-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-remove-correlations/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Remove all correlation functionality from economic data generation. The system will generate independent variable data using univariate normal distribution per variable (based on mean yield and standard deviation from variable_statistics.csv). All correlation-related code, data files, and tests will be removed. The function `_gen_covariated_data` will be renamed to `_gen_variable_data` and modified to use univariate normal distribution instead of multivariate normal distribution with covariance matrix.

## Technical Context

**Language/Version**: Python 3.10.19  
**Primary Dependencies**: numpy (1.26.1), Flask (3.0.0), pandas (2.1.2), pydantic (2.4.2), PyYAML (6.0.1)  
**Storage**: CSV files (variable_statistics.csv), no database  
**Testing**: pytest framework with fixtures  
**Target Platform**: Linux server (Docker container)  
**Project Type**: Single web application (Flask backend)  
**Performance Goals**: Economic data generation completes in equivalent or better time compared to previous correlated version; <100ms per trial for standard configurations  
**Constraints**: API endpoints must respond within 2 seconds  
**Scale/Scope**: Internal simulation tool; handles multiple trials with configurable intervals per trial

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Gates:**
- [x] All code will include type hints for public functions and classes (existing code already has type hints; modifications will maintain this)
- [x] Code will pass pylint with minimum score of 8.0/10.0 (refactoring maintains existing code quality standards)
- [x] All modules will include module-level docstrings (existing module has docstring; will update if needed)
- [x] All public classes and functions will include docstrings (existing code has docstrings; modifications will maintain this)
- [x] No circular dependencies will be introduced (removing code reduces dependencies)
- [x] Object models (classes, dataclasses, TypedDict, Pydantic) will be used instead of plain dictionaries for type safety (existing code uses dataclasses; no changes needed)
- [x] Function calls will use named arguments (except single obvious argument cases) (will follow existing patterns and use named arguments)

**Testing Gates:**
- [x] Test-Driven Development (TDD) will be used: tests written before implementation for all application code (spec requires TDD per TR-001)
- [x] Test coverage plan achieves minimum 80% (95%+ for financial calculations) for application code (spec requires 80% overall, 95%+ for financial calculations per TR-002)
- [x] Tests will use pytest framework with proper fixtures (existing tests use pytest; will maintain this)
- [x] Integration tests planned for API endpoints (existing integration tests will be updated; no new endpoints)
- [x] Test performance targets defined (<1s unit, <10s integration) (spec defines <1s unit, <10s integration per TR-004, TR-005)
- [x] If feature includes standalone scripts/notebooks: Exception documented per constitution Testing Standards (N/A - no standalone scripts/notebooks in this feature)

**User Experience Gates:**
- [x] API endpoints follow consistent naming conventions (no API changes; existing endpoints remain unchanged)
- [x] Error messages will be clear and actionable (edge cases specify graceful error handling)
- [x] Response time targets defined (<2s for interactive endpoints) (spec defines <2s per PR-001)
- [x] Configuration validation planned (no configuration changes; existing validation remains)

**Performance Gates:**
- [x] Performance benchmarks defined for simulation operations (spec requires equivalent or better performance per PR-002)
- [x] Profiling strategy identified for critical paths (spec requires profiling before merge per PR-004)
- [x] Memory usage constraints considered (removing correlation matrices may reduce memory usage per PR-003)
- [x] Scalability considerations documented (internal tool; no scalability changes needed)

## Project Structure

### Documentation (this feature)

```text
specs/001-remove-correlations/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── models/
│   └── controllers/
│       └── economic_data.py    # Main file to modify
├── data/
│   ├── constants.py            # Remove CORRELATION_PATH constant
│   └── variable_correlation.csv # File to delete
└── routes/                     # No changes needed

tests/
├── models/
│   └── controllers/
│       ├── test_economic_data.py                    # Update tests
│       └── test_csv_variable_mix_repo_correlation.csv # File to delete
└── sample_configs/            # No changes needed
```

**Structure Decision**: Single project structure. This is a refactoring feature that modifies existing code in `app/models/controllers/economic_data.py` and removes correlation-related files. No new modules or major structural changes are needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - all constitution gates pass. This is a straightforward refactoring that simplifies the codebase by removing correlation functionality.

## Phase 0: Research Complete

**Status**: ✅ Complete

**Artifacts Generated**:
- `research.md` - Technical decisions and implementation approach documented

**Key Decisions**:
1. Use univariate normal distribution per variable (independent generation)
2. Rename `_gen_covariated_data` to `_gen_variable_data`
3. Remove `correlation_matrix` from `VariableMix` dataclass
4. Use `np.random.default_rng()` for random number generation

## Phase 1: Design & Contracts Complete

**Status**: ✅ Complete

**Artifacts Generated**:
- `data-model.md` - Entity structures, relationships, and validation rules
- `contracts/README.md` - API contract documentation (no API changes)
- `quickstart.md` - Developer quickstart guide

**Key Design Elements**:
- Data model changes: removed `correlation_matrix` attribute, removed `correlation_path` parameter
- No API contract changes: all external interfaces remain unchanged

**Agent Context Updated**:
- Cursor IDE context file updated with Python 3.10.19, numpy, Flask, pandas, pydantic, PyYAML

## Next Steps

**Phase 2**: Task breakdown via `/speckit.tasks` command (not part of `/speckit.plan`)

The planning phase is complete. All research, design, and contract documentation has been generated. The feature is ready for task breakdown and implementation.

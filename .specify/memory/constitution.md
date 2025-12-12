<!--
Sync Impact Report:
Version: 1.1.0 → 1.2.0
Type: New principles added + Testing Standards clarification (MINOR)
Modified principles:
  - Code Quality Standards: Added object models over dictionaries principle, added named arguments principle
  - Testing Standards: Clarified exception for standalone scripts/notebooks, added TDD requirement
Added sections: None
Removed sections: None
Templates requiring updates:
  - ✅ updated: .specify/templates/spec-template.md (Testing Requirements section includes exception note)
  - ✅ updated: .specify/templates/plan-template.md (Testing Gates section includes exception note, Code Quality Gates updated)
  - ✅ updated: .specify/templates/tasks-template.md (Test tasks include exception note and TDD guidance)
Follow-up TODOs: None
-->

# LifeFInances Project Constitution

**Version:** 1.2.0  
**Ratification Date:** 2025-12-10  
**Last Amended:** 2025-12-12

## Purpose

This constitution establishes the non-negotiable principles governing the LifeFInances project. All code contributions, architectural decisions, and development practices MUST align with these principles. Violations require explicit justification and constitutional amendment.

## Principles

### Code Quality Standards

**All code MUST maintain high quality standards through static analysis, type safety, and documentation.**

- **Static Analysis Compliance**: All Python code MUST pass pylint with a minimum score of 8.0/10.0. Code MUST be formatted consistently using project-standard tools (isort, black if adopted, or equivalent).

- **Type Safety**: All public functions, class methods, and module-level functions MUST include type hints. Internal helper functions SHOULD include type hints unless doing so would significantly reduce readability. Type checking MUST pass via pyright or mypy as configured in `pyrightconfig.json`.

- **Documentation Requirements**: All modules MUST include module-level docstrings. All public classes and functions MUST include docstrings following Google or NumPy style conventions. Complex algorithms or business logic MUST include inline comments explaining non-obvious decisions.

- **Code Organization**: Code MUST follow the established project structure (app/, tests/, requirements/). Related functionality MUST be grouped logically. Circular dependencies MUST be avoided. Import statements MUST be organized (stdlib, third-party, local) and unused imports MUST be removed.

- **Object Models Over Dictionaries**: Code MUST favor creating object models (classes, dataclasses, TypedDict, Pydantic models) rather than plain dictionaries for type safety. Dictionaries SHOULD only be used when object models would add unnecessary complexity or when interfacing with external APIs that require dictionary formats. Rationale: Object models provide compile-time type checking, better IDE support, and clearer contracts.

- **Named Function Arguments**: Function calls MUST use named arguments unless there is exactly one obvious argument where positional calling is unambiguous. Functions with multiple parameters MUST be called with named arguments to improve readability and reduce errors. Rationale: Named arguments make code self-documenting and prevent argument order mistakes.

- **Error Handling**: All user-facing code paths MUST handle expected error conditions gracefully. Exceptions MUST include meaningful error messages. Critical errors MUST be logged appropriately. Broad exception catching (except Exception) MUST be justified with comments when used.

### Testing Standards

**All functionality related to the application (simulator and Flask app) MUST be covered by automated tests that validate correctness, edge cases, and integration points. Testing requirements remain strict for application code, with exceptions only for standalone scripts/notebooks not used as application inputs.**

- **Test-Driven Development**: Where tests are required (all application code), Test-Driven Development (TDD) MUST be used. Tests MUST be written before implementation code. The TDD cycle (Red-Green-Refactor) MUST be followed: write failing tests first, implement minimal code to pass, then refactor. Rationale: TDD ensures testability, drives better design, and prevents untested code from being merged.

- **Test Coverage**: All new code in the application (simulator and Flask app) MUST include corresponding tests. Test coverage MUST maintain a minimum of 80% for all modules. Critical business logic (financial calculations, state transitions, simulation logic) MUST achieve 95%+ coverage.

- **Exception for Standalone Scripts/Notebooks**: Scripts and notebooks that are standalone tools and NOT used as inputs for the application (simulator or Flask app) MAY be exempted from testing requirements. This exception applies only to:
  - Standalone analysis scripts that do not feed data or logic into the application
  - Jupyter notebooks used for exploration or one-off calculations that are not imported or executed by the application
  - Utility scripts that are explicitly documented as experimental or exploratory and are not dependencies of the simulator or Flask app
  - Scripts that are not imported, executed, or referenced by any application code (simulator or Flask app)
  
  **Note**: If a script or notebook is used as input, imported, executed, or referenced by the application, it MUST follow all testing requirements including TDD.

- **Test Structure**: Tests MUST use pytest as the testing framework. Test files MUST mirror the source code structure under `tests/`. Test functions MUST have descriptive names following `test_<functionality>` or `test_<scenario>` patterns. Test classes MUST follow `Test<ClassName>` naming.

- **Test Quality**: Tests MUST be independent and executable in any order. Tests MUST use fixtures from `conftest.py` for shared setup. Tests MUST clean up after themselves (no persistent side effects). Tests MUST validate both success and failure cases.

- **Integration Testing**: API endpoints MUST have integration tests verifying HTTP status codes, response formats, and error handling. Simulation engine MUST be tested with multiple configuration scenarios. Data loading and transformation MUST be tested with sample data files.

- **Test Performance**: Unit tests MUST complete in under 1 second per test. Integration tests MUST complete in under 10 seconds per test. Slow tests MUST be marked with `@pytest.mark.slow` and excluded from default test runs. Test suites MUST complete in under 5 minutes total.

### User Experience Consistency

**All user-facing interfaces MUST provide consistent, predictable, and intuitive experiences across the application.**

- **API Consistency**: All REST API endpoints MUST follow consistent naming conventions (snake_case for Python, kebab-case for URLs). Response formats MUST be consistent (JSON structure, error message format, status codes). API versioning MUST be implemented when breaking changes are introduced.

- **Error Messages**: All user-facing error messages MUST be clear, actionable, and non-technical when possible. Error responses MUST include appropriate HTTP status codes. Validation errors MUST identify specific fields and provide guidance on correction.

- **Response Times**: Interactive API endpoints MUST respond within 2 seconds under normal load. Long-running operations (simulations) MUST provide progress indicators or asynchronous processing with status endpoints. Timeout errors MUST be handled gracefully with informative messages.

- **Configuration Validation**: User configuration files (config.yml) MUST be validated on load with clear error messages for invalid values. Default values MUST be provided where appropriate. Configuration schema MUST be documented.

### Performance Requirements

**The application MUST meet performance benchmarks and be optimized for production workloads.**

- **Simulation Performance**: Single simulation trials MUST complete within reasonable time bounds (target: <100ms per trial for standard configurations). Simulation engines MUST support parallel execution where applicable. Memory usage MUST be bounded and monitored.

- **API Performance**: API endpoints MUST handle concurrent requests without degradation. Database queries (if applicable) MUST be optimized and avoid N+1 problems. Caching MUST be implemented for expensive computations or frequently accessed data.

- **Profiling and Monitoring**: Performance-critical code paths MUST be profiled using cProfile or equivalent tools. Profiling results MUST be reviewed before merging performance-sensitive changes. Memory leaks MUST be identified and resolved.

- **Resource Efficiency**: The application MUST operate within reasonable memory constraints. Large datasets MUST be processed incrementally or streamed when possible. Unnecessary data loading or computation MUST be avoided.

## Governance

### Amendment Procedure

Constitutional amendments require:

1. **Proposal**: A detailed proposal describing the principle change, rationale, and impact assessment.
2. **Review**: Review by project maintainers with consideration of backward compatibility and migration paths.
3. **Version Update**: Semantic versioning update (MAJOR.MINOR.PATCH) based on change impact:
   - **MAJOR**: Backward-incompatible principle changes, removal of principles, or fundamental redefinitions.
   - **MINOR**: Addition of new principles or significant expansion of existing guidance.
   - **PATCH**: Clarifications, wording improvements, typo fixes, or non-semantic refinements.
4. **Documentation**: Update of all dependent templates and documentation to reflect changes.
5. **Communication**: Clear communication of changes to all contributors.

### Compliance Review

- All pull requests MUST be reviewed for constitutional compliance before merging.
- Automated checks (linting, type checking, tests) MUST pass as a minimum compliance threshold.
- Manual review MUST verify adherence to principles not covered by automation.
- Violations MUST be addressed before merge approval unless explicitly exempted via constitutional amendment.

### Version History

- **1.2.0** (2025-12-12): Added principles for object models over dictionaries, named function arguments, and test-driven development. Clarified testing exception applies only to scripts/notebooks not used as application inputs. Testing requirements remain strict for all application code (simulator and Flask app).

- **1.1.0** (2025-12-10): Added exception to testing requirements for standalone scripts/notebooks not used as application inputs. Testing standards remain strict for simulator and Flask app functionality.

- **1.0.0** (2025-12-10): Initial constitution establishing code quality, testing, UX consistency, and performance principles.

# Testing Guide for LifeFinances

This document explains how to run tests locally before pushing to ensure your changes pass CI.

## Quick Test Before Push

To verify your changes will pass CI, run:

```bash
make test
make lint
```

Or run them together:
```bash
make all
```

This will:
1. Run all unit and integration tests
2. Run ruff linting checks
3. Run ruff format checks
4. Run pyright type checking

## Running Tests Locally

### Standard Tests (Unit + Integration)

Run all standard tests:
```bash
pytest tests/
```

Or use the Makefile (recommended):
```bash
make test
```

This runs the same tests that run in CI, **excluding E2E tests** which require additional setup.

### Specific Test Categories

Run specific test modules:
```bash
# Route tests
pytest tests/test_routes.py -v

# Config model tests
pytest tests/models/test_config.py -v

# Simulator tests
pytest tests/models/test_simulator.py -v

# All model tests
pytest tests/models/ -v
```

### Linting

Run linting checks (same as CI):
```bash
make lint
```

This runs:
- `ruff check .` - Code quality checks
- `ruff format --check .` - Format checks
- `pyright` - Type checking

To auto-fix ruff issues:
```bash
python -m ruff check . --fix
python -m ruff format .
```

## End-to-End (E2E) Tests

E2E tests are **NOT included in `make test`** because they:
- Require selenium dependencies (`pip install -r requirements-e2e.txt`)
- Need a running Flask application
- Take longer to run

### Running E2E Tests

1. Install E2E dependencies:
   ```bash
   pip install -r requirements-e2e.txt
   ```

2. Start the Flask app in a separate terminal:
   ```bash
   python -m flask --app app run
   ```

3. Run E2E tests:
   ```bash
   pytest tests/e2e/ -v
   ```

See [tests/e2e/README.md](tests/e2e/README.md) for detailed E2E testing documentation.

## Understanding Test Results

### All Tests Pass ✅
```
====================== 120 passed in 2.88s ======================
```
Your changes are ready to push!

### Some Tests Fail ❌
```
====================== 5 failed, 115 passed in 3.21s ======================
```
Fix the failing tests before pushing. Review the error output to understand what broke.

### Linting Errors ⚠️
```
Found 3 errors.
app/routes/config.py:5:1: I001 Import block is un-sorted
```
Run `python -m ruff check . --fix` to auto-fix most issues.

## CI Environment

The CI environment (Docker) runs:
1. `make test` - All standard tests (excludes E2E)
2. `make lint` - All linting checks

**Important**: E2E tests are excluded from CI because the Docker environment doesn't have selenium installed. This is by design - E2E tests are for local GUI validation.

## Common Issues

### "ModuleNotFoundError: No module named 'selenium'"

This is expected if you haven't installed E2E dependencies. E2E tests are excluded from default test runs.

**Solution**: Either:
- Ignore it (E2E tests aren't required for CI)
- Install E2E dependencies: `pip install -r requirements-e2e.txt`

### Tests pass locally but fail in CI

**Possible causes**:
1. You're using local dependencies not in requirements
2. Environment-specific paths (use relative paths)
3. Tests depend on local state (ensure tests are independent)

**Debug steps**:
1. Run `make test` locally (uses same config as CI)
2. Check if you added new dependencies
3. Verify tests don't rely on local files

### Linting passes locally but fails in CI

Make sure you're using the project's ruff version:
```bash
pip install ruff
python -m ruff check .
```

## Test Configuration

- **pytest.ini**: Pytest configuration, excludes `tests/e2e/` from default runs
- **pyproject.toml**: Ruff configuration for linting
- **Makefile**: CI commands and test targets
- **requirements-e2e.txt**: Optional E2E testing dependencies

## Best Practices

1. **Always run `make test` before pushing** - Catches issues early
2. **Run `make lint` to check code quality** - Ensures consistent style
3. **Write tests for new features** - Helps prevent regressions
4. **Keep tests independent** - Don't rely on test execution order
5. **Use fixtures for common setup** - Reduces code duplication

## Need Help?

- Standard tests: See test files in `tests/` directory
- E2E tests: See [tests/e2e/README.md](tests/e2e/README.md)
- Linting: See [pyproject.toml](pyproject.toml) for ruff configuration
- CI: See [Makefile](Makefile) for CI commands

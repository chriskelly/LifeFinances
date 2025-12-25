# End-to-End (E2E) Testing for LifeFinances GUI

This directory contains end-to-end tests for the LifeFinances Flask GUI using Selenium WebDriver.

## Important: E2E Tests are Excluded from Default Test Runs

**E2E tests are NOT run by default** when executing `pytest tests/` or `make test`. This is intentional because:
- E2E tests require additional dependencies (selenium, ChromeDriver)
- E2E tests need a running Flask application
- CI/CD environments may not have browser automation capabilities

To run E2E tests, you must **explicitly** specify the e2e directory:
```bash
pytest tests/e2e/
```

## Overview

The E2E test suite validates the complete user workflows through the web interface, including:
- Navigation between pages
- Configuration management (create, edit, save)
- Simulation execution
- Results visualization and interactivity
- Dashboard functionality
- Session persistence
- Error handling and validation

## Test Structure

```
tests/e2e/
├── conftest.py                 # Pytest configuration and shared fixtures
├── page_objects/               # Page Object Model classes
│   ├── base_page.py           # Base class for all page objects
│   ├── dashboard_page.py      # Dashboard page object
│   ├── config_page.py         # Configuration page object
│   ├── run_page.py            # Run simulation page object
│   └── results_page.py        # Results page object
└── test_suites/               # Test suites organized by functionality
    ├── test_navigation.py     # Navigation tests
    ├── test_configuration.py  # Config management tests
    ├── test_simulation.py     # Simulation execution tests
    ├── test_results.py        # Results visualization tests
    ├── test_dashboard.py      # Dashboard functionality tests
    ├── test_session.py        # Session persistence tests
    └── test_error_handling.py # Error handling tests
```

## Installation

### 1. Install E2E Testing Dependencies

```bash
pip install -r requirements-e2e.txt
```

This installs:
- `selenium` - Browser automation
- `pytest-selenium` - Pytest integration for Selenium
- `webdriver-manager` - Automatic ChromeDriver management
- `pytest-xdist` - Parallel test execution (optional)
- `pytest-html` - HTML test reports (optional)

### 2. Ensure Chrome Browser is Installed

The tests use Chrome/Chromium. Make sure you have Chrome installed on your system.

## Running Tests

### Prerequisites

**IMPORTANT**: The Flask application must be running before executing E2E tests.

Start the Flask app in a separate terminal:

```bash
python -m flask --app app run
```

Or if using the GUI entry point:

```bash
python gui.py
```

The app should be accessible at `http://localhost:5000`.

### Run All E2E Tests

```bash
# From project root
pytest tests/e2e/ -v
```

### Run Specific Test Suites

```bash
# Navigation tests only
pytest tests/e2e/test_suites/test_navigation.py -v

# Configuration tests only
pytest tests/e2e/test_suites/test_configuration.py -v

# Simulation tests only
pytest tests/e2e/test_suites/test_simulation.py -v

# Results tests only
pytest tests/e2e/test_suites/test_results.py -v
```

### Run by Test Markers

```bash
# Run only smoke tests (quick validation)
pytest tests/e2e/ -m smoke -v

# Run navigation tests
pytest tests/e2e/ -m navigation -v

# Run configuration tests
pytest tests/e2e/ -m config -v

# Run simulation tests
pytest tests/e2e/ -m simulation -v

# Run results tests
pytest tests/e2e/ -m results -v
```

### Headless Mode

Run tests in headless mode (no visible browser):

```bash
# Using environment variable
HEADLESS=1 pytest tests/e2e/ -v

# Or on Windows
set HEADLESS=1 && pytest tests/e2e/ -v
```

### Generate HTML Report

```bash
pytest tests/e2e/ --html=test-report.html --self-contained-html
```

## Configuration

### Environment Variables

- `E2E_BASE_URL` - Base URL of the Flask app (default: `http://localhost:5000`)
- `HEADLESS` - Run tests in headless mode (set to any value to enable)
- `CI` - Automatically enables headless mode in CI environments

### Custom Base URL

```bash
E2E_BASE_URL=http://localhost:8080 pytest tests/e2e/ -v
```

## Test Development

### Page Object Model (POM)

All tests use the Page Object Model pattern for maintainability:

1. **Page Objects** - Located in `page_objects/`, these classes encapsulate page interactions
2. **Test Suites** - Located in `test_suites/`, these contain test logic using page objects

Example:

```python
def test_save_configuration(config_page, sample_config):
    """Test saving a valid configuration."""
    config_page.navigate()
    config_page.set_config_content(sample_config)
    config_page.click_save()
    assert "/config" in config_page.get_current_url()
```

### Adding New Tests

1. Determine which test suite file is appropriate
2. Use existing page objects or extend them with new methods
3. Add appropriate pytest markers (`@pytest.mark.e2e`, `@pytest.mark.category`)
4. Follow the existing test patterns

### Adding New Page Objects

1. Create a new file in `page_objects/`
2. Inherit from `BasePage`
3. Define locators as class attributes using tuples: `(By.ID, "element-id")`
4. Implement page-specific methods
5. Add fixture in `conftest.py`

## CI Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-e2e.txt

      - name: Start Flask app
        run: |
          python -m flask --app app run &
          sleep 5  # Wait for app to start

      - name: Run E2E tests
        run: pytest tests/e2e/ -v --html=report.html
        env:
          HEADLESS: 1

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: e2e-test-report
          path: report.html
```

## Test Coverage

The E2E test suite covers:

- ✅ **Navigation** (7 tests) - Page navigation, URL routing, breadcrumb trails
- ✅ **Configuration** (7 tests) - YAML editing, saving, persistence, validation
- ✅ **Simulation** (7 tests) - Running simulations, progress tracking, completion
- ✅ **Results** (11 tests) - Charts, tables, interactivity, export
- ✅ **Dashboard** (8 tests) - Stats, recent simulations, quick actions
- ✅ **Session** (7 tests) - Data persistence across navigation and reloads
- ✅ **Error Handling** (12 tests) - Invalid inputs, edge cases, error recovery

**Total: 59+ E2E test cases**

## Performance

- **Target Runtime**: < 5 minutes for full suite
- **Smoke Tests**: < 1 minute (marked with `@pytest.mark.smoke`)
- Tests run sequentially to avoid race conditions

## Troubleshooting

### ChromeDriver Issues

If you encounter ChromeDriver errors:

```bash
# Manually update ChromeDriver
pip install --upgrade webdriver-manager
```

### Flask App Not Running

Error: Connection refused or timeouts

**Solution**: Ensure Flask app is running on `http://localhost:5000` before running tests

### Tests Timing Out

If tests are timing out during simulation:

1. Check that the simulation completes successfully manually
2. Increase timeout in specific tests (default is 60 seconds for simulations)
3. Check server logs for errors

### Element Not Found Errors

If tests fail with element not found:

1. Check that page templates match the locators in page objects
2. Verify element IDs and classes in HTML templates
3. Run tests in non-headless mode to see what's happening

## Best Practices

1. **Always start with page object methods** - Don't use WebDriver directly in tests
2. **Use explicit waits** - Don't use `time.sleep()`, use WebDriverWait
3. **Keep tests independent** - Each test should be able to run in isolation
4. **Use meaningful assertions** - Assert on visible outcomes, not just URLs
5. **Clean up after tests** - Fixtures handle this automatically
6. **Mark tests appropriately** - Use pytest markers for organization

## Future Enhancements

- [ ] Visual regression testing (Percy/BackstopJS)
- [ ] Mobile/responsive testing
- [ ] Performance testing (page load times)
- [ ] Accessibility testing (axe-core)
- [ ] Cross-browser testing (Firefox, Safari)
- [ ] Parallel test execution
- [ ] Video recording of test runs

# GUI End-to-End Testing Specification

## Overview
This specification outlines a comprehensive end-to-end (E2E) testing strategy for the LifeFinances Flask web application using Selenium WebDriver. These tests will validate the full user workflow from configuration to results visualization.

## Goals
- Validate complete user workflows through the GUI
- Test interactive elements (buttons, forms, charts) that unit tests cannot verify
- Ensure JavaScript chart rendering works correctly
- Verify session persistence across page navigation
- Test error handling and edge cases in the browser environment

## Technology Stack
- **Selenium WebDriver**: Browser automation
- **pytest-selenium**: pytest integration for Selenium
- **webdriver-manager**: Automatic driver management (no manual downloads)
- **Chrome/Firefox**: Target browsers (headless mode for CI)

## Test Structure

### Directory Layout
```
tests/
├── e2e/
│   ├── __init__.py
│   ├── conftest.py              # Selenium fixtures and config
│   ├── test_navigation.py       # Navigation and routing tests
│   ├── test_configuration.py    # Config CRUD operations
│   ├── test_simulation.py       # Running simulations
│   ├── test_results.py          # Results page and charts
│   ├── test_dashboard.py        # Dashboard functionality
│   └── pages/                   # Page Object Model classes
│       ├── __init__.py
│       ├── base_page.py
│       ├── dashboard_page.py
│       ├── config_page.py
│       ├── run_page.py
│       └── results_page.py
```

## Test Scenarios

### 1. Navigation Tests (`test_navigation.py`)
**Purpose**: Verify routing and navigation between pages

#### Test Cases:
- `test_index_redirects_to_dashboard`: Verify root `/` redirects to `/dashboard`
- `test_navigation_bar_links`: Click each nav link and verify correct page loads
- `test_breadcrumb_navigation`: Test breadcrumb navigation if implemented
- `test_back_button_behavior`: Verify browser back button works correctly
- `test_404_handling`: Navigate to non-existent route and verify 404 page

**Acceptance Criteria**:
- All navigation links are clickable
- URLs match expected patterns
- Page titles update correctly
- No JavaScript errors in console

---

### 2. Configuration Tests (`test_configuration.py`)
**Purpose**: Test configuration CRUD operations

#### Test Cases:
- `test_config_page_loads_existing_config`: Verify YAML appears in textarea
- `test_save_configuration_updates_file`:
  - Edit YAML in textarea
  - Click "Save Configuration"
  - Verify page reloads with updated config
  - Verify config.yml file updated on disk
- `test_save_and_run_redirects_to_run_page`:
  - Edit config
  - Click "Save & Run Simulation"
  - Verify redirected to `/run`
  - Verify config was saved
- `test_invalid_yaml_shows_error`:
  - Enter invalid YAML
  - Click save
  - Verify error message appears
- `test_cancel_button_returns_to_dashboard`:
  - Click "Cancel"
  - Verify redirected to dashboard
- `test_configuration_validation_errors`:
  - Enter valid YAML but invalid config (e.g., negative age)
  - Verify Pydantic validation error shown

**Acceptance Criteria**:
- Form submission works
- Validation errors display clearly
- Config persists between page reloads
- No data loss on navigation

---

### 3. Simulation Execution Tests (`test_simulation.py`)
**Purpose**: Test running Monte Carlo simulations

#### Test Cases:
- `test_run_simulation_with_valid_config`:
  - Click "Run Simulation" button
  - Wait for simulation to complete (loading indicator)
  - Verify redirected to `/results`
  - Verify success message or results appear
- `test_run_simulation_without_config_shows_error`:
  - Delete config.yml
  - Navigate to `/run`
  - Verify error message
- `test_loading_indicator_appears_during_simulation`:
  - Start simulation
  - Verify loading overlay/spinner appears
  - Verify it disappears when complete
- `test_simulation_adds_to_history`:
  - Run simulation
  - Navigate to dashboard
  - Verify simulation appears in recent runs

**Acceptance Criteria**:
- Loading states work correctly
- Long-running simulations don't timeout
- Results persist in session
- Dashboard history updates

---

### 4. Results Page Tests (`test_results.py`)
**Purpose**: Test results visualization and chart interactions

#### Test Cases:
- `test_results_page_shows_gauge_chart`:
  - Run simulation
  - Navigate to `/results`
  - Wait for Plotly gauge chart to render
  - Verify chart element exists in DOM
- `test_variable_selector_changes_chart`:
  - Select different variable from dropdown
  - Verify chart updates with new data
  - Check X/Y axis labels change
- `test_chart_handles_negative_values`:
  - Select variable with negative values (e.g., "Spending")
  - Verify chart renders without fill-to-zero
  - Verify Y-axis scales correctly
- `test_log_scale_toggle`:
  - Click "Log" button
  - Verify chart switches to logarithmic scale
  - Click again to toggle back
  - Verify button state changes (outline vs filled)
- `test_maximize_chart_opens_fullscreen`:
  - Click maximize button
  - Verify modal opens
  - Verify chart renders in modal
  - Close modal and verify returns to normal view
- `test_chart_fullscreen_respects_current_variable_and_scale`:
  - Select variable and enable log scale
  - Click maximize
  - Verify fullscreen chart shows same variable and scale
- `test_no_results_shows_placeholder`:
  - Clear session
  - Navigate to `/results`
  - Verify "No Results Available" message
  - Verify "Run Simulation" button present
- `test_results_table_displays_data`:
  - Verify results table has correct columns
  - Verify data rows present
- `test_success_percentage_displays_correctly`:
  - Run simulation with known success rate
  - Verify gauge shows correct percentage
  - Test edge cases: 0%, 50%, 100%

**Acceptance Criteria**:
- All Plotly charts render without errors
- Interactive elements (dropdowns, buttons) work
- Chart updates happen smoothly
- Modal interactions work correctly
- Negative values display properly

---

### 5. Dashboard Tests (`test_dashboard.py`)
**Purpose**: Test dashboard statistics and quick actions

#### Test Cases:
- `test_dashboard_shows_statistics`:
  - Run simulation
  - Navigate to dashboard
  - Verify stats cards show correct counts
  - Verify latest success rate displays
- `test_recent_simulations_list`:
  - Run multiple simulations
  - Verify recent runs list shows up to 5 runs
  - Verify runs show timestamps and success rates
- `test_quick_action_buttons`:
  - Click "Run New Simulation"
  - Verify navigates to `/run`
  - Return to dashboard
  - Click "Edit Configuration"
  - Verify navigates to `/config`
- `test_dashboard_with_no_simulations`:
  - Clear session/history
  - Navigate to dashboard
  - Verify appropriate empty state messages
- `test_dashboard_session_persistence`:
  - Run simulation
  - Navigate away and back
  - Verify stats still display

**Acceptance Criteria**:
- All statistics are accurate
- Quick actions navigate correctly
- Empty states are user-friendly
- Session data persists

---

### 6. Session Management Tests (`test_session.py`)
**Purpose**: Test server-side session handling

#### Test Cases:
- `test_session_persists_across_pages`:
  - Run simulation
  - Navigate through all pages
  - Verify results still accessible
- `test_session_survives_page_refresh`:
  - Run simulation
  - Refresh `/results` page
  - Verify results still display
- `test_multiple_browser_tabs_share_session`:
  - Run simulation in one tab
  - Open new tab to `/results`
  - Verify results appear (same session)
- `test_session_isolation_between_browsers`:
  - Run simulation in Chrome
  - Open Firefox (different session)
  - Verify no results in Firefox

**Acceptance Criteria**:
- Sessions persist correctly
- Server-side session storage works
- No cookie overflow errors
- Session isolation works

---

### 7. Error Handling Tests (`test_error_handling.py`)
**Purpose**: Test graceful error handling

#### Test Cases:
- `test_javascript_errors_caught`:
  - Monitor browser console logs
  - Perform all actions
  - Verify no uncaught JavaScript errors
- `test_network_error_handling`:
  - Simulate slow network (if possible)
  - Verify loading states work
- `test_invalid_session_data_handling`:
  - Corrupt session data
  - Navigate to `/results`
  - Verify graceful error message
- `test_missing_plotly_cdn_fallback`:
  - Block Plotly CDN (if fallback exists)
  - Verify error message or fallback

**Acceptance Criteria**:
- No uncaught exceptions
- Error messages are user-friendly
- Application doesn't crash

---

### 8. Responsive Design Tests (`test_responsive.py`)
**Purpose**: Test responsive behavior (if needed)

#### Test Cases:
- `test_mobile_viewport_renders`:
  - Set viewport to mobile size
  - Navigate through pages
  - Verify layout doesn't break
- `test_chart_responsive_resize`:
  - Resize browser window
  - Verify charts resize correctly

---

## Page Object Model (POM)

### Why POM?
- **Maintainability**: UI changes only require updating page classes
- **Readability**: Tests read like user actions
- **Reusability**: Common actions shared across tests
- **Separation of Concerns**: Test logic separate from element selectors

### Base Page (`base_page.py`)
```python
class BasePage:
    """Base class for all page objects"""

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def navigate_to(self, path):
        self.driver.get(f"http://localhost:5000{path}")

    def find_element(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def click(self, locator):
        element = self.find_element(locator)
        element.click()

    def get_text(self, locator):
        return self.find_element(locator).text

    def check_no_js_errors(self):
        logs = self.driver.get_log('browser')
        errors = [log for log in logs if log['level'] == 'SEVERE']
        return errors
```

### Dashboard Page (`dashboard_page.py`)
```python
class DashboardPage(BasePage):
    # Locators
    STATS_CARD = (By.CLASS_NAME, "stats-card")
    RUN_SIMULATION_BTN = (By.LINK_TEXT, "Run New Simulation")
    EDIT_CONFIG_BTN = (By.LINK_TEXT, "Edit Configuration")
    RECENT_RUNS_LIST = (By.ID, "recent-simulations")

    def get_simulation_count(self):
        return self.get_text(self.STATS_CARD)

    def click_run_simulation(self):
        self.click(self.RUN_SIMULATION_BTN)

    def get_recent_runs(self):
        list_element = self.find_element(self.RECENT_RUNS_LIST)
        return list_element.find_elements(By.TAG_NAME, "li")
```

### Results Page (`results_page.py`)
```python
class ResultsPage(BasePage):
    # Locators
    GAUGE_CHART = (By.ID, "successGauge")
    VARIABLE_SELECTOR = (By.ID, "variableSelect")
    LOG_SCALE_BTN = (By.ID, "btnToggleLogScale")
    MAXIMIZE_BTN = (By.ID, "btnMaximizeChart")
    DYNAMIC_CHART = (By.ID, "dynamicChart")
    FULLSCREEN_MODAL = (By.ID, "chartModal")

    def wait_for_chart_render(self):
        # Wait for Plotly chart to render (checks for SVG element)
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#successGauge .plotly"))
        )

    def select_variable(self, variable_name):
        select = Select(self.find_element(self.VARIABLE_SELECTOR))
        select.select_by_visible_text(variable_name)
        time.sleep(0.5)  # Wait for chart update

    def toggle_log_scale(self):
        self.click(self.LOG_SCALE_BTN)

    def maximize_chart(self):
        self.click(self.MAXIMIZE_BTN)
        # Wait for modal animation
        self.wait.until(EC.visibility_of_element_located(self.FULLSCREEN_MODAL))

    def is_log_scale_active(self):
        btn = self.find_element(self.LOG_SCALE_BTN)
        return "btn-secondary" in btn.get_attribute("class")
```

---

## Configuration & Fixtures

### `conftest.py`
```python
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import subprocess
import time

@pytest.fixture(scope="session")
def flask_app():
    """Start Flask app for testing"""
    # Start Flask in a subprocess
    process = subprocess.Popen(
        ["python", "run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)  # Wait for app to start

    yield process

    # Cleanup
    process.terminate()
    process.wait()

@pytest.fixture(scope="function")
def driver(flask_app):
    """Create a Chrome driver instance"""
    options = Options()
    options.add_argument("--headless")  # Run headless in CI
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    # Enable browser logging
    options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)

    yield driver

    # Cleanup
    driver.quit()

@pytest.fixture(scope="function")
def clean_session(driver):
    """Clear session before each test"""
    driver.get("http://localhost:5000")
    driver.delete_all_cookies()
    # Also clear server-side session if API exists
    yield

@pytest.fixture
def sample_config():
    """Return sample valid configuration YAML"""
    return """
age: 30
trial_quantity: 10
portfolio:
  current_net_worth: 100000
  allocation_strategy:
    flat:
      chosen: true
      allocation:
        US_Stock: 0.6
        US_Bond: 0.4
spending:
  profiles:
    - yearly_amount: 50000
"""
```

---

## Running Tests

### Local Development
```bash
# Install dependencies
pip install pytest pytest-selenium selenium webdriver-manager

# Run all E2E tests
pytest tests/e2e/ -v

# Run specific test file
pytest tests/e2e/test_results.py -v

# Run with visible browser (not headless)
pytest tests/e2e/ -v --headless=false

# Run with screenshots on failure
pytest tests/e2e/ -v --screenshot=failure
```

### CI Integration (GitHub Actions)
```yaml
- name: Run E2E Tests
  run: |
    # Start Flask app in background
    python run.py &
    sleep 5

    # Run E2E tests
    pytest tests/e2e/ -v --headless

    # Upload screenshots on failure
  if: failure()
  uses: actions/upload-artifact@v3
  with:
    name: e2e-screenshots
    path: tests/e2e/screenshots/
```

---

## Best Practices

### 1. Use Explicit Waits
```python
# Good
wait.until(EC.element_to_be_clickable((By.ID, "submit-btn")))

# Bad
time.sleep(5)  # Arbitrary wait
```

### 2. Use Page Object Model
```python
# Good
dashboard = DashboardPage(driver)
dashboard.click_run_simulation()

# Bad
driver.find_element(By.LINK_TEXT, "Run New Simulation").click()
```

### 3. Take Screenshots on Failure
```python
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = item.funcargs.get('driver')
        if driver:
            driver.save_screenshot(f"screenshots/{item.name}.png")
```

### 4. Test Isolation
- Each test should be independent
- Use fixtures to ensure clean state
- Don't rely on test execution order

### 5. Meaningful Assertions
```python
# Good
assert "Configuration saved successfully" in page.get_success_message()

# Bad
assert True
```

---

## Dependencies

Add to `requirements/dev.txt`:
```
selenium>=4.15.0
pytest-selenium>=4.0.0
webdriver-manager>=4.0.0
```

---

## Success Metrics

### Coverage Goals
- [ ] 100% of user-facing pages tested
- [ ] All interactive elements covered
- [ ] All chart interactions validated
- [ ] Session management verified
- [ ] Error states tested

### Performance Goals
- E2E test suite completes in < 5 minutes
- Individual tests complete in < 30 seconds
- No flaky tests (tests that randomly fail)

---

## Future Enhancements

### Phase 2 (Optional)
- **Cross-browser testing**: Firefox, Safari, Edge
- **Mobile testing**: Test on actual mobile devices
- **Accessibility testing**: Screen reader compatibility, keyboard navigation
- **Visual regression testing**: Percy or BackstopJS for UI changes
- **Performance testing**: Lighthouse scores, load times
- **Parallel execution**: pytest-xdist for faster runs

---

## Questions for Review

1. **Test Scope**: Are these test scenarios comprehensive enough?
2. **Browser Support**: Should we test Firefox/Safari or Chrome only?
3. **CI Runtime**: Is 5 minutes acceptable for E2E suite?
4. **Screenshot Storage**: Where should failure screenshots be stored?
5. **Headless Mode**: Always run headless in CI or provide option?
6. **Test Data**: Should we use fixtures or real config files?
7. **Parallel Tests**: Should tests run in parallel or sequentially?

---

## Approval Checklist

- [ ] Test scenarios cover all critical user workflows
- [ ] Page Object Model structure is clear
- [ ] Dependencies are acceptable
- [ ] CI integration approach works
- [ ] Test isolation strategy is sound
- [ ] Performance goals are reasonable

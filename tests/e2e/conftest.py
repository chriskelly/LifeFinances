"""
Pytest configuration and fixtures for E2E tests.

This module provides shared fixtures and configuration for all E2E tests.
"""
import os
from typing import Generator

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from app import create_app


@pytest.fixture(scope="session")
def flask_app():
    """
    Create Flask app instance for testing.

    Yields:
        Flask app instance
    """
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture(scope="session")
def base_url(flask_app) -> str:
    """
    Get the base URL for the Flask app.

    For E2E tests, we assume the app is running on localhost:5000.
    In CI, this should be configured to point to the test server.

    Args:
        flask_app: Flask app fixture

    Returns:
        Base URL string
    """
    # In production E2E tests, read from environment or start test server
    return os.getenv("E2E_BASE_URL", "http://localhost:5000")


@pytest.fixture(scope="function")
def chrome_options() -> Options:
    """
    Create Chrome options for WebDriver.

    Returns:
        Chrome options configured for testing
    """
    options = Options()

    # Run in headless mode for CI
    if os.getenv("CI") or os.getenv("HEADLESS"):
        options.add_argument("--headless=new")

    # Additional options for stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Disable logging for cleaner output
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    return options


@pytest.fixture(scope="function")
def driver(chrome_options: Options) -> Generator[WebDriver, None, None]:
    """
    Create Chrome WebDriver instance.

    Args:
        chrome_options: Chrome options fixture

    Yields:
        WebDriver instance

    Cleanup:
        Quits the driver after test completes
    """
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(10)  # Default implicit wait

    yield driver

    driver.quit()


@pytest.fixture(scope="function")
def dashboard_page(driver: WebDriver, base_url: str):
    """
    Create Dashboard page object.

    Args:
        driver: WebDriver fixture
        base_url: Base URL fixture

    Returns:
        DashboardPage instance
    """
    from tests.e2e.page_objects.dashboard_page import DashboardPage

    return DashboardPage(driver, base_url)


@pytest.fixture(scope="function")
def config_page(driver: WebDriver, base_url: str):
    """
    Create Config page object.

    Args:
        driver: WebDriver fixture
        base_url: Base URL fixture

    Returns:
        ConfigPage instance
    """
    from tests.e2e.page_objects.config_page import ConfigPage

    return ConfigPage(driver, base_url)


@pytest.fixture(scope="function")
def run_page(driver: WebDriver, base_url: str):
    """
    Create Run page object.

    Args:
        driver: WebDriver fixture
        base_url: Base URL fixture

    Returns:
        RunPage instance
    """
    from tests.e2e.page_objects.run_page import RunPage

    return RunPage(driver, base_url)


@pytest.fixture(scope="function")
def results_page(driver: WebDriver, base_url: str):
    """
    Create Results page object.

    Args:
        driver: WebDriver fixture
        base_url: Base URL fixture

    Returns:
        ResultsPage instance
    """
    from tests.e2e.page_objects.results_page import ResultsPage

    return ResultsPage(driver, base_url)


@pytest.fixture(scope="function")
def sample_config() -> str:
    """
    Provide a sample valid configuration for testing.

    Returns:
        Sample configuration YAML as string
    """
    return """
User:
  name: Test User
  DOB: 1985-01-15
  retirement_date: 2050-01-01
  state: CA
  income_profiles:
    - start_date: 2025-01-01
      end_date: 2050-01-01
      gross_income: 100000

Portfolio:
  starting_balance: 500000
  allocation_strategy: flat

Strategy:
  strategy: flat_withdrawal
  withdrawal_amount: 40000

Spending:
  spending_profiles:
    - start_date: 2025-01-01
      annual_spending: 60000
"""


def pytest_configure(config):
    """
    Configure pytest with custom markers.

    Args:
        config: Pytest configuration object
    """
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "navigation: Navigation tests")
    config.addinivalue_line("markers", "config: Configuration tests")
    config.addinivalue_line("markers", "simulation: Simulation tests")
    config.addinivalue_line("markers", "results: Results tests")
    config.addinivalue_line("markers", "dashboard: Dashboard tests")
    config.addinivalue_line("markers", "session: Session persistence tests")
    config.addinivalue_line("markers", "error: Error handling tests")
    config.addinivalue_line("markers", "smoke: Smoke tests for quick validation")

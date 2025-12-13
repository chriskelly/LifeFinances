"""
Pytest configuration for Qt GUI tests.

Provides fixtures and setup for headless Qt testing.
"""

import os
import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Set environment variable to skip Flask initialization
os.environ["SKIP_FLASK_INIT"] = "1"


@pytest.fixture(scope="session")
def qapp():
    """
    Create a QApplication instance for the entire test session.

    This fixture ensures that Qt tests run headlessly without requiring
    a display server.

    Returns:
        QApplication instance
    """
    # Set headless mode for Qt
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Cleanup is automatic


@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    """
    Create a temporary configuration file path for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary config file
    """
    config_path = tmp_path / "test_config.yml"
    return config_path


@pytest.fixture
def sample_config_content() -> str:
    """
    Provide sample configuration content for testing.

    Returns:
        YAML configuration string
    """
    return """
age: 30
trial_quantity: 10
calculate_til: 2050
net_worth_target: 1500
state: California

portfolio:
  current_net_worth: 250
  tax_rate: 0.1
  allocation_strategy:
    flat:
      chosen: true
      allocation:
        US_Stock: 0.6
        US_Bond: 0.4

income_profiles:
  - starting_income: 80
    tax_deferred_income: 10
    yearly_raise: 0.04
    try_to_optimize: true
    social_security_eligible: true
    last_date: 2035.25

spending:
  spending_strategy:
    inflation_only:
      chosen: true
  profiles:
    - yearly_amount: 60

social_security_pension:
  trust_factor: 0.8
  pension_eligible: false
  strategy:
    mid:
      chosen: true
  earnings_records: {}
"""

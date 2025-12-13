"""
End-to-end tests for Qt GUI with actual simulation.

These tests run a real simulation and verify the GUI can display results.
"""

import pytest
from pathlib import Path

from qt_gui.widgets.results_viewer import ResultsViewerWidget
from app.models.simulator import gen_simulation_results


def test_results_viewer_with_real_simulation(qapp, tmp_path: Path) -> None:
    """
    Test that ResultsViewerWidget can display real simulation results.

    This is an end-to-end test that runs an actual simulation and verifies
    the results viewer can process and display the data without errors.

    Args:
        qapp: QApplication fixture
        tmp_path: Pytest temporary directory fixture
    """
    # Create a minimal config for quick simulation
    minimal_config = """
age: 30
trial_quantity: 5
calculate_til: 2040
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

    # Write minimal config to temp file
    config_path = tmp_path / "test_config.yml"
    config_path.write_text(minimal_config)

    # Save current config path and set to test config
    from app.data import constants
    original_config_path = constants.CONFIG_PATH
    constants.CONFIG_PATH = config_path

    try:
        # Run simulation (5 trials for speed)
        results = gen_simulation_results()

        # Verify results object
        assert results is not None
        assert results.trials is not None
        assert len(results.trials) == 5

        # Get dataframes
        dataframes = results.as_dataframes()
        assert len(dataframes) == 5

        # Check first dataframe has expected columns
        df = dataframes[0]
        assert 'Date' in df.columns
        assert 'Net Worth' in df.columns
        assert len(df) > 0  # Should have multiple intervals

        # Create results viewer widget
        widget = ResultsViewerWidget()

        # Display results (this should not crash)
        widget.display_results(results)

        # Verify widget state after display
        assert widget._results is not None
        assert widget._dataframes is not None
        assert len(widget._dataframes) == 5

        # Verify statistics were updated
        assert widget.num_trials_label.text() == "5"

        # Success label should have percentage
        success_text = widget.success_label.text()
        assert "Success Rate:" in success_text
        assert "%" in success_text

        # Table should have data
        assert widget.data_table.rowCount() > 0
        assert widget.data_table.columnCount() > 0

    finally:
        # Restore original config path
        constants.CONFIG_PATH = original_config_path


def test_simulation_success_calculation(qapp, tmp_path: Path) -> None:
    """
    Test that success/failure calculation works correctly.

    Args:
        qapp: QApplication fixture
        tmp_path: Pytest temporary directory fixture
    """
    # Use the same minimal config as above
    minimal_config = """
age: 30
trial_quantity: 3
calculate_til: 2040

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

    config_path = tmp_path / "test_config.yml"
    config_path.write_text(minimal_config)

    from app.data import constants
    original_config_path = constants.CONFIG_PATH
    constants.CONFIG_PATH = config_path

    try:
        # Run simulation
        results = gen_simulation_results()

        # Check each trial has get_success() method
        for trial in results.trials:
            success = trial.get_success()
            assert isinstance(success, bool)

            # Verify final net worth matches success status
            final_net_worth = trial.intervals[-1].state.net_worth
            if success:
                assert final_net_worth > 0
            else:
                assert final_net_worth <= 0

        # Verify calc_success_percentage returns a string
        success_pct = results.calc_success_percentage()
        assert isinstance(success_pct, str)
        assert "." in success_pct  # Should be like "66.7" or "100.0"

    finally:
        constants.CONFIG_PATH = original_config_path

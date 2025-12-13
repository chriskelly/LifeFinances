"""
Tests for SimulationRunnerWidget.

These tests run headlessly without requiring a display.
"""

import pytest
from pathlib import Path
from PyQt6.QtCore import Qt

from qt_gui.widgets.simulation_runner import SimulationRunnerWidget, SimulationWorker


def test_simulation_runner_initialization(qapp, test_config_path: Path) -> None:
    """
    Test that SimulationRunnerWidget initializes correctly.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = SimulationRunnerWidget(config_path=test_config_path)

    assert widget is not None
    assert widget.config_path == test_config_path
    assert not widget._simulation_running
    assert widget.run_btn.isEnabled()
    assert not widget.stop_btn.isEnabled()


def test_simulation_runner_ui_elements(qapp, test_config_path: Path) -> None:
    """
    Test that SimulationRunnerWidget has required UI elements.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = SimulationRunnerWidget(config_path=test_config_path)

    # Check UI components exist
    assert widget.age_label is not None
    assert widget.trials_label is not None
    assert widget.calculate_til_label is not None
    assert widget.net_worth_label is not None
    assert widget.progress_bar is not None
    assert widget.progress_label is not None
    assert widget.log_text is not None
    assert widget.run_btn is not None
    assert widget.stop_btn is not None


def test_simulation_runner_load_config_info(
    qapp, test_config_path: Path, sample_config_content: str
) -> None:
    """
    Test that SimulationRunnerWidget loads config information correctly.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
        sample_config_content: Sample YAML config
    """
    # Write sample config
    test_config_path.write_text(sample_config_content)

    widget = SimulationRunnerWidget(config_path=test_config_path)

    # Verify config info is loaded
    assert widget.age_label.text() == "30"
    assert widget.trials_label.text() == "10"
    assert "250" in widget.net_worth_label.text()


def test_simulation_runner_missing_config(qapp, test_config_path: Path) -> None:
    """
    Test that SimulationRunnerWidget handles missing config gracefully.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path (doesn't exist)
    """
    widget = SimulationRunnerWidget(config_path=test_config_path)

    # Should show default values when config is missing
    assert widget.age_label.text() == "--"
    assert widget.trials_label.text() == "--"
    assert widget.net_worth_label.text() == "--"


def test_simulation_runner_reload_config(
    qapp, test_config_path: Path, sample_config_content: str
) -> None:
    """
    Test that SimulationRunnerWidget can reload config.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
        sample_config_content: Sample YAML config
    """
    widget = SimulationRunnerWidget(config_path=test_config_path)

    # Initially no config
    assert widget.age_label.text() == "--"

    # Write config and reload
    test_config_path.write_text(sample_config_content)
    widget.reload_config()

    # Should now show config values
    assert widget.age_label.text() == "30"


def test_simulation_runner_log_message(qapp, test_config_path: Path) -> None:
    """
    Test that SimulationRunnerWidget can log messages.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = SimulationRunnerWidget(config_path=test_config_path)

    # Log should be empty initially
    assert widget.log_text.toPlainText() == ""

    # Log a message
    widget.log_message("Test message")

    # Verify message appears in log
    assert "Test message" in widget.log_text.toPlainText()


def test_simulation_worker_initialization(test_config_path: Path, sample_config_content: str) -> None:
    """
    Test that SimulationWorker initializes correctly.

    Args:
        test_config_path: Temporary config file path
        sample_config_content: Sample YAML config
    """
    test_config_path.write_text(sample_config_content)

    worker = SimulationWorker(config_path=test_config_path)

    assert worker is not None
    assert worker.config_path == test_config_path
    assert not worker._should_stop


def test_simulation_worker_can_stop(test_config_path: Path, sample_config_content: str) -> None:
    """
    Test that SimulationWorker can be stopped.

    Args:
        test_config_path: Temporary config file path
        sample_config_content: Sample YAML config
    """
    test_config_path.write_text(sample_config_content)

    worker = SimulationWorker(config_path=test_config_path)

    assert not worker._should_stop

    worker.stop()

    assert worker._should_stop

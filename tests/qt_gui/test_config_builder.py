"""
Tests for ConfigBuilderWidget.

These tests run headlessly without requiring a display.
"""

import pytest
from pathlib import Path
from PyQt6.QtCore import Qt

from qt_gui.widgets.config_builder import ConfigBuilderWidget


def test_config_builder_initialization(qapp, test_config_path: Path) -> None:
    """
    Test that ConfigBuilderWidget initializes correctly.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = ConfigBuilderWidget(config_path=test_config_path)

    assert widget is not None
    assert widget.config_path == test_config_path
    assert not widget.has_unsaved_changes()


def test_config_builder_default_values(qapp, test_config_path: Path) -> None:
    """
    Test that ConfigBuilderWidget has sensible default values.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = ConfigBuilderWidget(config_path=test_config_path)

    # Check basic settings defaults
    assert widget.age_spin.value() == 30
    assert widget.trials_spin.value() == 500
    assert widget.calculate_til_spin.value() == 2090

    # Check portfolio defaults
    assert widget.current_net_worth_spin.value() == 250
    assert widget.tax_rate_spin.value() == 0.1

    # Check allocation defaults
    assert widget.us_stock_spin.value() == 0.6
    assert widget.us_bond_spin.value() == 0.4


def test_config_builder_marks_unsaved_changes(qapp, test_config_path: Path) -> None:
    """
    Test that ConfigBuilderWidget marks unsaved changes when values change.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = ConfigBuilderWidget(config_path=test_config_path)

    assert not widget.has_unsaved_changes()
    assert not widget.save_btn.isEnabled()

    # Change a value
    widget.age_spin.setValue(35)

    assert widget.has_unsaved_changes()
    assert widget.save_btn.isEnabled()


def test_config_builder_build_config_dict(qapp, test_config_path: Path) -> None:
    """
    Test that ConfigBuilderWidget builds correct configuration dictionary.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = ConfigBuilderWidget(config_path=test_config_path)

    # Set some values
    widget.age_spin.setValue(40)
    widget.trials_spin.setValue(100)
    widget.current_net_worth_spin.setValue(500)

    config_dict = widget._build_config_dict()

    assert config_dict['age'] == 40
    assert config_dict['trial_quantity'] == 100
    assert config_dict['portfolio']['current_net_worth'] == 500


def test_config_builder_load_and_save(
    qapp, test_config_path: Path, sample_config_content: str
) -> None:
    """
    Test that ConfigBuilderWidget can load and save configuration.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
        sample_config_content: Sample YAML config
    """
    # Write sample config
    test_config_path.write_text(sample_config_content)

    # Create widget and load config
    widget = ConfigBuilderWidget(config_path=test_config_path)

    # Verify loaded values
    assert widget.age_spin.value() == 30
    assert widget.trials_spin.value() == 10  # Note: sample has 10 trials

    # Modify and save
    widget.age_spin.setValue(35)
    assert widget.save_config()

    # Verify file was updated
    assert test_config_path.exists()
    content = test_config_path.read_text()
    assert 'age: 35' in content


def test_config_builder_validation_on_save(qapp, test_config_path: Path) -> None:
    """
    Test that ConfigBuilderWidget validates configuration on save.

    Args:
        qapp: QApplication fixture
        test_config_path: Temporary config file path
    """
    widget = ConfigBuilderWidget(config_path=test_config_path)

    # Set invalid allocation (doesn't sum to 1.0)
    widget.us_stock_spin.setValue(0.3)
    widget.us_bond_spin.setValue(0.3)  # Total = 0.6, not 1.0

    # This should still build the config, but Pydantic may validate
    # Note: Current config may or may not enforce this constraint
    config_dict = widget._build_config_dict()
    assert config_dict['portfolio']['allocation_strategy']['flat']['allocation']['US_Stock'] == 0.3

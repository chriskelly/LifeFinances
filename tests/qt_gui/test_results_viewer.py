"""
Tests for ResultsViewerWidget.

These tests run headlessly without requiring a display.
"""

import pytest
from pathlib import Path
from PyQt6.QtCore import Qt

from qt_gui.widgets.results_viewer import ResultsViewerWidget


def test_results_viewer_initialization(qapp) -> None:
    """
    Test that ResultsViewerWidget initializes correctly.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    assert widget is not None
    assert widget._results is None
    assert widget._dataframes is None


def test_results_viewer_ui_elements(qapp) -> None:
    """
    Test that ResultsViewerWidget has required UI elements.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    # Check UI components exist
    assert widget.success_label is not None
    assert widget.num_trials_label is not None
    assert widget.num_success_label is not None
    assert widget.num_failure_label is not None
    assert widget.view_tabs is not None
    assert widget.canvas is not None
    assert widget.data_table is not None
    assert widget.placeholder_label is not None


def test_results_viewer_initial_state(qapp) -> None:
    """
    Test that ResultsViewerWidget shows placeholder initially.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    # Note: In headless mode, widgets aren't shown so isVisible() returns False
    # We check that placeholder is not hidden (isHidden() returns False)
    assert not widget.placeholder_label.isHidden()

    # View tabs should be hidden
    assert widget.view_tabs.isHidden()

    # Statistics should show defaults
    assert widget.num_trials_label.text() == "--"
    assert widget.num_success_label.text() == "--"
    assert widget.num_failure_label.text() == "--"


def test_results_viewer_clear_results(qapp) -> None:
    """
    Test that ResultsViewerWidget can clear results.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    # Clear results (should not crash even if no results)
    widget.clear_results()

    # Verify state is reset
    assert widget._results is None
    assert widget._dataframes is None
    # In headless mode, check that placeholder is not hidden
    assert not widget.placeholder_label.isHidden()
    assert widget.view_tabs.isHidden()


def test_results_viewer_table_columns(qapp) -> None:
    """
    Test that ResultsViewerWidget data table is properly initialized.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    # Initially, table should be empty
    assert widget.data_table.rowCount() == 0
    assert widget.data_table.columnCount() == 0


def test_results_viewer_canvas_initialization(qapp) -> None:
    """
    Test that ResultsViewerWidget matplotlib canvas initializes correctly.

    Args:
        qapp: QApplication fixture
    """
    widget = ResultsViewerWidget()

    # Canvas should exist
    assert widget.canvas is not None
    assert widget.canvas.figure is not None
    assert widget.canvas.axes is not None

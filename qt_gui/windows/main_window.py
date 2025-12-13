"""
Main window for LifeFinances Qt GUI.

Provides a tabbed interface with:
- Configuration Builder
- Simulation Runner
- Results Viewer
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QStatusBar,
)

from qt_gui.widgets.config_builder import ConfigBuilderWidget
from qt_gui.widgets.simulation_runner import SimulationRunnerWidget
from qt_gui.widgets.results_viewer import ResultsViewerWidget


class MainWindow(QMainWindow):
    """
    Main application window for LifeFinances Qt GUI.

    Provides a tabbed interface for configuration, simulation, and results.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("LifeFinances - Retirement Planning Simulator")
        self.setMinimumSize(1200, 800)

        # Configuration file path
        self.config_path: Path = Path("config.yml")

        # Create central widget with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main layout
        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Initialize widgets
        self._init_widgets()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Connect signals
        self._connect_signals()

    def _init_widgets(self) -> None:
        """Initialize all tab widgets."""
        # Configuration builder tab
        self.config_builder = ConfigBuilderWidget(config_path=self.config_path)
        self.tabs.addTab(self.config_builder, "Configuration")

        # Simulation runner tab
        self.simulation_runner = SimulationRunnerWidget(config_path=self.config_path)
        self.tabs.addTab(self.simulation_runner, "Run Simulation")

        # Results viewer tab
        self.results_viewer = ResultsViewerWidget()
        self.tabs.addTab(self.results_viewer, "Results")

    def _connect_signals(self) -> None:
        """Connect signals between widgets."""
        # When config is saved, update simulation runner
        self.config_builder.config_saved.connect(self._on_config_saved)

        # When simulation completes, update results viewer
        self.simulation_runner.simulation_completed.connect(
            self._on_simulation_completed
        )

        # Status bar updates
        self.config_builder.status_message.connect(self.status_bar.showMessage)
        self.simulation_runner.status_message.connect(self.status_bar.showMessage)
        self.results_viewer.status_message.connect(self.status_bar.showMessage)

    def _on_config_saved(self, config_path: Path) -> None:
        """
        Handle configuration saved event.

        Args:
            config_path: Path to the saved configuration file
        """
        self.status_bar.showMessage(f"Configuration saved to {config_path}", 5000)
        # Reload config in simulation runner
        self.simulation_runner.reload_config()

    def _on_simulation_completed(self, results: object) -> None:
        """
        Handle simulation completion event.

        Args:
            results: Results object from simulation
        """
        self.status_bar.showMessage("Simulation completed successfully", 5000)
        # Switch to results tab and display results
        self.results_viewer.display_results(results)
        self.tabs.setCurrentWidget(self.results_viewer)

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Prompts user to save unsaved changes if necessary.

        Args:
            event: Close event
        """
        if self.config_builder.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved configuration changes. Do you want to save before exiting?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )

            if reply == QMessageBox.StandardButton.Save:
                if not self.config_builder.save_config():
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        event.accept()

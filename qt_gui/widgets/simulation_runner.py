"""
Simulation runner widget for LifeFinances Qt GUI.

Provides interface for running Monte Carlo simulations with real-time
progress tracking.
"""

from pathlib import Path
from typing import Optional
from threading import Thread

from PyQt6.QtCore import pyqtSignal, QObject, QThread, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)

from app.models.simulator import gen_simulation_results, Results
from app.models.config import get_config, read_config_file


class SimulationWorker(QObject):
    """
    Worker object for running simulation in a separate thread.

    Emits progress updates and results upon completion.
    """

    # Signals
    progress_updated = pyqtSignal(int, int)  # current, total
    simulation_completed = pyqtSignal(object)  # Results object
    simulation_failed = pyqtSignal(str)  # Error message
    log_message = pyqtSignal(str)  # Log messages

    def __init__(self, config_path: Path) -> None:
        """
        Initialize the simulation worker.

        Args:
            config_path: Path to the configuration file
        """
        super().__init__()
        self.config_path = config_path
        self._should_stop = False

    def run(self) -> None:
        """Run the simulation."""
        try:
            self.log_message.emit("Loading configuration...")
            config = get_config(config_path=self.config_path)

            self.log_message.emit(
                f"Starting simulation with {config.trial_quantity} trials..."
            )

            # Note: The current gen_simulation_results doesn't support progress callbacks
            # For now, we'll show indeterminate progress and update when complete
            # Future enhancement: Modify simulator to support progress callbacks

            results = gen_simulation_results()

            if self._should_stop:
                self.log_message.emit("Simulation cancelled by user.")
                return

            self.log_message.emit("Simulation completed successfully!")
            self.simulation_completed.emit(results)

        except Exception as e:
            error_msg = f"Simulation failed: {str(e)}"
            self.log_message.emit(error_msg)
            self.simulation_failed.emit(error_msg)

    def stop(self) -> None:
        """Request simulation to stop."""
        self._should_stop = True


class SimulationRunnerWidget(QWidget):
    """
    Widget for running Monte Carlo simulations.

    Provides controls for starting/stopping simulations and displays
    real-time progress and log output.
    """

    # Signals
    simulation_completed = pyqtSignal(object)  # Results object
    status_message = pyqtSignal(str)  # Status message for status bar

    def __init__(self, config_path: Path, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the simulation runner widget.

        Args:
            config_path: Path to the configuration file
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_path = config_path
        self.worker: Optional[SimulationWorker] = None
        self.worker_thread: Optional[QThread] = None
        self._simulation_running = False

        self._init_ui()
        self._load_config_info()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Configuration info section
        info_group = QGroupBox("Configuration Summary")
        info_layout = QFormLayout(info_group)

        self.age_label = QLabel("--")
        info_layout.addRow("Current Age:", self.age_label)

        self.trials_label = QLabel("--")
        info_layout.addRow("Number of Trials:", self.trials_label)

        self.calculate_til_label = QLabel("--")
        info_layout.addRow("Calculate Until:", self.calculate_til_label)

        self.net_worth_label = QLabel("--")
        info_layout.addRow("Current Net Worth:", self.net_worth_label)

        layout.addWidget(info_group)

        # Control section
        control_layout = QHBoxLayout()

        self.run_btn = QPushButton("Run Simulation")
        self.run_btn.clicked.connect(self._start_simulation)
        self.run_btn.setStyleSheet("font-size: 14pt; padding: 10px;")
        control_layout.addWidget(self.run_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_simulation)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        layout.addLayout(control_layout)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready to run simulation")
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # Log section
        log_group = QGroupBox("Simulation Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        # Add stretch to push everything to the top
        layout.addStretch()

    def _load_config_info(self) -> None:
        """Load and display configuration information."""
        try:
            if self.config_path.exists():
                config = get_config(config_path=self.config_path)

                self.age_label.setText(str(config.age))
                self.trials_label.setText(str(config.trial_quantity))
                self.calculate_til_label.setText(str(config.calculate_til))
                self.net_worth_label.setText(
                    f"${config.portfolio.current_net_worth:,.0f}k"
                )

                self.status_message.emit("Configuration loaded")
            else:
                self._clear_config_info()
                self.status_message.emit(
                    f"Configuration file not found: {self.config_path}"
                )

        except Exception as e:
            self._clear_config_info()
            self.log_message(f"Error loading configuration: {e}")
            self.status_message.emit("Error loading configuration")

    def _clear_config_info(self) -> None:
        """Clear configuration information display."""
        self.age_label.setText("--")
        self.trials_label.setText("--")
        self.calculate_til_label.setText("--")
        self.net_worth_label.setText("--")

    def _start_simulation(self) -> None:
        """Start the simulation in a background thread."""
        if self._simulation_running:
            return

        # Verify config file exists
        if not self.config_path.exists():
            QMessageBox.warning(
                self,
                "Configuration Not Found",
                f"Configuration file not found: {self.config_path}\n\n"
                "Please create a configuration first.",
            )
            return

        # Clear log
        self.log_text.clear()

        # Create worker and thread
        self.worker = SimulationWorker(config_path=self.config_path)
        self.worker_thread = QThread()

        # Move worker to thread
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.simulation_completed.connect(self._on_simulation_completed)
        self.worker.simulation_failed.connect(self._on_simulation_failed)
        self.worker.log_message.connect(self.log_message)
        self.worker_thread.finished.connect(self._on_thread_finished)

        # Update UI state
        self._simulation_running = True
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        self.progress_label.setText("Running simulation...")
        self.status_message.emit("Simulation running...")

        # Start thread
        self.worker_thread.start()

    def _stop_simulation(self) -> None:
        """Stop the running simulation."""
        if self.worker:
            self.worker.stop()
            self.log_message("Stopping simulation...")
            self.status_message.emit("Stopping simulation...")

    def _on_progress_updated(self, current: int, total: int) -> None:
        """
        Handle progress update from worker.

        Args:
            current: Current trial number
            total: Total number of trials
        """
        if total > 0:
            progress_pct = int((current / total) * 100)
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(progress_pct)
            self.progress_label.setText(f"Trial {current} of {total} ({progress_pct}%)")

    def _on_simulation_completed(self, results: Results) -> None:
        """
        Handle simulation completion.

        Args:
            results: Results object from simulation
        """
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Simulation completed!")

        # Display success percentage
        success_pct = results.calc_success_percentage()
        self.log_message(f"\nSuccess Rate: {success_pct}")

        # Emit signal for results viewer
        self.simulation_completed.emit(results)

        # Clean up thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()

    def _on_simulation_failed(self, error_msg: str) -> None:
        """
        Handle simulation failure.

        Args:
            error_msg: Error message
        """
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)
        self.progress_label.setText("Simulation failed")

        QMessageBox.critical(self, "Simulation Error", error_msg)

        # Clean up thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()

    def _on_thread_finished(self) -> None:
        """Handle thread cleanup."""
        self._simulation_running = False
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        # Clean up worker and thread
        if self.worker_thread:
            self.worker_thread.deleteLater()
            self.worker_thread = None
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def log_message(self, message: str) -> None:
        """
        Add a message to the log.

        Args:
            message: Message to log
        """
        self.log_text.append(message)

    def reload_config(self) -> None:
        """Reload configuration information."""
        self._load_config_info()

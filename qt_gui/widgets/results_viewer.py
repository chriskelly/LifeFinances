"""
Results viewer widget for LifeFinances Qt GUI.

Displays simulation results with summary statistics and visualizations.
"""

from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QTabWidget,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.models.simulator import Results


class MatplotlibCanvas(FigureCanvas):
    """
    Matplotlib canvas for embedding plots in Qt.
    """

    def __init__(self, parent: Optional[QWidget] = None, width: int = 8, height: int = 6, dpi: int = 100) -> None:
        """
        Initialize the matplotlib canvas.

        Args:
            parent: Parent widget
            width: Figure width in inches
            height: Figure height in inches
            dpi: Dots per inch
        """
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        super().__init__(self.figure)
        self.setParent(parent)


class ResultsViewerWidget(QWidget):
    """
    Widget for viewing simulation results.

    Displays summary statistics, success percentage, and visualizations
    of net worth projections across trials.
    """

    # Signals
    status_message = pyqtSignal(str)  # Status message for status bar

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the results viewer widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._results: Optional[Results] = None
        self._dataframes: Optional[list[pd.DataFrame]] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Summary statistics section
        stats_group = QGroupBox("Summary Statistics")
        stats_layout = QVBoxLayout(stats_group)

        # Success percentage (large, prominent)
        success_layout = QHBoxLayout()
        success_layout.addStretch()
        self.success_label = QLabel("No simulation results yet")
        self.success_label.setStyleSheet(
            "font-size: 24pt; font-weight: bold; color: #2c3e50;"
        )
        success_layout.addWidget(self.success_label)
        success_layout.addStretch()
        stats_layout.addLayout(success_layout)

        # Additional statistics
        stats_form_layout = QHBoxLayout()
        self.num_trials_label = QLabel("--")
        self.num_success_label = QLabel("--")
        self.num_failure_label = QLabel("--")

        stats_form_layout.addWidget(QLabel("Total Trials:"))
        stats_form_layout.addWidget(self.num_trials_label)
        stats_form_layout.addStretch()
        stats_form_layout.addWidget(QLabel("Successful:"))
        stats_form_layout.addWidget(self.num_success_label)
        stats_form_layout.addStretch()
        stats_form_layout.addWidget(QLabel("Failed:"))
        stats_form_layout.addWidget(self.num_failure_label)
        stats_form_layout.addStretch()

        stats_layout.addLayout(stats_form_layout)
        layout.addWidget(stats_group)

        # Tabs for different views
        self.view_tabs = QTabWidget()
        layout.addWidget(self.view_tabs)

        # Visualization tab
        viz_widget = QWidget()
        viz_layout = QVBoxLayout(viz_widget)

        self.canvas = MatplotlibCanvas(viz_widget, width=10, height=6, dpi=100)
        viz_layout.addWidget(self.canvas)

        self.view_tabs.addTab(viz_widget, "Net Worth Projection")

        # Data table tab
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)

        # Table controls
        table_controls = QHBoxLayout()
        table_controls.addWidget(QLabel("Showing data from first trial"))
        table_controls.addStretch()

        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self._export_to_csv)
        table_controls.addWidget(export_btn)

        table_layout.addLayout(table_controls)

        self.data_table = QTableWidget()
        table_layout.addWidget(self.data_table)

        self.view_tabs.addTab(table_widget, "Data Table")

        # Placeholder message
        self.placeholder_label = QLabel("Run a simulation to view results")
        self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder_label.setStyleSheet("font-size: 14pt; color: #7f8c8d;")
        layout.addWidget(self.placeholder_label)

        # Hide data views initially
        self.view_tabs.hide()

    def display_results(self, results: Results) -> None:
        """
        Display simulation results.

        Args:
            results: Results object from simulation
        """
        self._results = results
        self._dataframes = results.as_dataframes()

        # Hide placeholder, show views
        self.placeholder_label.hide()
        self.view_tabs.show()

        # Update summary statistics
        self._update_statistics()

        # Update visualization
        self._update_visualization()

        # Update data table
        self._update_data_table()

        self.status_message.emit("Results displayed successfully")

    def _update_statistics(self) -> None:
        """Update summary statistics display."""
        if not self._results:
            return

        # Success percentage
        success_pct = self._results.calc_success_percentage()
        self.success_label.setText(f"Success Rate: {success_pct}")

        # Change color based on success rate
        try:
            pct_value = float(success_pct.strip('%'))
            if pct_value >= 90:
                color = "#27ae60"  # Green
            elif pct_value >= 75:
                color = "#f39c12"  # Orange
            else:
                color = "#e74c3c"  # Red
            self.success_label.setStyleSheet(
                f"font-size: 24pt; font-weight: bold; color: {color};"
            )
        except ValueError:
            pass

        # Count successful vs failed trials
        num_trials = len(self._results.trials)
        num_success = sum(1 for trial in self._results.trials if trial.get_success())
        num_failure = num_trials - num_success

        self.num_trials_label.setText(str(num_trials))
        self.num_success_label.setText(str(num_success))
        self.num_failure_label.setText(str(num_failure))

    def _update_visualization(self) -> None:
        """Update net worth projection visualization."""
        if not self._dataframes or len(self._dataframes) == 0:
            return

        # Clear previous plot
        self.canvas.axes.clear()

        # Plot multiple trials (sample to avoid overcrowding)
        num_trials_to_plot = min(50, len(self._dataframes))
        alpha = 0.3 if num_trials_to_plot > 10 else 0.6

        for i in range(num_trials_to_plot):
            df = self._dataframes[i]
            trial = self._results.trials[i]

            # Determine color based on success
            color = 'green' if trial.get_success() else 'red'

            # Plot net worth over time
            if 'Date' in df.columns and 'Net Worth' in df.columns:
                self.canvas.axes.plot(
                    df['Date'],
                    df['Net Worth'],
                    color=color,
                    alpha=alpha,
                    linewidth=0.5
                )

        # Add median projection (bold line)
        if len(self._dataframes) > 0:
            # Calculate median net worth at each time point
            all_dates = self._dataframes[0]['Date'].values
            median_net_worths = []

            for date in all_dates:
                net_worths_at_date = []
                for df in self._dataframes:
                    matching_rows = df[df['Date'] == date]
                    if not matching_rows.empty:
                        net_worths_at_date.append(matching_rows['Net Worth'].values[0])

                if net_worths_at_date:
                    median_net_worths.append(pd.Series(net_worths_at_date).median())
                else:
                    median_net_worths.append(0)

            self.canvas.axes.plot(
                all_dates,
                median_net_worths,
                color='blue',
                linewidth=2,
                label='Median'
            )

        # Formatting
        self.canvas.axes.set_xlabel('Year')
        self.canvas.axes.set_ylabel('Net Worth ($k)')
        self.canvas.axes.set_title('Net Worth Projections Across Trials')
        self.canvas.axes.legend(['Successful', 'Failed', 'Median'], loc='best')
        self.canvas.axes.grid(True, alpha=0.3)
        self.canvas.axes.axhline(y=0, color='black', linestyle='--', linewidth=0.5)

        # Refresh canvas
        self.canvas.draw()

    def _update_data_table(self) -> None:
        """Update data table with first trial results."""
        if not self._dataframes or len(self._dataframes) == 0:
            return

        # Use first trial data
        df = self._dataframes[0]

        # Set up table
        self.data_table.setRowCount(len(df))
        self.data_table.setColumnCount(len(df.columns))
        self.data_table.setHorizontalHeaderLabels(df.columns.tolist())

        # Populate table
        for row_idx in range(len(df)):
            for col_idx, col_name in enumerate(df.columns):
                value = df.iloc[row_idx, col_idx]

                # Format numbers nicely
                if isinstance(value, (int, float)):
                    if col_name == 'date':
                        display_value = f"{value:.2f}"
                    else:
                        display_value = f"{value:,.2f}"
                else:
                    display_value = str(value)

                item = QTableWidgetItem(display_value)
                self.data_table.setItem(row_idx, col_idx, item)

        # Resize columns to content
        self.data_table.resizeColumnsToContents()

    def _export_to_csv(self) -> None:
        """Export results to CSV file."""
        if not self._dataframes or len(self._dataframes) == 0:
            QMessageBox.warning(
                self, "No Data", "No simulation results to export."
            )
            return

        # Ask user for file location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Results to CSV",
            "simulation_results.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if not file_path:
            return

        try:
            # Export first trial data
            df = self._dataframes[0]
            df.to_csv(file_path, index=False)

            QMessageBox.information(
                self,
                "Export Successful",
                f"Results exported to:\n{file_path}"
            )
            self.status_message.emit(f"Results exported to {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export results:\n{e}"
            )
            self.status_message.emit("Export failed")

    def clear_results(self) -> None:
        """Clear displayed results."""
        self._results = None
        self._dataframes = None

        self.success_label.setText("No simulation results yet")
        self.success_label.setStyleSheet(
            "font-size: 24pt; font-weight: bold; color: #2c3e50;"
        )
        self.num_trials_label.setText("--")
        self.num_success_label.setText("--")
        self.num_failure_label.setText("--")

        self.canvas.axes.clear()
        self.canvas.draw()

        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)

        self.view_tabs.hide()
        self.placeholder_label.show()

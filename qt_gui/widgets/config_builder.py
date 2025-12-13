"""
Configuration builder widget for LifeFinances Qt GUI.

Provides a form-based interface for creating and editing configuration files.
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QScrollArea,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QLabel,
    QCheckBox,
    QTabWidget,
)

import yaml
from pydantic import ValidationError

from app.models.config import User, read_config_file, write_config_file


class ConfigBuilderWidget(QWidget):
    """
    Form-based configuration builder widget.

    Provides a structured form interface for editing LifeFinances configuration.
    Emits signals when configuration is saved or modified.
    """

    # Signals
    config_saved = pyqtSignal(Path)  # Emitted when config is saved
    status_message = pyqtSignal(str)  # Status message for status bar

    def __init__(self, config_path: Path, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the configuration builder widget.

        Args:
            config_path: Path to the configuration file
            parent: Parent widget
        """
        super().__init__(parent)
        self.config_path = config_path
        self._unsaved_changes = False
        self._config_data: Optional[dict] = None

        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)

        # Header with file path
        header_layout = QHBoxLayout()
        self.file_label = QLabel(f"Editing: {self.config_path}")
        self.file_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.file_label)
        header_layout.addStretch()

        # Buttons
        load_btn = QPushButton("Load Different File")
        load_btn.clicked.connect(self._load_different_file)
        header_layout.addWidget(load_btn)

        layout.addLayout(header_layout)

        # Create scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create form widget
        form_widget = QWidget()
        self.form_layout = QVBoxLayout(form_widget)

        # Create tabbed interface for different config sections
        self.config_tabs = QTabWidget()
        self.form_layout.addWidget(self.config_tabs)

        # Initialize form sections
        self._init_basic_settings()
        self._init_portfolio_settings()
        self._init_income_settings()
        self._init_spending_settings()
        self._init_social_security_settings()

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._save_config)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)

        self.reset_btn = QPushButton("Reset Changes")
        self.reset_btn.clicked.connect(self._load_config)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)

        layout.addLayout(button_layout)

    def _init_basic_settings(self) -> None:
        """Initialize basic settings form."""
        basic_widget = QWidget()
        layout = QFormLayout(basic_widget)

        # Age
        self.age_spin = QSpinBox()
        self.age_spin.setRange(18, 120)
        self.age_spin.setValue(30)
        self.age_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Current Age:", self.age_spin)

        # Trial quantity
        self.trials_spin = QSpinBox()
        self.trials_spin.setRange(1, 10000)
        self.trials_spin.setValue(500)
        self.trials_spin.setSingleStep(100)
        self.trials_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Number of Trials:", self.trials_spin)

        # Calculate until
        self.calculate_til_spin = QDoubleSpinBox()
        self.calculate_til_spin.setRange(2020, 2150)
        self.calculate_til_spin.setValue(2090)
        self.calculate_til_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Calculate Until Year:", self.calculate_til_spin)

        # Net worth target
        self.net_worth_target_spin = QDoubleSpinBox()
        self.net_worth_target_spin.setRange(0, 1000000)
        self.net_worth_target_spin.setValue(1500)
        self.net_worth_target_spin.setSuffix(" k")
        self.net_worth_target_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Net Worth Target:", self.net_worth_target_spin)

        # State
        self.state_edit = QLineEdit("California")
        self.state_edit.textChanged.connect(self._mark_unsaved)
        layout.addRow("State:", self.state_edit)

        self.config_tabs.addTab(basic_widget, "Basic Settings")

    def _init_portfolio_settings(self) -> None:
        """Initialize portfolio settings form."""
        portfolio_widget = QWidget()
        layout = QFormLayout(portfolio_widget)

        # Current net worth
        self.current_net_worth_spin = QDoubleSpinBox()
        self.current_net_worth_spin.setRange(-10000, 1000000)
        self.current_net_worth_spin.setValue(250)
        self.current_net_worth_spin.setSuffix(" k")
        self.current_net_worth_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Current Net Worth:", self.current_net_worth_spin)

        # Tax rate
        self.tax_rate_spin = QDoubleSpinBox()
        self.tax_rate_spin.setRange(0, 1)
        self.tax_rate_spin.setSingleStep(0.01)
        self.tax_rate_spin.setValue(0.1)
        self.tax_rate_spin.setDecimals(2)
        self.tax_rate_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Tax Rate:", self.tax_rate_spin)

        # Allocation strategy section
        allocation_group = QGroupBox("Allocation Strategy")
        allocation_layout = QVBoxLayout(allocation_group)

        # Flat allocation
        self.flat_allocation_check = QCheckBox("Use Flat Allocation")
        self.flat_allocation_check.setChecked(True)
        self.flat_allocation_check.stateChanged.connect(self._mark_unsaved)
        allocation_layout.addWidget(self.flat_allocation_check)

        flat_form = QFormLayout()
        self.us_stock_spin = QDoubleSpinBox()
        self.us_stock_spin.setRange(0, 1)
        self.us_stock_spin.setSingleStep(0.01)
        self.us_stock_spin.setValue(0.6)
        self.us_stock_spin.setDecimals(2)
        self.us_stock_spin.valueChanged.connect(self._mark_unsaved)
        flat_form.addRow("US Stock %:", self.us_stock_spin)

        self.us_bond_spin = QDoubleSpinBox()
        self.us_bond_spin.setRange(0, 1)
        self.us_bond_spin.setSingleStep(0.01)
        self.us_bond_spin.setValue(0.4)
        self.us_bond_spin.setDecimals(2)
        self.us_bond_spin.valueChanged.connect(self._mark_unsaved)
        flat_form.addRow("US Bond %:", self.us_bond_spin)

        allocation_layout.addLayout(flat_form)

        layout.addRow(allocation_group)

        self.config_tabs.addTab(portfolio_widget, "Portfolio")

    def _init_income_settings(self) -> None:
        """Initialize income settings form."""
        income_widget = QWidget()
        layout = QFormLayout(income_widget)

        # Primary income profile
        income_group = QGroupBox("Primary Income Profile")
        income_layout = QFormLayout(income_group)

        self.starting_income_spin = QDoubleSpinBox()
        self.starting_income_spin.setRange(0, 10000)
        self.starting_income_spin.setValue(80)
        self.starting_income_spin.setSuffix(" k")
        self.starting_income_spin.valueChanged.connect(self._mark_unsaved)
        income_layout.addRow("Starting Income:", self.starting_income_spin)

        self.tax_deferred_spin = QDoubleSpinBox()
        self.tax_deferred_spin.setRange(0, 1000)
        self.tax_deferred_spin.setValue(10)
        self.tax_deferred_spin.setSuffix(" k")
        self.tax_deferred_spin.valueChanged.connect(self._mark_unsaved)
        income_layout.addRow("Tax Deferred Income:", self.tax_deferred_spin)

        self.yearly_raise_spin = QDoubleSpinBox()
        self.yearly_raise_spin.setRange(0, 1)
        self.yearly_raise_spin.setSingleStep(0.01)
        self.yearly_raise_spin.setValue(0.04)
        self.yearly_raise_spin.setDecimals(2)
        self.yearly_raise_spin.valueChanged.connect(self._mark_unsaved)
        income_layout.addRow("Yearly Raise %:", self.yearly_raise_spin)

        self.income_last_date_spin = QDoubleSpinBox()
        self.income_last_date_spin.setRange(2020, 2150)
        self.income_last_date_spin.setValue(2035.25)
        self.income_last_date_spin.valueChanged.connect(self._mark_unsaved)
        income_layout.addRow("Last Date:", self.income_last_date_spin)

        layout.addRow(income_group)

        self.config_tabs.addTab(income_widget, "Income")

    def _init_spending_settings(self) -> None:
        """Initialize spending settings form."""
        spending_widget = QWidget()
        layout = QFormLayout(spending_widget)

        # Primary spending profile
        spending_group = QGroupBox("Spending Profile")
        spending_layout = QFormLayout(spending_group)

        self.yearly_spending_spin = QDoubleSpinBox()
        self.yearly_spending_spin.setRange(0, 10000)
        self.yearly_spending_spin.setValue(60)
        self.yearly_spending_spin.setSuffix(" k")
        self.yearly_spending_spin.valueChanged.connect(self._mark_unsaved)
        spending_layout.addRow("Yearly Spending:", self.yearly_spending_spin)

        layout.addRow(spending_group)

        self.config_tabs.addTab(spending_widget, "Spending")

    def _init_social_security_settings(self) -> None:
        """Initialize social security settings form."""
        ss_widget = QWidget()
        layout = QFormLayout(ss_widget)

        # Trust factor
        self.ss_trust_spin = QDoubleSpinBox()
        self.ss_trust_spin.setRange(0, 1)
        self.ss_trust_spin.setSingleStep(0.1)
        self.ss_trust_spin.setValue(0.8)
        self.ss_trust_spin.setDecimals(1)
        self.ss_trust_spin.valueChanged.connect(self._mark_unsaved)
        layout.addRow("Trust Factor:", self.ss_trust_spin)

        # Strategy checkboxes
        strategy_group = QGroupBox("Claiming Strategies")
        strategy_layout = QVBoxLayout(strategy_group)

        self.ss_early_check = QCheckBox("Early (Age 62)")
        self.ss_early_check.stateChanged.connect(self._mark_unsaved)
        strategy_layout.addWidget(self.ss_early_check)

        self.ss_mid_check = QCheckBox("Mid (Age 67) - Default")
        self.ss_mid_check.setChecked(True)
        self.ss_mid_check.stateChanged.connect(self._mark_unsaved)
        strategy_layout.addWidget(self.ss_mid_check)

        self.ss_late_check = QCheckBox("Late (Age 70)")
        self.ss_late_check.stateChanged.connect(self._mark_unsaved)
        strategy_layout.addWidget(self.ss_late_check)

        layout.addRow(strategy_group)

        self.config_tabs.addTab(ss_widget, "Social Security")

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_path.exists():
                config_text = read_config_file(config_path=self.config_path)
                self._config_data = yaml.safe_load(config_text)
                self._populate_form()
                self.status_message.emit(f"Loaded configuration from {self.config_path}")
            else:
                self.status_message.emit(
                    f"Configuration file not found: {self.config_path}"
                )
                # Use default values (already set in _init_* methods)
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Configuration", f"Failed to load configuration:\n{e}"
            )
            self.status_message.emit("Error loading configuration")

        self._unsaved_changes = False
        self._update_button_states()

    def _populate_form(self) -> None:
        """Populate form fields from loaded config data."""
        if not self._config_data:
            return

        # Basic settings
        if "age" in self._config_data:
            self.age_spin.setValue(self._config_data["age"])
        if "trial_quantity" in self._config_data:
            self.trials_spin.setValue(self._config_data["trial_quantity"])
        if "calculate_til" in self._config_data:
            self.calculate_til_spin.setValue(self._config_data["calculate_til"])
        if "net_worth_target" in self._config_data:
            self.net_worth_target_spin.setValue(self._config_data["net_worth_target"])
        if "state" in self._config_data:
            self.state_edit.setText(self._config_data["state"])

        # Portfolio settings
        if "portfolio" in self._config_data:
            portfolio = self._config_data["portfolio"]
            if "current_net_worth" in portfolio:
                self.current_net_worth_spin.setValue(portfolio["current_net_worth"])
            if "tax_rate" in portfolio:
                self.tax_rate_spin.setValue(portfolio["tax_rate"])

            # Allocation
            if "allocation_strategy" in portfolio:
                alloc = portfolio["allocation_strategy"]
                if "flat" in alloc and "allocation" in alloc["flat"]:
                    flat_alloc = alloc["flat"]["allocation"]
                    if "US_Stock" in flat_alloc:
                        self.us_stock_spin.setValue(flat_alloc["US_Stock"])
                    if "US_Bond" in flat_alloc:
                        self.us_bond_spin.setValue(flat_alloc["US_Bond"])

        # Income settings
        if "income_profiles" in self._config_data and self._config_data["income_profiles"]:
            income = self._config_data["income_profiles"][0]
            if "starting_income" in income:
                self.starting_income_spin.setValue(income["starting_income"])
            if "tax_deferred_income" in income:
                self.tax_deferred_spin.setValue(income["tax_deferred_income"])
            if "yearly_raise" in income:
                self.yearly_raise_spin.setValue(income["yearly_raise"])
            if "last_date" in income:
                self.income_last_date_spin.setValue(income["last_date"])

        # Spending settings
        if "spending" in self._config_data and "profiles" in self._config_data["spending"]:
            profiles = self._config_data["spending"]["profiles"]
            if profiles:
                self.yearly_spending_spin.setValue(profiles[0]["yearly_amount"])

        # Social Security settings
        if "social_security_pension" in self._config_data:
            ss = self._config_data["social_security_pension"]
            if "trust_factor" in ss:
                self.ss_trust_spin.setValue(ss["trust_factor"])
            if "strategy" in ss:
                strategy = ss["strategy"]
                self.ss_early_check.setChecked(
                    strategy.get("early", {}).get("enabled", False)
                )
                self.ss_mid_check.setChecked(
                    strategy.get("mid", {}).get("chosen", False)
                )
                self.ss_late_check.setChecked(
                    strategy.get("late", {}).get("enabled", False)
                )

    def _mark_unsaved(self) -> None:
        """Mark configuration as having unsaved changes."""
        self._unsaved_changes = True
        self._update_button_states()

    def _update_button_states(self) -> None:
        """Update save/reset button states based on unsaved changes."""
        self.save_btn.setEnabled(self._unsaved_changes)
        self.reset_btn.setEnabled(self._unsaved_changes)

    def _save_config(self) -> bool:
        """
        Save configuration to file.

        Returns:
            True if save was successful, False otherwise
        """
        try:
            # Build config dictionary from form
            config_dict = self._build_config_dict()

            # Convert to YAML
            config_yaml = yaml.dump(config_dict, sort_keys=False, default_flow_style=False)

            # Validate and write
            write_config_file(config_text=config_yaml, config_path=self.config_path)

            self._unsaved_changes = False
            self._update_button_states()
            self.config_saved.emit(self.config_path)
            self.status_message.emit("Configuration saved successfully")

            QMessageBox.information(
                self, "Success", f"Configuration saved to {self.config_path}"
            )
            return True

        except ValidationError as e:
            QMessageBox.critical(
                self, "Validation Error", f"Configuration validation failed:\n{e}"
            )
            self.status_message.emit("Configuration validation failed")
            return False
        except Exception as e:
            QMessageBox.critical(
                self, "Error Saving Configuration", f"Failed to save configuration:\n{e}"
            )
            self.status_message.emit("Error saving configuration")
            return False

    def _build_config_dict(self) -> dict:
        """
        Build configuration dictionary from form values.

        Returns:
            Configuration dictionary
        """
        config = {
            "age": self.age_spin.value(),
            "trial_quantity": self.trials_spin.value(),
            "calculate_til": self.calculate_til_spin.value(),
            "net_worth_target": self.net_worth_target_spin.value(),
            "state": self.state_edit.text(),
            "portfolio": {
                "current_net_worth": self.current_net_worth_spin.value(),
                "tax_rate": self.tax_rate_spin.value(),
                "allocation_strategy": {
                    "flat": {
                        "chosen": self.flat_allocation_check.isChecked(),
                        "allocation": {
                            "US_Stock": self.us_stock_spin.value(),
                            "US_Bond": self.us_bond_spin.value(),
                        },
                    }
                },
            },
            "income_profiles": [
                {
                    "starting_income": self.starting_income_spin.value(),
                    "tax_deferred_income": self.tax_deferred_spin.value(),
                    "yearly_raise": self.yearly_raise_spin.value(),
                    "try_to_optimize": True,
                    "social_security_eligible": True,
                    "last_date": self.income_last_date_spin.value(),
                }
            ],
            "spending": {
                "spending_strategy": {"inflation_only": {"chosen": True}},
                "profiles": [{"yearly_amount": self.yearly_spending_spin.value()}],
            },
            "social_security_pension": {
                "trust_factor": self.ss_trust_spin.value(),
                "pension_eligible": False,
                "strategy": {
                    "early": {"enabled": self.ss_early_check.isChecked()},
                    "mid": {"chosen": self.ss_mid_check.isChecked()},
                    "late": {"enabled": self.ss_late_check.isChecked()},
                },
                "earnings_records": {},
            },
        }

        return config

    def _load_different_file(self) -> None:
        """Load a different configuration file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration File",
            str(self.config_path.parent),
            "YAML Files (*.yml *.yaml);;All Files (*)",
        )

        if file_path:
            self.config_path = Path(file_path)
            self.file_label.setText(f"Editing: {self.config_path}")
            self._load_config()

    def has_unsaved_changes(self) -> bool:
        """
        Check if there are unsaved changes.

        Returns:
            True if there are unsaved changes, False otherwise
        """
        return self._unsaved_changes

    def save_config(self) -> bool:
        """
        Public method to save configuration.

        Returns:
            True if save was successful, False otherwise
        """
        return self._save_config()

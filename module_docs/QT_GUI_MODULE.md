# Qt GUI Module Documentation

## Overview

This document provides comprehensive documentation for the Qt GUI frontend module of LifeFinances. This is an LLM-compatible reference that describes the module's architecture, usage, development process, and integration with the existing Flask application.

**Module Version:** 0.1.0
**Created:** 2024
**Framework:** PyQt6
**Python Version:** 3.10+

---

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Usage Guide](#usage-guide)
5. [Component Reference](#component-reference)
6. [Development Process](#development-process)
7. [Testing](#testing)
8. [Integration with Flask App](#integration-with-flask-app)
9. [Troubleshooting](#troubleshooting)
10. [Future Enhancements](#future-enhancements)

---

## Introduction

### Purpose

The Qt GUI module provides a native desktop application interface for LifeFinances, complementing the existing Flask web interface. It offers:

- **Form-based configuration builder** - Structured forms for creating/editing configurations
- **Asynchronous simulation runner** - Background execution with real-time progress tracking
- **Rich visualization** - Interactive charts and graphs of simulation results
- **Native desktop experience** - No browser required, faster interaction

### Key Principles

1. **Zero disruption** - Does not modify existing Flask application code
2. **Shared business logic** - Reuses all models and simulation code from `app/models/`
3. **Independent operation** - Can be used standalone or alongside Flask interface
4. **Test-driven** - Comprehensive headless tests ensure reliability
5. **LLM-friendly** - Clear structure and documentation for AI-assisted development

---

## Architecture

### High-Level Structure

```
LifeFinances/
├── qt_gui/                         # Qt GUI module (NEW)
│   ├── __init__.py                # Module initialization
│   ├── windows/                   # Main application windows
│   │   ├── __init__.py
│   │   └── main_window.py        # MainWindow with tabs
│   ├── widgets/                   # Reusable widgets
│   │   ├── __init__.py
│   │   ├── config_builder.py    # ConfigBuilderWidget
│   │   ├── simulation_runner.py # SimulationRunnerWidget
│   │   └── results_viewer.py    # ResultsViewerWidget
│   └── resources/                # UI resources (future: icons, etc.)
├── run_gui.py                     # Qt GUI entry point (NEW)
├── requirements/
│   └── qt.txt                     # Qt-specific dependencies (NEW)
├── tests/
│   └── qt_gui/                    # Qt GUI tests (NEW)
│       ├── __init__.py
│       ├── conftest.py           # Pytest fixtures
│       ├── test_config_builder.py
│       ├── test_simulation_runner.py
│       └── test_results_viewer.py
└── module_docs/                   # Module documentation (NEW)
    └── QT_GUI_MODULE.md          # This file
```

### Component Hierarchy

```
MainWindow (QMainWindow)
├── QTabWidget
│   ├── Tab 1: ConfigBuilderWidget
│   │   ├── Basic Settings (age, trials, etc.)
│   │   ├── Portfolio Settings (net worth, allocation)
│   │   ├── Income Settings
│   │   ├── Spending Settings
│   │   └── Social Security Settings
│   ├── Tab 2: SimulationRunnerWidget
│   │   ├── Configuration Summary
│   │   ├── Run/Stop Controls
│   │   ├── Progress Bar (real-time)
│   │   └── Simulation Log
│   └── Tab 3: ResultsViewerWidget
│       ├── Summary Statistics (success %)
│       ├── Net Worth Projection Chart
│       └── Data Table (first trial)
└── Status Bar
```

### Data Flow

```
User → ConfigBuilderWidget
         ↓ (save_config)
    config.yml file
         ↓ (reload_config)
    SimulationRunnerWidget
         ↓ (run simulation in thread)
    gen_simulation_results()
         ↓ (Results object)
    ResultsViewerWidget
         ↓ (display)
    Charts & Tables
```

### Thread Architecture

The Qt GUI uses threading to prevent UI freezing during long simulations:

```
Main Thread (UI)
    ↓
QThread (Worker Thread)
    ↓
SimulationWorker.run()
    ↓
gen_simulation_results() [500 trials]
    ↓
Signals back to Main Thread
    ↓
Update UI with results
```

---

## Installation & Setup

### Prerequisites

- Python 3.10+
- Virtual environment (recommended: `.venv`)
- LifeFinances base dependencies installed

### Step 1: Install Dependencies

```bash
# Activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install base dependencies
pip install -r requirements/dev.txt

# Install Qt GUI dependencies
pip install -r requirements/qt.txt
```

### Step 2: Verify Installation

```bash
# Test import
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"

# Test Qt GUI modules
python -c "import qt_gui; print(f'Qt GUI version: {qt_gui.__version__}')"
```

### Step 3: Run the GUI

```bash
# Launch Qt GUI
python run_gui.py
```

---

## Usage Guide

### Launching the Application

```bash
# From project root
python run_gui.py
```

The application will:
1. Set `SKIP_FLASK_INIT=1` to avoid Flask initialization
2. Initialize PyQt6 application
3. Create and display MainWindow
4. Load existing `config.yml` if available

### Creating a Configuration

1. **Navigate to "Configuration" tab**
2. **Fill in Basic Settings:**
   - Current Age (e.g., 30)
   - Number of Trials (e.g., 500)
   - Calculate Until Year (e.g., 2090)
   - Net Worth Target (e.g., 1500k)
   - State (e.g., California)

3. **Configure Portfolio:**
   - Current Net Worth (e.g., 250k)
   - Tax Rate (e.g., 0.1)
   - Allocation: US Stock % (e.g., 0.6), US Bond % (e.g., 0.4)

4. **Set Income Profile:**
   - Starting Income (e.g., 80k)
   - Tax Deferred Income (e.g., 10k)
   - Yearly Raise (e.g., 0.04 = 4%)
   - Last Date (e.g., 2035.25)

5. **Configure Spending:**
   - Yearly Spending (e.g., 60k)

6. **Social Security Settings:**
   - Trust Factor (e.g., 0.8)
   - Claiming Strategies (check: Early, Mid, Late)

7. **Click "Save Configuration"**

### Running a Simulation

1. **Navigate to "Run Simulation" tab**
2. **Review Configuration Summary** (displays loaded config)
3. **Click "Run Simulation"**
4. **Monitor Progress:**
   - Progress bar shows activity (currently indeterminate)
   - Log displays status messages
   - Stop button available to cancel

5. **Wait for Completion:**
   - Auto-switches to "Results" tab when done
   - Success message in status bar

### Viewing Results

1. **Summary Statistics:**
   - Success Rate (large, color-coded)
   - Total Trials, Successful, Failed counts

2. **Net Worth Projection Tab:**
   - Line chart showing all trial outcomes
   - Green lines = successful trials
   - Red lines = failed trials
   - Blue line = median projection

3. **Data Table Tab:**
   - Shows first trial in detail
   - Columns: date, net_worth, income, costs, etc.
   - Export to CSV button available

---

## Component Reference

### MainWindow (`qt_gui/windows/main_window.py`)

**Class:** `MainWindow(QMainWindow)`

**Purpose:** Top-level application window with tabbed interface

**Key Methods:**
- `__init__()` - Initialize window and tabs
- `_init_widgets()` - Create tab widgets
- `_connect_signals()` - Wire up signal/slot connections
- `_on_config_saved(config_path)` - Handle config save event
- `_on_simulation_completed(results)` - Handle simulation completion
- `closeEvent(event)` - Handle window close (checks unsaved changes)

**Signals:**
- None (uses child widget signals)

**Properties:**
- `config_path: Path` - Path to configuration file
- `tabs: QTabWidget` - Main tab container
- `config_builder: ConfigBuilderWidget` - Configuration tab
- `simulation_runner: SimulationRunnerWidget` - Simulation tab
- `results_viewer: ResultsViewerWidget` - Results tab

---

### ConfigBuilderWidget (`qt_gui/widgets/config_builder.py`)

**Class:** `ConfigBuilderWidget(QWidget)`

**Purpose:** Form-based configuration editor

**Key Methods:**
- `__init__(config_path, parent)` - Initialize widget
- `_init_ui()` - Create form interface
- `_init_basic_settings()` - Create basic settings form
- `_init_portfolio_settings()` - Create portfolio form
- `_init_income_settings()` - Create income form
- `_init_spending_settings()` - Create spending form
- `_init_social_security_settings()` - Create SS form
- `_load_config()` - Load config from file
- `_populate_form()` - Fill form from config data
- `_save_config()` - Save form to config file
- `_build_config_dict()` - Build config dict from form
- `_mark_unsaved()` - Mark changes as unsaved
- `has_unsaved_changes()` - Check for unsaved changes
- `save_config()` - Public save method

**Signals:**
- `config_saved(Path)` - Emitted when config is saved
- `status_message(str)` - Status updates for status bar

**Properties:**
- `config_path: Path` - Configuration file path
- `_unsaved_changes: bool` - Unsaved changes flag
- `_config_data: Optional[dict]` - Loaded config data

**Form Fields:**
- `age_spin: QSpinBox` - Current age
- `trials_spin: QSpinBox` - Number of trials
- `calculate_til_spin: QDoubleSpinBox` - Calculate until year
- `net_worth_target_spin: QDoubleSpinBox` - Net worth target
- `state_edit: QLineEdit` - State name
- `current_net_worth_spin: QDoubleSpinBox` - Current net worth
- `tax_rate_spin: QDoubleSpinBox` - Tax rate
- `us_stock_spin: QDoubleSpinBox` - US stock allocation
- `us_bond_spin: QDoubleSpinBox` - US bond allocation
- `starting_income_spin: QDoubleSpinBox` - Starting income
- `yearly_spending_spin: QDoubleSpinBox` - Yearly spending
- And more...

**Business Logic Integration:**
```python
from app.models.config import read_config_file, write_config_file, User
import yaml

# Load config
config_text = read_config_file(config_path=self.config_path)
self._config_data = yaml.safe_load(config_text)

# Save config
config_yaml = yaml.dump(config_dict, ...)
write_config_file(config_text=config_yaml, config_path=self.config_path)
```

---

### SimulationRunnerWidget (`qt_gui/widgets/simulation_runner.py`)

**Class:** `SimulationRunnerWidget(QWidget)`

**Purpose:** Run simulations with progress tracking

**Key Methods:**
- `__init__(config_path, parent)` - Initialize widget
- `_init_ui()` - Create UI elements
- `_load_config_info()` - Load and display config summary
- `_start_simulation()` - Start simulation in background thread
- `_stop_simulation()` - Request simulation stop
- `_on_progress_updated(current, total)` - Handle progress updates
- `_on_simulation_completed(results)` - Handle completion
- `_on_simulation_failed(error_msg)` - Handle errors
- `_on_thread_finished()` - Clean up thread
- `log_message(message)` - Add message to log
- `reload_config()` - Reload config information

**Signals:**
- `simulation_completed(object)` - Emitted with Results object
- `status_message(str)` - Status updates for status bar

**Properties:**
- `config_path: Path` - Configuration file path
- `worker: Optional[SimulationWorker]` - Background worker
- `worker_thread: Optional[QThread]` - Worker thread
- `_simulation_running: bool` - Simulation state flag

**Threading Model:**
```python
# Create worker and thread
self.worker = SimulationWorker(config_path=self.config_path)
self.worker_thread = QThread()

# Move worker to thread
self.worker.moveToThread(self.worker_thread)

# Connect signals
self.worker_thread.started.connect(self.worker.run)
self.worker.simulation_completed.connect(self._on_simulation_completed)

# Start thread
self.worker_thread.start()
```

---

### SimulationWorker (`qt_gui/widgets/simulation_runner.py`)

**Class:** `SimulationWorker(QObject)`

**Purpose:** Background worker for running simulations

**Key Methods:**
- `__init__(config_path)` - Initialize worker
- `run()` - Execute simulation (runs in QThread)
- `stop()` - Request stop

**Signals:**
- `progress_updated(int, int)` - Current, total progress
- `simulation_completed(object)` - Results object
- `simulation_failed(str)` - Error message
- `log_message(str)` - Log messages

**Business Logic Integration:**
```python
from app.models.simulator import gen_simulation_results
from app.models.config import get_config

# Load config
config = get_config(config_path=self.config_path)

# Run simulation
results = gen_simulation_results()

# Emit completion
self.simulation_completed.emit(results)
```

---

### ResultsViewerWidget (`qt_gui/widgets/results_viewer.py`)

**Class:** `ResultsViewerWidget(QWidget)`

**Purpose:** Display simulation results with charts and tables

**Key Methods:**
- `__init__(parent)` - Initialize widget
- `_init_ui()` - Create UI elements
- `display_results(results)` - Display Results object
- `_update_statistics()` - Update summary stats
- `_update_visualization()` - Update net worth chart
- `_update_data_table()` - Update data table
- `_export_to_csv()` - Export results to CSV
- `clear_results()` - Clear displayed results

**Signals:**
- `status_message(str)` - Status updates for status bar

**Properties:**
- `_results: Optional[Results]` - Stored results
- `_dataframes: Optional[list[pd.DataFrame]]` - Trial DataFrames
- `canvas: MatplotlibCanvas` - Chart canvas
- `data_table: QTableWidget` - Data table

**Visualization Details:**

The widget plots up to 50 trials on the net worth chart:
- Green lines: Successful trials (net worth > 0 at end)
- Red lines: Failed trials (net worth <= 0)
- Blue line: Median projection across all trials
- Horizontal dashed line: Net worth = 0

**Business Logic Integration:**
```python
from app.models.simulator import Results

# Get data
self._dataframes = results.as_dataframes()
success_pct = results.calc_success_percentage()

# Access trial data
for trial in results.trials:
    is_successful = trial.is_successful
```

---

### MatplotlibCanvas (`qt_gui/widgets/results_viewer.py`)

**Class:** `MatplotlibCanvas(FigureCanvas)`

**Purpose:** Embed Matplotlib plots in Qt

**Key Methods:**
- `__init__(parent, width, height, dpi)` - Initialize canvas

**Properties:**
- `figure: Figure` - Matplotlib figure
- `axes: Axes` - Matplotlib axes

---

## Development Process

### Adding New Features

When extending the Qt GUI module, follow this process:

#### 1. Planning

- Review existing architecture
- Identify affected components
- Check for reusable business logic in `app/models/`
- Design UI mockup (paper or tool)

#### 2. Write Tests First (TDD)

```python
# tests/qt_gui/test_new_feature.py
def test_new_feature_initialization(qapp):
    """Test new feature initializes correctly."""
    widget = NewFeatureWidget()
    assert widget is not None
```

#### 3. Implement Feature

```python
# qt_gui/widgets/new_feature.py
class NewFeatureWidget(QWidget):
    """New feature widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
```

#### 4. Integrate with MainWindow

```python
# qt_gui/windows/main_window.py
def _init_widgets(self):
    # ... existing widgets ...
    self.new_feature = NewFeatureWidget()
    self.tabs.addTab(self.new_feature, "New Feature")
```

#### 5. Run Tests

```bash
# Run Qt GUI tests
pytest tests/qt_gui/

# Run specific test
pytest tests/qt_gui/test_new_feature.py -v
```

#### 6. Update Documentation

- Add component reference to this document
- Update usage guide if user-facing
- Document any new dependencies

---

### Code Style Guidelines

Follow LifeFinances project constitution (see `.specify/memory/constitution.md`):

1. **Type Hints:** All public methods must have type hints
2. **Docstrings:** Google or NumPy style for all classes/methods
3. **Named Arguments:** Use named arguments for multi-parameter calls
4. **Object Models:** Prefer classes over dictionaries
5. **Pylint:** Minimum 8.0/10.0 score
6. **Testing:** TDD required, 80%+ coverage

**Qt-Specific Guidelines:**

- Use signals/slots for component communication
- Keep business logic out of widgets (import from `app/models/`)
- Use threading for long-running operations
- Follow Qt naming conventions (camelCase for methods)

---

### Environment Setup for Development

```bash
# 1. Set environment variable (prevents Flask init)
export SKIP_FLASK_INIT=1  # Linux/Mac
set SKIP_FLASK_INIT=1     # Windows CMD
$env:SKIP_FLASK_INIT="1"  # Windows PowerShell

# 2. Run GUI in development mode
python run_gui.py

# 3. Run tests in headless mode
export QT_QPA_PLATFORM=offscreen  # Automatically set by conftest.py
pytest tests/qt_gui/ -v

# 4. Run single test
pytest tests/qt_gui/test_config_builder.py::test_config_builder_initialization -v
```

---

## Testing

### Test Structure

```
tests/qt_gui/
├── __init__.py
├── conftest.py                   # Fixtures (qapp, test_config_path, etc.)
├── test_config_builder.py        # ConfigBuilderWidget tests
├── test_simulation_runner.py     # SimulationRunnerWidget tests
└── test_results_viewer.py        # ResultsViewerWidget tests
```

### Key Fixtures

**`qapp`** - QApplication instance for headless testing
```python
@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
```

**`test_config_path`** - Temporary config file path
```python
@pytest.fixture
def test_config_path(tmp_path: Path) -> Path:
    return tmp_path / "test_config.yml"
```

**`sample_config_content`** - Sample YAML configuration
```python
@pytest.fixture
def sample_config_content() -> str:
    return """
age: 30
trial_quantity: 10
# ... full config ...
"""
```

### Running Tests

```bash
# All Qt GUI tests
pytest tests/qt_gui/

# With verbose output
pytest tests/qt_gui/ -v

# With coverage
pytest tests/qt_gui/ --cov=qt_gui --cov-report=html

# Single test file
pytest tests/qt_gui/test_config_builder.py

# Single test function
pytest tests/qt_gui/test_config_builder.py::test_config_builder_initialization -v

# Headless mode (automatic via conftest.py)
# No additional flags needed - QT_QPA_PLATFORM=offscreen is set automatically
```

### Test Coverage Requirements

Per project constitution:
- **Minimum overall:** 80%
- **Business logic:** 95%+
- **Qt widgets:** 80%+ (focus on logic, not UI rendering)

**What to Test:**
- Widget initialization
- Signal/slot connections
- Data loading and saving
- Form validation
- Error handling
- State management

**What NOT to Test:**
- Qt framework internals
- Visual appearance
- Exact pixel positioning

---

## Integration with Flask App

### Shared Components

Both Flask and Qt GUI share:

1. **Business Logic:**
   - `app/models/config.py` - Configuration models and I/O
   - `app/models/simulator.py` - Simulation engine
   - `app/models/controllers/` - Financial controllers
   - `app/models/financial/` - State models
   - `app/data/` - Data files and constants

2. **Configuration File:**
   - `config.yml` - Both interfaces read/write same file
   - Validation via Pydantic `User` model

3. **Testing Infrastructure:**
   - `tests/sample_configs/` - Sample configurations
   - `tests/conftest.py` - Shared fixtures (partially)

### Separation of Concerns

**Flask-Specific (NOT imported by Qt):**
- `app/__init__.py` - Flask app factory
- `app/routes/` - HTTP route handlers
- `app/templates/` - Jinja2 templates

**Qt-Specific (NOT used by Flask):**
- `qt_gui/` - All Qt GUI code
- `run_gui.py` - Qt entry point
- `tests/qt_gui/` - Qt-specific tests

**Environment Variable:**
```python
# run_gui.py sets this before imports
os.environ["SKIP_FLASK_INIT"] = "1"

# app/__init__.py checks this
_skip_flask_init = os.environ.get("SKIP_FLASK_INIT", "0") == "1"
if not _skip_flask_init:
    # Flask imports here
```

### Running Both Interfaces

```bash
# Terminal 1: Flask web interface
flask run
# Access at http://localhost:5000

# Terminal 2: Qt GUI
python run_gui.py
# Native desktop window
```

Both can operate simultaneously on the same `config.yml` file. Changes in one will be visible in the other after reload/restart.

---

## Troubleshooting

### Common Issues

#### 1. Import Error: "No module named 'PyQt6'"

**Problem:** PyQt6 not installed

**Solution:**
```bash
pip install -r requirements/qt.txt
```

---

#### 2. Import Error: "No module named 'app'"

**Problem:** Project root not in Python path

**Solution:**
```bash
# Run from project root
cd /path/to/LifeFinances
python run_gui.py
```

---

#### 3. Qt Platform Plugin Error

**Problem:** Qt cannot find platform plugin (Linux)

**Solution:**
```bash
# Install platform plugins
sudo apt-get install libxcb-xinerama0

# Or force offscreen platform
export QT_QPA_PLATFORM=offscreen
```

---

#### 4. Simulation Hangs UI

**Problem:** UI freezes during simulation

**Solution:** Ensure simulation runs in QThread (already implemented in SimulationRunnerWidget)

---

#### 5. Tests Fail with Display Error

**Problem:** Tests try to create windows on headless system

**Solution:** Ensure `conftest.py` sets `QT_QPA_PLATFORM=offscreen`:
```python
# tests/qt_gui/conftest.py
os.environ["QT_QPA_PLATFORM"] = "offscreen"
```

---

#### 6. Configuration Validation Fails

**Problem:** Invalid YAML or config structure

**Solution:**
- Check YAML syntax
- Compare with `tests/sample_configs/full_config.yml`
- Review Pydantic validation errors in dialog

---

#### 7. Matplotlib Backend Error

**Problem:** Matplotlib can't find Qt backend

**Solution:**
```bash
# Reinstall matplotlib with Qt support
pip uninstall matplotlib
pip install matplotlib
```

---

### Debug Mode

Enable verbose logging:

```python
# In run_gui.py, add before app.exec()
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Future Enhancements

### Planned Features

1. **Enhanced Progress Tracking**
   - Modify `gen_simulation_results()` to support progress callbacks
   - Show deterministic progress bar (trial X of Y)

2. **Advanced Visualization**
   - Percentile bands (10th, 25th, 50th, 75th, 90th)
   - Multiple chart types (histogram, box plot)
   - Interactive charts (zoom, pan, tooltips)

3. **Configuration Templates**
   - Save/load configuration presets
   - Template library for common scenarios

4. **Multi-Configuration Comparison**
   - Load multiple configs
   - Compare success rates side-by-side
   - Diff viewer for configs

5. **Export Enhancements**
   - Export all trials to CSV (not just first)
   - Export charts as PNG/PDF
   - Generate report PDF

6. **Advanced Config Builder**
   - Partner configuration section
   - Kids configuration section
   - TPAW planner settings
   - Disability insurance calculator integration

7. **Real-time Config Validation**
   - Validate as user types
   - Show validation errors inline
   - Suggest corrections

8. **Dark Mode**
   - Support system dark mode
   - Manual theme toggle

### Technical Debt

1. **Progress Callbacks** - Simulator doesn't currently support progress updates
2. **Form Validation** - Basic validation only, could be more comprehensive
3. **Configuration Sections** - Only basic settings exposed, not all features
4. **Chart Interactivity** - Static matplotlib charts, could use PyQt6-Charts
5. **Undo/Redo** - No undo functionality for config edits

---

## API Reference

### Environment Variables

| Variable | Description | Values | Default |
|----------|-------------|--------|---------|
| `SKIP_FLASK_INIT` | Skip Flask initialization | "0" or "1" | "0" |
| `QT_QPA_PLATFORM` | Qt platform plugin | "offscreen", "xcb", etc. | Auto-detect |

### Import Paths

```python
# Widgets
from qt_gui.widgets.config_builder import ConfigBuilderWidget
from qt_gui.widgets.simulation_runner import SimulationRunnerWidget, SimulationWorker
from qt_gui.widgets.results_viewer import ResultsViewerWidget, MatplotlibCanvas

# Windows
from qt_gui.windows.main_window import MainWindow

# Business logic (shared with Flask)
from app.models.config import User, read_config_file, write_config_file, get_config
from app.models.simulator import gen_simulation_results, Results, SimulationEngine
```

### Dependencies

**Production (requirements/qt.txt):**
- PyQt6 == 6.6.1
- PyQt6-Charts == 6.6.0
- matplotlib == 3.8.2

**Development (requirements/dev.txt):**
- pytest == 7.4.3
- pytest-qt (if added)

---

## Conclusion

The Qt GUI module provides a robust, maintainable desktop interface for LifeFinances. Its clean separation from the Flask application ensures both interfaces can evolve independently while sharing the same battle-tested business logic.

For questions or contributions, refer to:
- Project constitution: `.specify/memory/constitution.md`
- Main documentation: `CLAUDE.md`
- Flask app structure: `README.md`

---

**Document Version:** 1.0
**Last Updated:** 2024
**Maintained by:** LifeFinances Development Team

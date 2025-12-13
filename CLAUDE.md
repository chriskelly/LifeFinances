# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LifeFinances is a Monte Carlo retirement and financial planning simulator with both **Flask web interface** and **PyQt6 desktop GUI**. It performs probabilistic simulations to assess the success of financial plans based on various economic scenarios, life events, and investment strategies.

**Core Focus Areas:**
- Retirement planning with Monte Carlo simulations (default 500 trials)
- Social Security and pension claiming strategies (early, mid, late, net_worth_based)
- Disability insurance calculations
- Investment allocation strategies (flat, net-worth-pivot)
- Tax optimization and life events (children support, income changes)

**User Interfaces:**
- **Flask Web App** - Browser-based interface with YAML config editor
- **Qt Desktop GUI** - Native desktop application with form-based config builder (see [module_docs/QT_GUI_MODULE.md](module_docs/QT_GUI_MODULE.md))

## Development Commands

### Setup & Installation
```bash
# Install production dependencies
pip install -r requirements/common.txt

# Install development dependencies (includes pytest, pylint, black)
pip install -r requirements/dev.txt

# Install Qt GUI dependencies (for desktop interface)
pip install -r requirements/qt.txt

# Copy a sample configuration to start
cp tests/sample_configs/full_config.yml config.yml
```

### Running the Application

**Flask Web Interface:**
```bash
# Start Flask development server (without Docker)
flask run
# Accessible at http://localhost:5000

# With DevContainer (VS Code):
# - Open in Dev Container (auto-installs dependencies)
# - Run `flask run` (auto-forwards port 3500)

# Entry point
python run.py
```

**Qt Desktop GUI:**
```bash
# Launch PyQt6 desktop application
python run_gui.py

# The GUI provides:
# - Form-based configuration builder
# - Asynchronous simulation runner with progress bar
# - Rich visualization of results with charts and tables
```

### Testing
```bash
# Run all tests (includes Flask and Qt GUI tests)
pytest

# Run specific test file
pytest tests/models/test_simulator.py

# Run Qt GUI tests (headless)
pytest tests/qt_gui/

# Run with coverage
pytest --cov=app --cov=qt_gui --cov-report=html

# Run with coverage report
pytest --cov=app --cov-report=html

# Docker-based testing (recommended for CI)
make test        # Run full test suite in Docker
make all         # Down, build, up, test (full CI cycle)
make build       # Build Docker containers
make up          # Start containers
make down        # Stop containers
```

### Code Quality
```bash
# Linting (minimum 8.0/10.0 required)
pylint app/

# Type checking
pyright

# Format code
black app/ tests/
```

### Performance Profiling
```bash
# Profile simulation performance
make profile
# Generates cProfile output and opens snakeviz visualization
```

### Running Single Tests
```bash
# Run a specific test by name
pytest tests/models/test_simulator.py::test_gen_all_trials -v

# Run tests matching a pattern
pytest -k "social_security" -v

# Run tests marked as slow
pytest -m slow
```

## Architecture Overview

### High-Level Structure

The application uses a **Controller Pattern** where specialized controllers manage different financial domains (allocation, income, Social Security, pension, annuity). Each simulation trial generates quarterly intervals using shared economic data and user-specific strategies.

```
SimulationEngine
  └─ gen_all_trials() → Creates 500 SimulationTrial instances
      ├─ Shared Controllers (allocation, job_income)
      ├─ Trial-specific Controllers (economic, SS, pension, annuity)
      └─ Generates Intervals (quarterly periods)
          ├─ State (snapshot: date, net_worth, inflation)
          ├─ StateChange (income, costs, taxes, portfolio return)
          └─ Controllers (strategy execution per interval)
```

### Core Components

**Configuration Layer** ([app/models/config.py:1](app/models/config.py#L1))
- Pydantic models for YAML configuration validation
- Hierarchical structure: `User`, `Portfolio`, `Spending`, `SocialSecurity`, `Pension`, `IncomeProfile`, `Partner`
- Multi-strategy support with `StrategyConfig` and `StrategyOptions` base classes
- Comprehensive validation with custom validators

**Simulation Engine** ([app/models/simulator.py:1](app/models/simulator.py#L1))
- `SimulationEngine` orchestrates multiple trials
- `SimulationTrial` generates a single lifetime simulation
- `Results` aggregates trial data into Pandas DataFrames
- Quarterly interval generation from user age to `calculate_til` date

**Economic Data Controller** ([app/models/controllers/economic_data.py:1](app/models/controllers/economic_data.py#L1))
- Generates correlated random economic scenarios using multivariate normal distribution
- Loads asset statistics and correlations from CSV files ([app/data/variable_statistics.csv:1](app/data/variable_statistics.csv#L1), [app/data/variable_correlation.csv:1](app/data/variable_correlation.csv#L1))
- `CsvVariableMixRepo` → `EconomicEngine` → `EconomicTrialData` → `Controller`
- Assets: US_Stock, US_Bond, Intl_ex_US_Stock, TIPS, Treasuries (various), REIT, Commodities, Gold

**Financial State Models** ([app/models/financial/](app/models/financial/))
- `State`: Snapshot of financial position at a point in time
- `StateChange`: Breakdown of income, costs, taxes, and portfolio returns
- `Interval`: Quarterly period containing state, state changes, and controllers
- `Taxes`: Federal income tax, Medicare, Social Security, portfolio taxes

**Strategy Controllers** ([app/models/controllers/](app/models/controllers/))
- Each controller inherits from base `Controller` pattern
- `allocation.py`: Portfolio allocation by strategy (flat or net-worth pivot)
- `job_income.py`: Salary progression based on income profiles
- `social_security.py`: Benefit calculation and claiming strategies
- `pension.py`: Pension benefit claiming strategies
- `annuity.py`: Annuity purchase and payout logic

**Flask Application** ([app/__init__.py:1](app/__init__.py#L1))
- Factory pattern via `create_app()`
- Routes: Index (GET/POST for config form), API blueprint
- Config validation → Simulation → Results rendering

### Data Sources

**Asset Data** ([app/data/README.md:1](app/data/README.md#L1)):
- Correlation data from Portfolio Visualizer
- Historical returns and standard deviations
- Inflation data from Bureau of Labor Statistics (CPI)

**Configuration Format** (YAML):
- Sample configs: [tests/sample_configs/](tests/sample_configs/)
- `full_config.yml`: Complete example with all options
- `min_config_income.yml`: Minimal config using income profiles
- `min_config_net_worth.yml`: Minimal config using net worth only

## Code Quality Requirements (Constitution v1.2.0)

The project enforces strict governance through [.specify/memory/constitution.md:1](.specify/memory/constitution.md#L1):

### Mandatory Standards
- **Pylint**: Minimum 8.0/10.0 score required
- **Type Hints**: All public functions and methods must include type hints
- **Documentation**: Module, class, and public function docstrings mandatory (Google or NumPy style)
- **Object Models**: Favor classes/dataclasses/Pydantic models over plain dictionaries
- **Named Arguments**: Multi-parameter functions must be called with named arguments
- **Test-Driven Development (TDD)**: Tests written before implementation for all application code
- **Test Coverage**: 80% minimum overall, 95%+ for business logic (financial calculations, state transitions, simulation)

### Testing Exception
Standalone scripts/notebooks NOT used as inputs for the simulator or Flask app MAY be exempted from testing requirements. All code that is imported, executed, or referenced by the application MUST follow TDD and testing standards.

### Code Organization
- Type checking via `pyrightconfig.json`
- Test structure mirrors source code under `tests/`
- Pytest fixtures in `tests/conftest.py`
- No circular dependencies allowed
- Imports organized: stdlib, third-party, local

## Key Design Patterns

1. **Controller Pattern**: Each financial domain has a dedicated controller accepting config and generating interval-level data
2. **Factory Pattern**: Flask app creation via `create_app()`
3. **Strategy Pattern**: Multiple allocation/claiming strategies with polymorphic behavior via `StrategyConfig`
4. **Composition Over Inheritance**: Controllers composed into trials, not deep hierarchies
5. **Interval-Based Simulation**: Quarterly time steps for consistent calculations
6. **Configuration-Driven**: All user preferences centralized in YAML config with Pydantic validation

## Important File Locations

**Entry Points:**
- [run.py:1](run.py#L1) - Flask web application entry point (port 3500)
- [run_gui.py:1](run_gui.py#L1) - Qt desktop GUI entry point

**Core Business Logic:**
- [app/models/config.py:1](app/models/config.py#L1) (616 lines) - Configuration models
- [app/models/simulator.py:1](app/models/simulator.py#L1) (260 lines) - Simulation engine
- [app/models/controllers/economic_data.py:1](app/models/controllers/economic_data.py#L1) (352 lines) - Economic simulation

**Qt GUI Components:**
- [qt_gui/windows/main_window.py:1](qt_gui/windows/main_window.py#L1) - Main Qt window with tabs
- [qt_gui/widgets/config_builder.py:1](qt_gui/widgets/config_builder.py#L1) - Form-based config editor
- [qt_gui/widgets/simulation_runner.py:1](qt_gui/widgets/simulation_runner.py#L1) - Async simulation with progress
- [qt_gui/widgets/results_viewer.py:1](qt_gui/widgets/results_viewer.py#L1) - Charts and data tables

**Testing:**
- [tests/conftest.py:1](tests/conftest.py#L1) - Pytest fixtures (app, sample_config_data, sample_user, first_state)
- [tests/models/test_simulator.py:1](tests/models/test_simulator.py#L1) (136 lines) - Simulation tests
- [tests/qt_gui/conftest.py:1](tests/qt_gui/conftest.py#L1) - Qt GUI test fixtures (qapp, headless mode)
- [tests/qt_gui/](tests/qt_gui/) - Qt GUI component tests

**Configuration:**
- [.devcontainer/devcontainer.json:1](.devcontainer/devcontainer.json#L1) - Dev Container setup
- [.github/workflows/main_ci.yml:1](.github/workflows/main_ci.yml#L1) - GitHub Actions CI
- [pyrightconfig.json:1](pyrightconfig.json#L1) - Type checking config

**Documentation:**
- [module_docs/QT_GUI_MODULE.md:1](module_docs/QT_GUI_MODULE.md#L1) - Comprehensive Qt GUI documentation

## Common Development Workflows

### Adding a New Financial Strategy

1. Define strategy options in [app/models/config.py:1](app/models/config.py#L1) as a `StrategyOptions` subclass
2. Add strategy config to parent `StrategyConfig` class
3. Implement controller logic in [app/models/controllers/](app/models/controllers/)
4. Write tests first (TDD) in corresponding `tests/models/controllers/` file
5. Update sample configs in [tests/sample_configs/](tests/sample_configs/) if needed
6. Ensure pylint >= 8.0 and type hints are complete

### Modifying Simulation Logic

1. Identify affected component: `SimulationEngine`, `SimulationTrial`, or `Interval`
2. Write failing tests first (TDD) in [tests/models/test_simulator.py:1](tests/models/test_simulator.py#L1)
3. Implement changes with type hints and docstrings
4. Verify test coverage >= 95% for business logic changes
5. Run `make profile` to check performance impact

### Adding API Endpoints

1. Define route in [app/routes/api.py:1](app/routes/api.py#L1) using blueprint pattern
2. Write integration tests in [tests/test_routes.py:1](tests/test_routes.py#L1) first (TDD)
3. Implement endpoint with input validation and error handling
4. Ensure response times < 2 seconds for interactive endpoints
5. Document API behavior in docstrings

### Working with Configuration

Sample configurations demonstrate different use cases:
- [tests/sample_configs/full_config.yml:1](tests/sample_configs/full_config.yml#L1) - All features enabled
- [tests/sample_configs/min_config_income.yml:1](tests/sample_configs/min_config_income.yml#L1) - Income profile based
- [tests/sample_configs/min_config_net_worth.yml:1](tests/sample_configs/min_config_net_worth.yml#L1) - Net worth based

Configuration is validated via Pydantic on load. See [app/models/config.py:1](app/models/config.py#L1) for schema details.

## Technology Stack

**Core:**
- **Python 3.10** (required version)
- **Pydantic 2.4.2** - Configuration validation and models
- **NumPy 1.26.1** - Numerical computation and random number generation
- **Pandas 2.1.2** - Data manipulation and DataFrame output
- **PyYAML 6.0.1** - YAML parsing

**Web Interface:**
- **Flask 3.0.0** - Web framework

**Desktop GUI:**
- **PyQt6 6.6.1** - Qt6 bindings for Python
- **PyQt6-Charts 6.6.0** - Chart widgets
- **Matplotlib 3.8.2** - Advanced plotting

**Development:**
- **pytest 7.4.3** - Testing framework
- **pylint 3.0.2** - Code quality analysis
- **Docker & Docker Compose** - Containerization and CI

## Qt GUI Module

The Qt desktop GUI provides an alternative to the Flask web interface with:

- **Form-based configuration** - Structured forms instead of YAML editing
- **Async simulation** - Background execution with progress tracking
- **Rich visualization** - Interactive charts and data tables
- **Shared business logic** - Uses same simulation engine as Flask

**Quick Start:**
```bash
pip install -r requirements/qt.txt
python run_gui.py
```

**Full Documentation:** [module_docs/QT_GUI_MODULE.md](module_docs/QT_GUI_MODULE.md)

**Architecture:**
- Zero disruption to Flask app (separate module)
- Headless tests for all components
- Threading for UI responsiveness
- Reuses all business logic from `app/models/`

## Additional Resources

- **Figma Board**: [Visual representation of intended structure](https://www.figma.com/file/UddWSekF9Sl6REDWII9dtr/LifeFinances-Functional-Tree?type=whiteboard&node-id=0%3A1&t=p6KDxEXCU2BdB7MZ-1)
- **Asset Data Sources**: [app/data/README.md:1](app/data/README.md#L1)
- **Project Constitution**: [.specify/memory/constitution.md:1](.specify/memory/constitution.md#L1)
- **Qt GUI Module Documentation**: [module_docs/QT_GUI_MODULE.md:1](module_docs/QT_GUI_MODULE.md#L1)

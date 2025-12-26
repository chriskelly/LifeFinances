@echo off
REM Pre-commit CI Pipeline Check for LifeFinances
REM This script mimics the exact CI pipeline from Makefile
REM Equivalent to running: make test lint
REM Run this script from the project root directory

echo ========================================
echo LifeFinances CI Pipeline Check
echo Equivalent to: make test lint
echo ========================================
echo.

REM Change to project root if not already there
cd /d "%~dp0"

REM Activate virtual environment
call .venv\Scripts\activate.bat >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Make sure .venv exists. Run: python -m venv .venv
    exit /b 1
)

REM Run tests (make test)
echo [1/4] Running test suite...
echo Command: pytest tests
python -m pytest tests
if errorlevel 1 (
    echo.
    echo ✗ FAILED: Tests failed
    echo Fix the failing tests before committing
    exit /b 1
)
echo ✓ Tests passed
echo.

REM Run ruff linting check (make ruff-check)
echo [2/4] Running ruff linting check...
echo Command: ruff check .
python -m ruff check .
if errorlevel 1 (
    echo.
    echo ✗ FAILED: Ruff linting errors detected
    echo Fix linting errors or run: python -m ruff check --fix .
    exit /b 1
)
echo ✓ Ruff check passed
echo.

REM Run ruff format check (make ruff-format-check)
echo [3/4] Running ruff format check...
echo Command: ruff format --check .
python -m ruff format --check .
if errorlevel 1 (
    echo.
    echo ✗ FAILED: Code formatting issues detected
    echo Fix by running: python -m ruff format .
    exit /b 1
)
echo ✓ Ruff format passed
echo.

REM Run pyright type checking (make pyright)
echo [4/4] Running pyright type checking...
echo Command: pyright
python -m pyright
if errorlevel 1 (
    echo.
    echo ✗ FAILED: Pyright type checking found issues
    echo Fix type errors before committing
    exit /b 1
)
echo ✓ Pyright passed
echo.

echo ========================================
echo ✓ ALL CI CHECKS PASSED!
echo ========================================
echo.
echo Your code is ready to commit and push.
echo The CI pipeline will pass.
echo.
pause

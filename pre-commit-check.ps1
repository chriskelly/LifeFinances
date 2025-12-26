# Pre-commit CI Pipeline Check for LifeFinances
# This script mimics the exact CI pipeline from Makefile
# Equivalent to running: make test lint
# Run this script from the project root directory: .\pre-commit-check.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "LifeFinances CI Pipeline Check" -ForegroundColor Cyan
Write-Host "Equivalent to: make test lint" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to script directory (project root)
Set-Location $PSScriptRoot

# Check if virtual environment exists
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found" -ForegroundColor Red
    Write-Host "Create one with: python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

# Run tests (make test)
Write-Host "[1/4] Running test suite..." -ForegroundColor Yellow
Write-Host "Command: pytest tests" -ForegroundColor Gray
& .venv\Scripts\python.exe -m pytest tests
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ FAILED: Tests failed" -ForegroundColor Red
    Write-Host "Fix the failing tests before committing" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Tests passed" -ForegroundColor Green
Write-Host ""

# Run ruff linting check (make ruff-check)
Write-Host "[2/4] Running ruff linting check..." -ForegroundColor Yellow
Write-Host "Command: ruff check ." -ForegroundColor Gray
& .venv\Scripts\python.exe -m ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ FAILED: Ruff linting errors detected" -ForegroundColor Red
    Write-Host "Fix linting errors or run: python -m ruff check --fix ." -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Ruff check passed" -ForegroundColor Green
Write-Host ""

# Run ruff format check (make ruff-format-check)
Write-Host "[3/4] Running ruff format check..." -ForegroundColor Yellow
Write-Host "Command: ruff format --check ." -ForegroundColor Gray
& .venv\Scripts\python.exe -m ruff format --check .
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ FAILED: Code formatting issues detected" -ForegroundColor Red
    Write-Host "Fix by running: python -m ruff format ." -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Ruff format passed" -ForegroundColor Green
Write-Host ""

# Run pyright type checking (make pyright)
Write-Host "[4/4] Running pyright type checking..." -ForegroundColor Yellow
Write-Host "Command: pyright" -ForegroundColor Gray
& .venv\Scripts\python.exe -m pyright
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "✗ FAILED: Pyright type checking found issues" -ForegroundColor Red
    Write-Host "Fix type errors before committing" -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Pyright passed" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ ALL CI CHECKS PASSED!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your code is ready to commit and push." -ForegroundColor Cyan
Write-Host "The CI pipeline will pass." -ForegroundColor Cyan
Write-Host ""

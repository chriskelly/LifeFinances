#!/usr/bin/env bash
set -euo pipefail

# Copy default config if none exists
if [ ! -f config.yml ]; then
    cp backend/tests/sample_configs/full_config.yml config.yml
fi

# Install Python backend dependencies
uv sync --locked --project backend

# Install pre-commit hooks
pre-commit install

# Install frontend dependencies if package.json is present
if [ -f frontend/package.json ]; then
    npm install --prefix frontend
fi

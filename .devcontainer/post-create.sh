#!/usr/bin/env bash
set -euo pipefail

# When the workspace is bind-mounted from a host with a different UID (any CI
# runner using devcontainers/ci, and some local Linux setups), git refuses to
# operate on /workspace with "dubious ownership". pre-commit's error in that
# case is the misleading "git failed. Is it installed, and are you in a Git
# repository directory?". Mark the workspace safe up front so subsequent git
# commands in this script (and in pre-commit hooks) succeed regardless of UID.
git config --global --add safe.directory /workspace

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

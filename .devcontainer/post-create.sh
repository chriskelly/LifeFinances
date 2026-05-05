#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." >/dev/null 2>&1 && pwd)"
cd "$REPO_ROOT"

# Copy default config if none exists
if [ ! -f config.yml ]; then
    cp backend/tests/sample_configs/full_config.yml config.yml
fi

# Install Python backend dependencies
uv sync --locked --project backend

# Install pre-commit hooks
if [ -z "${CI:-}" ] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    pre-commit install
fi

# Install frontend dependencies if package.json is present
if [ -f frontend/package.json ]; then
    npm install --prefix frontend
fi

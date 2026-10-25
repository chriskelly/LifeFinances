#!/bin/bash
# LifeFinances — macOS launcher. Double-click in Finder to start the app locally.
#
# Starts uvicorn on 127.0.0.1 and opens the default browser once the app answers.
# Logs stay in this Terminal window; Ctrl+C stops the server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

PREFERRED_PORT=8000
LAST_FALLBACK_PORT=8010
READY_TIMEOUT_SECONDS=30

# uv may place the environment outside .venv; the sync stamp must live where it actually is.
VENV_DIR="${UV_PROJECT_ENVIRONMENT:-.venv}"
[[ "$VENV_DIR" = /* ]] || VENV_DIR="$REPO_ROOT/$VENV_DIR"
SYNC_STAMP="$VENV_DIR/.lifefinances-synced"

# Finder launches .command files with a minimal PATH; add the usual uv locations.
export PATH="$PATH:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin"

stop_watcher() {
  # Only kill it while bash still tracks it as a job, so a finished watcher's recycled
  # PID can never be hit hours later when the server finally stops.
  local job
  for job in $(jobs -p); do
    if [[ "$job" == "${WATCHER_PID:-}" ]]; then
      kill "$job" 2>/dev/null || true
      return
    fi
  done
}

pause_on_error() {
  # Stop a late "did not answer" watcher message from landing under the real error.
  stop_watcher
  echo >&2
  echo "LifeFinances: $1" >&2
  shift
  for line in "$@"; do
    echo "  $line" >&2
  done
  read -r -p "Press Return to close this window..." _ || true
  exit 1
}

if [[ ! -f "$REPO_ROOT/pyproject.toml" ]]; then
  pause_on_error "pyproject.toml is missing next to LifeFinances.command." \
    "Keep LifeFinances.command in the LifeFinances repository root."
fi

if ! command -v uv >/dev/null 2>&1; then
  pause_on_error "'uv' was not found on PATH." \
    "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh" \
    "Then double-click LifeFinances.command again."
fi

# Probe a static asset instead of "/": "/" runs the cached simulation, so it can take
# seconds on a cold start, and this file exists only in this app.
app_answers() {
  curl --silent --fail --noproxy '*' --max-time 2 --output /dev/null "http://127.0.0.1:$1/static/style.css" 2>/dev/null
}

port_in_use() {
  nc -z -w 1 127.0.0.1 "$1" >/dev/null 2>&1
}

needs_sync() {
  local stamp="$SYNC_STAMP"
  [[ -f "$stamp" ]] || return 0
  [[ "$REPO_ROOT/pyproject.toml" -nt "$stamp" ]] || [[ "$REPO_ROOT/uv.lock" -nt "$stamp" ]]
}

# Reuse a server that is already running instead of starting a second one.
if port_in_use "$PREFERRED_PORT"; then
  if app_answers "$PREFERRED_PORT"; then
    echo "LifeFinances is already running at http://127.0.0.1:$PREFERRED_PORT/"
    open "http://127.0.0.1:$PREFERRED_PORT/"
    exit 0
  fi
  PORT=""
  for ((candidate = PREFERRED_PORT + 1; candidate <= LAST_FALLBACK_PORT; candidate++)); do
    if ! port_in_use "$candidate"; then
      PORT="$candidate"
      break
    fi
  done
  if [[ -z "$PORT" ]]; then
    pause_on_error "ports ${PREFERRED_PORT}-${LAST_FALLBACK_PORT} are all in use." \
      "Stop one of the processes using them, then double-click again."
  fi
  echo "LifeFinances: port $PREFERRED_PORT is in use; starting on $PORT instead."
else
  PORT="$PREFERRED_PORT"
fi

if needs_sync; then
  echo "LifeFinances: syncing the Python environment (this can take a few minutes on the first run)..."
  if ! uv sync; then
    pause_on_error "could not sync the Python environment (see above)." \
      "Check your network connection, then double-click again."
  fi
  # A read-only environment is not worth failing the launch for.
  touch "$SYNC_STAMP" 2>/dev/null || true
fi

if ! uv run python scripts/init_db.py; then
  pause_on_error "could not prepare data/data.db (see above)." \
    "Restore data/data.db.blank from git, then double-click again."
fi

URL="http://127.0.0.1:$PORT/"

open_when_ready() {
  local deadline=$((SECONDS + READY_TIMEOUT_SECONDS))
  while ((SECONDS < deadline)); do
    if app_answers "$PORT"; then
      open "$URL"
      return 0
    fi
    sleep 0.5
  done
  echo "LifeFinances: the server did not answer within ${READY_TIMEOUT_SECONDS}s." >&2
  echo "Open $URL manually once it is up." >&2
}

open_when_ready &
WATCHER_PID=$!
trap 'stop_watcher' EXIT

echo "LifeFinances: starting at $URL - press Ctrl+C to stop."
STATUS=0
uv run uvicorn web.app:app --reload --host 127.0.0.1 --port "$PORT" || STATUS=$?

# Ctrl+C (130), a closed window (129), or a kill (143) is a normal stop.
case "$STATUS" in
  0 | 129 | 130 | 143) ;;
  *)
    # A second launch can lose the bind race to one that is still starting; reuse it.
    if app_answers "$PORT"; then
      echo "LifeFinances is already running at $URL"
      open "$URL"
      exit 0
    fi
    pause_on_error "the server stopped with an error (exit $STATUS)." \
      "Read the output above for the cause."
    ;;
esac

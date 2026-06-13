# Tools — Agent Guide

Marimo standalone apps live here. Phase 5 adds the disability insurance calculator.

## Rules

- Import `core`, `domain`, `simulation` only — **never** `web`.
- Load plans from SQLite (`data/data.db`) or inline parameters for what-if analysis.
- Run: `uv run marimo edit tools/<app>.py` (Marimo added in Phase 5).

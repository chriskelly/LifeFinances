#!/usr/bin/env python3
"""One-shot generator for data/data.db.blank. Re-run only when schema changes."""

from __future__ import annotations

import sqlite3

from core.paths import default_blank_db_path, repo_root

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    fred_api_key TEXT,
    eod_api_key TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO app_settings (id) VALUES (1);
"""


def main() -> None:
    blank_path = default_blank_db_path()
    blank_path.parent.mkdir(parents=True, exist_ok=True)
    if blank_path.exists():
        blank_path.unlink()
    conn = sqlite3.connect(blank_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    print(f"Wrote blank schema to {blank_path} (repo root {repo_root()})")


if __name__ == "__main__":
    main()

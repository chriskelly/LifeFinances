from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from core.models import AppSettings
from core.paths import default_db_path

APP_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    fred_api_key TEXT,
    eod_api_key TEXT,
    default_plan_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class SettingsRepository:
    db_path: Path

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(app_settings)").fetchall()
        }
        if "default_plan_id" not in columns:
            conn.execute("ALTER TABLE app_settings ADD COLUMN default_plan_id INTEGER")

    def _ensure_settings_row(self, conn: sqlite3.Connection) -> None:
        conn.execute(APP_SETTINGS_SCHEMA)
        self._ensure_columns(conn)
        conn.execute("INSERT OR IGNORE INTO app_settings (id) VALUES (1)")

    def get(self) -> AppSettings:
        conn = self._connect()
        try:
            self._ensure_settings_row(conn)
            row = conn.execute(
                """
                SELECT fred_api_key, eod_api_key, default_plan_id
                FROM app_settings
                WHERE id = 1
                """
            ).fetchone()
            conn.commit()
        finally:
            conn.close()

        if row is None:
            return AppSettings()
        return AppSettings(
            fred_api_key=row[0],
            eod_api_key=row[1],
            default_plan_id=row[2],
        )

    def save(self, settings: AppSettings) -> None:
        conn = self._connect()
        try:
            self._ensure_settings_row(conn)
            conn.execute(
                """
                UPDATE app_settings
                SET fred_api_key = ?,
                    eod_api_key = ?,
                    default_plan_id = ?,
                    updated_at = datetime('now')
                WHERE id = 1
                """,
                (
                    settings.fred_api_key,
                    settings.eod_api_key,
                    settings.default_plan_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

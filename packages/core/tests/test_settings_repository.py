from __future__ import annotations

import sqlite3

from core.models import AppSettings
from core.settings_repository import SettingsRepository


def test_app_settings_normalizes_blank_keys_to_none() -> None:
    settings = AppSettings(fred_api_key="  ", eod_api_key="")

    assert settings.fred_api_key is None
    assert settings.eod_api_key is None


def test_settings_repository_returns_defaults_for_blank_db(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)

    settings = repo.get()

    assert settings == AppSettings()


def test_settings_repository_round_trips_api_keys(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)
    expected_fred_key = "fred-test-key"
    expected_eod_key = "eod-test-key"

    repo.save(
        AppSettings(
            fred_api_key=expected_fred_key,
            eod_api_key=expected_eod_key,
        )
    )
    loaded = repo.get()

    assert loaded.fred_api_key == expected_fred_key
    assert loaded.eod_api_key == expected_eod_key


def test_settings_repository_creates_table_for_older_db(tmp_path) -> None:
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    repo = SettingsRepository(db_path=db_path)
    expected_key = "fred-from-old-db"
    repo.save(AppSettings(fred_api_key=expected_key))

    assert repo.get().fred_api_key == expected_key

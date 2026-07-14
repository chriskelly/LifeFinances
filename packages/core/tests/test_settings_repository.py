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


def test_settings_repository_round_trips_default_plan_id(db_path) -> None:
    repo = SettingsRepository(db_path=db_path)
    expected_plan_id = 3

    repo.save(AppSettings(default_plan_id=expected_plan_id))
    loaded = repo.get()

    assert loaded.default_plan_id == expected_plan_id


def test_settings_repository_adds_default_plan_id_column_on_older_settings_table(
    tmp_path,
) -> None:
    db_path = tmp_path / "old_settings.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE app_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                fred_api_key TEXT,
                eod_api_key TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO app_settings (id) VALUES (1);
            """
        )
        conn.commit()
    finally:
        conn.close()

    repo = SettingsRepository(db_path=db_path)
    expected_plan_id = 7
    repo.save(AppSettings(default_plan_id=expected_plan_id))

    assert repo.get().default_plan_id == expected_plan_id


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

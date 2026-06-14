"""Tests for database bootstrap."""

import sqlite3
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import init_db  # noqa: E402


@pytest.fixture
def temp_repo_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    blank = data_dir / "data.db.blank"
    blank.write_bytes((REPO_ROOT / "data" / "data.db.blank").read_bytes())
    monkeypatch.setenv("LIFE_FINANCES_DB_PATH", str(data_dir / "data.db"))
    monkeypatch.setattr(
        "core.paths.default_blank_db_path",
        lambda: blank,
    )
    return data_dir


def test_init_db_creates_file_from_blank(temp_repo_paths: Path) -> None:
    db_path = init_db.init_db()
    assert db_path.is_file()
    conn = sqlite3.connect(db_path)
    try:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    assert ("plans",) in tables


def test_init_db_is_idempotent(temp_repo_paths: Path) -> None:
    first = init_db.init_db()
    second = init_db.init_db()
    assert first == second

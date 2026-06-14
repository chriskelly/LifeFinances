import sqlite3
from pathlib import Path

from core.db_bootstrap import materialize_blank_db


def test_materialize_blank_db_creates_plans_table(tmp_path: Path) -> None:
    db_path = tmp_path / "nested" / "data.db"

    result = materialize_blank_db(db_path)

    assert result == db_path
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        conn.close()
    assert "plans" in tables

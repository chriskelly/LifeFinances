from __future__ import annotations

from pathlib import Path

from core.paths import default_blank_db_path


def materialize_blank_db(db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(default_blank_db_path().read_bytes())
    return db_path

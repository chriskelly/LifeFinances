#!/usr/bin/env python3
"""Bootstrap data/data.db from data/data.db.blank."""

from __future__ import annotations

from pathlib import Path

from core.db_bootstrap import materialize_blank_db
from core.paths import default_blank_db_path, default_db_path


def init_db(*, force: bool = False) -> Path:
    """Copy blank schema to working DB path if missing (or when force=True)."""
    db_path = default_db_path()
    blank_path = default_blank_db_path()
    if not blank_path.is_file():
        raise FileNotFoundError(f"Blank schema not found: {blank_path}")
    if db_path.exists() and not force:
        return db_path
    return materialize_blank_db(db_path)


def main() -> None:
    path = init_db()
    print(f"Database ready at {path}")


if __name__ == "__main__":
    main()

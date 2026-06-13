"""Repository path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the LifeFinances repository root."""
    return Path(__file__).resolve().parents[3]


def default_blank_db_path() -> Path:
    return repo_root() / "data" / "data.db.blank"


def default_db_path() -> Path:
    override = os.environ.get("LIFE_FINANCES_DB_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return repo_root() / "data" / "data.db"
